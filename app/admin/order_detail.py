"""Order details (C10, docs/SPEC.md screen 14 and pop-ups 2-3): GET renders
the page; the three POSTs apply an assign, a status move or a cancel. All
wording lives in order_detail_presentation.py / order_detail_dialogs.py; all
dispatch logic reuses app/dispatch.py - nothing here duplicates it."""

import sqlite3

from flask import abort, flash, g, redirect, render_template, request, url_for

from app import dispatch, timeutil
from app.admin import bp
from app.admin.order_detail_dialogs import (
    assign_dialog_context,
    cancel_dialog_context,
    status_dialog_context,
)
from app.admin.order_detail_presentation import (
    ALLOWED_STATUS_MOVES,
    CANCEL_OTHER_MAX_LENGTH,
    CANCEL_REASONS,
    CANCELLABLE_STATUSES,
    customer_info,
    driver_panel,
    header,
    location_info,
    next_step,
    order_info,
    route_stops,
    tracking_history,
)
from app.applog import app_logger
from app.db import get_db
from app.queries import admin_orders as order_queries
from app.queries import assignments as assignment_queries
from app.queries import drivers as driver_queries
from app.queries import orders as order_mutations
from app.queries import tracking as tracking_queries

STALE_MESSAGE = "This order was updated by someone else. Reload to see the latest."
ILLEGAL_MOVE_MESSAGE = "This move is not allowed from the order's current status."


def _load_order_or_404(db, order_id):
    order_row = order_queries.find_admin_by_id(db, order_id)
    if order_row is None:
        abort(404)
    return order_row


def _load_order_or_404_in_transaction(db, order_id):
    """Same lookup, but rolls back first - used inside a POST's BEGIN
    IMMEDIATE, where an uncaught abort() would otherwise leave the
    transaction for the connection teardown to discard instead."""
    order_row = order_queries.find_admin_by_id(db, order_id)
    if order_row is None:
        db.rollback()
        abort(404)
    return order_row


def _redirect_to_order(order_id):
    return redirect(url_for("admin.order_detail", order_id=order_id))


def _is_stale(db, order_id):
    posted = request.form.get("stale_token", type=int)
    return posted != tracking_queries.latest_id_for_order(db, order_id)


def _build_dialogs(db, order_row, moves):
    """Only the pop-ups this order's current status can actually open."""
    dialogs = {}
    needs_assign = order_row["driver_id"] is not None and order_row["status"] == "Assigned"
    for move in moves:
        if move["action"] == "assign":
            needs_assign = True
        elif move["action"] == "cancel":
            dialogs["dialog-cancel"] = cancel_dialog_context(order_row)
        else:
            context = status_dialog_context(order_row, move)
            dialogs[context["dialog_id"]] = context
    if needs_assign:
        ranked = dispatch.rank_available_drivers(db, order_row)
        total_drivers = driver_queries.count_active(db)
        dialogs["dialog-assign"] = assign_dialog_context(order_row, ranked, total_drivers)
    return dialogs


@bp.get("/admin/orders/<int:order_id>")
def order_detail(order_id):
    db = get_db()
    order_row = _load_order_or_404(db, order_id)
    next_step_data = next_step(order_row)
    return render_template(
        "admin/order_detail.html",
        header=header(order_row),
        order_info=order_info(order_row),
        customer=customer_info(order_row),
        location=location_info(order_row),
        driver=driver_panel(order_row),
        route=route_stops(db, order_row),
        tracking=tracking_history(tracking_queries.list_for_order(db, order_id), order_row),
        next_step=next_step_data,
        dialogs=_build_dialogs(db, order_row, next_step_data["moves"]),
        stale_token=tracking_queries.latest_id_for_order(db, order_id),
    )


@bp.post("/admin/orders/<int:order_id>/assign")
def order_assign(order_id):
    db = get_db()
    driver_id = request.form.get("driver_id", type=int)
    order_row = None
    try:
        db.execute("BEGIN IMMEDIATE")
        order_row = _load_order_or_404_in_transaction(db, order_id)
        if _is_stale(db, order_id):
            db.rollback()
            flash(STALE_MESSAGE, "error")
            return _redirect_to_order(order_id)
        if order_row["status"] not in ("Pending", "Assigned") or not order_row["call_confirmed"]:
            db.rollback()
            flash(ILLEGAL_MOVE_MESSAGE, "error")
            return _redirect_to_order(order_id)
        driver = driver_queries.find_by_id(db, driver_id) if driver_id else None
        if driver is None or driver["status"] != "Available" or not driver["is_active"]:
            db.rollback()
            flash("That driver is no longer free. Pick another.", "error")
            return _redirect_to_order(order_id)
        dispatch.assign_driver(db, order_row, driver_id)
        db.commit()
    except sqlite3.IntegrityError:
        db.rollback()
        raise
    app_logger().info(
        "order %s assigned to driver %s by admin %s", order_id, driver_id, g.current_user["user_id"]
    )
    return _redirect_to_order(order_id)


