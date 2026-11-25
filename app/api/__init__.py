"""API blueprint: live JSON for admin counters and order tracking polls."""

from datetime import timedelta

from flask import Blueprint, abort, g, jsonify, request, url_for

from app import money, timeutil
from app.customer import presentation
from app.db import get_db
from app.labels import order_status_label
from app.queries import admin_orders as admin_order_queries
from app.queries import drivers as driver_queries
from app.queries import orders as order_queries
from app.queries import tracking as tracking_queries
from app.security import limiter, require_admin

bp = Blueprint("api", __name__)


@bp.get("/api/admin/live")
def admin_live():
    """Polled every 15 s from the admin dashboard and All orders (docs/SPEC.md
    screens 12-13): live counts, plus any open emergency newer than the
    `after` order_id the browser already rendered, so it can slide the new
    row in instead of reloading the page."""
    guard_response = require_admin()
    if guard_response is not None:
        return guard_response
    db = get_db()
    now = timeutil.utcnow()
    after_id = request.args.get("after", 0, type=int) or 0
    new_rows = admin_order_queries.list_open_emergencies_after_id(db, after_id)
    due_soon_count = admin_order_queries.count_due_soon(
        db, timeutil.to_sql(now), timeutil.to_sql(now + timedelta(minutes=60))
    )
    return jsonify(
        {
            "available_drivers": driver_queries.count_by_status(db, "Available"),
            "busy_drivers": driver_queries.count_by_status(db, "Busy"),
            "open_emergencies": admin_order_queries.count_open_emergencies(db),
            "due_soon": due_soon_count,
            "call_needed": admin_order_queries.count_call_needed(db),
            "new_emergencies": [
                {
                    "order_id": row["order_id"],
                    "order_number": f"ORD-{row['order_id']:04d}",
                    "customer_name": row["customer_name"],
                    "amount_label": money.format_pkr(money.from_db(row["total_amount"])),
                    "detail_url": url_for("admin.order_detail", order_id=row["order_id"]),
                }
                for row in new_rows
            ],
        }
    )


@bp.get("/api/orders/<int:order_id>/status")
@limiter.limit("120/minute")
def order_status(order_id):
    user = g.get("current_user")
    if user is None:
        abort(404)
    db = get_db()
    if user["role"] == "admin":
        order = order_queries.find_by_id(db, order_id)
    else:
        order = order_queries.find_by_id_for_user(db, order_id, user["user_id"])
    if order is None:
        abort(404)
    now = timeutil.utcnow()
    tracking_rows = tracking_queries.list_for_order(db, order_id)
    track = presentation.track_order_context(order, tracking_rows, now)
    return jsonify(
        status=order["status"],
        status_label=order_status_label(order["status"]),
        driver=presentation.driver_api_payload(order),
        steps=track["steps"],
        eta_text=track["eta_text"],
        eta_target=track["eta_target_iso"],
        is_finished=track["is_finished"],
        delivered_label=track["delivered_label"],
        delivered_sub_label=track["delivered_sub_label"],
        cancelled_label=track["cancelled_label"],
        reason_label=track["reason_label"],
    )
