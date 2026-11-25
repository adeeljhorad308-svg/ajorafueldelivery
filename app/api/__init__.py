"""API blueprint: live JSON for admin counters and order tracking polls."""

from flask import Blueprint, abort, g, jsonify

from app import timeutil
from app.customer import presentation
from app.db import get_db
from app.labels import order_status_label
from app.queries import drivers as driver_queries
from app.queries import orders as order_queries
from app.queries import tracking as tracking_queries
from app.security import limiter, require_admin

bp = Blueprint("api", __name__)


@bp.get("/api/admin/live")
def admin_live():
    guard_response = require_admin()
    if guard_response is not None:
        return guard_response
    db = get_db()
    return jsonify(
        {
            "available_drivers": driver_queries.count_by_status(db, "Available"),
            "busy_drivers": driver_queries.count_by_status(db, "Busy"),
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