def _parse_cancel_reason(form):
    reason = form.get("cancel_reason") or ""
    valid_values = {value for value, _ in CANCEL_REASONS}
    if reason not in valid_values:
        return None, "Choose a reason for cancelling."
    if reason == "Other":
        other = (form.get("cancel_reason_other") or "").strip()[:CANCEL_OTHER_MAX_LENGTH]
        if not other:
            return None, "Type the reason."
        return other, None
    return reason, None


def _apply_status_move(db, order_row, new_status, cancel_reason, now_sql):
    freed_driver_id = None
    if new_status == "Cancelled":
        if order_row["driver_id"] is not None:
            assignment_queries.delete_by_order_id(db, order_row["order_id"])
            freed_driver_id = order_row["driver_id"]
        order_mutations.cancel(db, order_row["order_id"], cancel_reason)
    elif new_status == "Pending":
        assignment_queries.delete_by_order_id(db, order_row["order_id"])
        freed_driver_id = order_row["driver_id"]
        order_mutations.update_status(db, order_row["order_id"], new_status)
    elif new_status == "Delivered":
        lat, lon = dispatch.order_location(order_row)
        assignment_queries.mark_completed(db, order_row["assign_id"], now_sql)
        driver_queries.update_location(db, order_row["driver_id"], lat, lon)
        freed_driver_id = order_row["driver_id"]
        order_mutations.update_status(db, order_row["order_id"], new_status)
    else:
        order_mutations.update_status(db, order_row["order_id"], new_status)
    if freed_driver_id is not None:
        driver_queries.set_status(db, freed_driver_id, "Available")
    tracking_queries.add_tracking(
        db,
        order_row["order_id"],
        new_status,
        now_sql,
        order_row["latitude"],
        order_row["longitude"],
    )
    return freed_driver_id is not None


@bp.post("/admin/orders/<int:order_id>/status")
def order_status(order_id):
    db = get_db()
    new_status = request.form.get("new_status")
    is_cancel = new_status == "Cancelled"
    cancel_reason = None
    if is_cancel:
        cancel_reason, reason_error = _parse_cancel_reason(request.form)
        if reason_error:
            flash(reason_error, "error")
            return _redirect_to_order(order_id)

    freed_driver = False
    from_status = None
    try:
        db.execute("BEGIN IMMEDIATE")
        order_row = _load_order_or_404_in_transaction(db, order_id)
        from_status = order_row["status"]
        if _is_stale(db, order_id):
            db.rollback()
            flash(STALE_MESSAGE, "error")
            return _redirect_to_order(order_id)
        allowed = (
            from_status in CANCELLABLE_STATUSES
            if is_cancel
            else (from_status, new_status) in ALLOWED_STATUS_MOVES
        )
        if not allowed:
            db.rollback()
            flash(ILLEGAL_MOVE_MESSAGE, "error")
            return _redirect_to_order(order_id)
        now_sql = timeutil.to_sql(timeutil.utcnow())
        freed_driver = _apply_status_move(db, order_row, new_status, cancel_reason, now_sql)
        db.commit()
    except sqlite3.IntegrityError:
        db.rollback()
        raise
    if freed_driver:
        dispatch.dispatch_pending(db)
    app_logger().info(
        "order %s status %s -> %s by admin %s",
        order_id,
        from_status,
        new_status,
        g.current_user["user_id"],
    )
    return _redirect_to_order(order_id)


@bp.post("/admin/orders/<int:order_id>/call-done")
def order_call_done(order_id):
    db = get_db()
    order_row = None
    try:
        db.execute("BEGIN IMMEDIATE")
        order_row = _load_order_or_404_in_transaction(db, order_id)
        if _is_stale(db, order_id):
            db.rollback()
            flash(STALE_MESSAGE, "error")
            return _redirect_to_order(order_id)
        if order_row["call_confirmed"]:
            db.rollback()
            flash("This call is already marked done.", "error")
            return _redirect_to_order(order_id)
        order_mutations.mark_call_confirmed(db, order_id)
        db.commit()
    except sqlite3.IntegrityError:
        db.rollback()
        raise
    if order_row["status"] == "Pending" and order_row["scheduled_at"] is None:
        try:
            db.execute("BEGIN IMMEDIATE")
            dispatch.dispatch_order(db, order_row, timeutil.utcnow())
            db.commit()
        except sqlite3.IntegrityError:
            db.rollback()
            raise
    app_logger().info("order %s call marked done by admin %s", order_id, g.current_user["user_id"])
    return _redirect_to_order(order_id)
