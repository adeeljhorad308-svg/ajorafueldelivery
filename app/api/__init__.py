"""API blueprint. /api/orders/<id>/status lands when order placement is built."""

from flask import Blueprint, jsonify

from app.db import get_db
from app.queries import drivers as driver_queries
from app.security import require_admin

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
