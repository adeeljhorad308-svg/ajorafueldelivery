"""API blueprint: live JSON for admin counters and order tracking polls."""

from flask import Blueprint, abort, g, jsonify

from app import money
from app.db import get_db
from app.labels import order_status_label
from app.queries import drivers as driver_queries
from app.queries import orders as order_queries
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


def _initials(name):
    words = name.split()
    return "".join(word[0] for word in words[:2]).upper()


def _driver_payload(order):
    if order["driver_id"] is None:
        return None
    distance = f"{float(money.from_db(order['distance_km'])):.1f}"
    return {
        "name": order["driver_name"],
        "initials": _initials(order["driver_name"]),
        "vehicle_no": order["vehicle_no"],
        "rating_label": f"{float(order['driver_rating']):.1f}",
        "eta_minutes": order["eta_minutes"],
        "distance_label": f"{distance} km away",
        "phone": order["driver_phone"],
    }


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
    return jsonify(
        status=order["status"],
        status_label=order_status_label(order["status"]),
        driver=_driver_payload(order),
    )
