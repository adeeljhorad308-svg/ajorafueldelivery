"""Drivers (C12, docs/SPEC.md screen 18, pop-up 6). GET lists every active
driver; POSTs add, edit/quick-switch, or soft-remove one - all wording lives
in drivers_presentation.py / drivers_validation.py."""

import sqlite3
from decimal import Decimal

from flask import abort, flash, g, redirect, render_template, request, url_for

from app import dispatch
from app.admin import bp
from app.admin.drivers_presentation import driver_row, drivers_summary, remove_dialog_context
from app.admin.drivers_validation import (
    is_valid_area,
    is_valid_status,
    is_valid_vehicle_no,
    normalize_vehicle_no,
)
from app.applog import app_logger
from app.areas import area_centre, area_names
from app.auth.validation import is_valid_name, is_valid_phone, normalize_phone
from app.db import get_db
from app.queries import admin_orders as order_queries
from app.queries import assignments as assignment_queries
from app.queries import drivers as driver_queries

PHONE_TAKEN_MESSAGE = "This phone number is already used by another driver."
VEHICLE_TAKEN_MESSAGE = "This vehicle number is already used by another driver."


def _parse_driver_form(form, default_status="Available"):
    name = (form.get("name") or "").strip()
    phone = normalize_phone(form.get("phone") or "")
    vehicle_no = normalize_vehicle_no(form.get("vehicle_no"))
    area = form.get("area") or ""
    # The quick on/off switch is a checkbox sharing name="status" with a
    # hidden "Off Duty" fallback before it in the DOM, so a browser submits
    # both values when checked and only the hidden one when not - the last
    # value in document order is the real one. The add/edit dialog's two
    # radios (same name) submit exactly one value, so this still works there.
    status_values = form.getlist("status")
    status = status_values[-1] if status_values else default_status

    errors = {}
    if not is_valid_name(name):
        errors["name"] = "Name must be 2-60 characters."
    if not is_valid_phone(phone):
        errors["phone"] = "Enter a valid mobile number like 0300-1234567."
    if not is_valid_vehicle_no(vehicle_no):
        errors["vehicle_no"] = "Enter a vehicle number like LEA-1234."
    if not is_valid_area(area):
        errors["area"] = "Pick an area."
    if not is_valid_status(status):
        status = default_status
    fields = {
        "name": name,
        "phone": phone,
        "vehicle_no": vehicle_no,
        "area": area,
        "status": status,
    }
    return fields, errors


def _rows_context(db, open_dialog=None, form_errors=None, form_values=None, error_driver_id=None):
    driver_rows = driver_queries.list_active_all(db)
    open_counts = assignment_queries.count_open_by_driver(db)
    rows = [driver_row(row, open_counts.get(row["driver_id"], 0)) for row in driver_rows]
    remove_dialogs = []
    for row, context in zip(driver_rows, rows, strict=True):
        open_orders = (
            order_queries.list_open_orders_for_driver(db, row["driver_id"])
            if context["open_orders"]
            else []
        )
        remove_dialogs.append(remove_dialog_context(context, open_orders))
    return {
        "rows": rows,
        "summary": drivers_summary(driver_rows),
        "area_options": [(name, name) for name in area_names()],
        "remove_dialogs": remove_dialogs,
        "open_dialog": open_dialog,
        "form_errors": form_errors or {},
        "form_values": form_values,
        "error_driver_id": error_driver_id,
    }


@bp.get("/admin/drivers")
def drivers():
    db = get_db()
    return render_template("admin/drivers.html", **_rows_context(db))


@bp.post("/admin/drivers")
def driver_create():
    db = get_db()
    fields, errors = _parse_driver_form(request.form)
    if not errors:
        if driver_queries.find_by_phone(db, fields["phone"]) is not None:
            errors["phone"] = PHONE_TAKEN_MESSAGE
        if driver_queries.find_by_vehicle_no(db, fields["vehicle_no"]) is not None:
            errors["vehicle_no"] = VEHICLE_TAKEN_MESSAGE
    if errors:
        return render_template(
            "admin/drivers.html",
            **_rows_context(db, "dialog-add-driver", errors, fields),
        ), 400

    lat, lng = area_centre(fields["area"])
    db.execute("BEGIN IMMEDIATE")
    try:
        driver_queries.create_driver(
            db,
            fields["name"],
            fields["phone"],
            fields["vehicle_no"],
            fields["area"],
            fields["status"],
            lat,
            lng,
            Decimal("5.0"),
        )
        db.commit()
    except sqlite3.IntegrityError:
        db.rollback()
        return render_template(
            "admin/drivers.html",
            **_rows_context(db, "dialog-add-driver", {"phone": PHONE_TAKEN_MESSAGE}, fields),
        ), 400
    app_logger().info("driver '%s' added by admin %s", fields["name"], g.current_user["user_id"])
    flash(f"{fields['name']} added.", "success")
    return redirect(url_for("admin.drivers"))


@bp.post("/admin/drivers/<int:driver_id>")
def driver_update(driver_id):
    db = get_db()
    existing = driver_queries.find_by_id(db, driver_id)
    if existing is None:
        abort(404)

    fields, errors = _parse_driver_form(request.form, default_status=existing["status"])
    if not errors:
        other_phone = driver_queries.find_by_phone(db, fields["phone"])
        if other_phone is not None and other_phone["driver_id"] != driver_id:
            errors["phone"] = PHONE_TAKEN_MESSAGE
        if driver_queries.find_by_vehicle_no_excluding(db, fields["vehicle_no"], driver_id):
            errors["vehicle_no"] = VEHICLE_TAKEN_MESSAGE
    if errors:
        return render_template(
            "admin/drivers.html",
            **_rows_context(db, f"dialog-edit-driver-{driver_id}", errors, fields, driver_id),
        ), 400

    # Busy is set only by the system (CLAUDE.md): an edit never moves a
    # driver away from Busy, whatever the form posted.
    status = existing["status"] if existing["status"] == "Busy" else fields["status"]
    db.execute("BEGIN IMMEDIATE")
    try:
        driver_queries.update_driver(
            db,
            driver_id,
            fields["name"],
            fields["phone"],
            fields["vehicle_no"],
            fields["area"],
            status,
        )
        db.commit()
    except sqlite3.IntegrityError:
        db.rollback()
        return render_template(
            "admin/drivers.html",
            **_rows_context(
                db,
                f"dialog-edit-driver-{driver_id}",
                {"phone": PHONE_TAKEN_MESSAGE},
                fields,
                driver_id,
            ),
        ), 400
    if status == "Available" and existing["status"] != "Available":
        dispatch.dispatch_pending(db)
    app_logger().info("driver %s updated by admin %s", driver_id, g.current_user["user_id"])
    return redirect(url_for("admin.drivers"))


@bp.post("/admin/drivers/<int:driver_id>/remove")
def driver_remove(driver_id):
    db = get_db()
    driver = None
    try:
        db.execute("BEGIN IMMEDIATE")
        driver = driver_queries.find_by_id(db, driver_id)
        if driver is None:
            db.rollback()
            abort(404)
        open_orders = order_queries.list_open_orders_for_driver(db, driver_id)
        if open_orders:
            db.rollback()
            flash(f"{driver['name']} has an active order. Finish or reassign it first.", "error")
            return redirect(url_for("admin.drivers"))
        driver_queries.soft_remove(db, driver_id)
        db.commit()
    except sqlite3.IntegrityError:
        db.rollback()
        raise
    app_logger().info("driver %s removed by admin %s", driver_id, g.current_user["user_id"])
    flash(f"{driver['name']} removed.", "success")
    return redirect(url_for("admin.drivers"))
