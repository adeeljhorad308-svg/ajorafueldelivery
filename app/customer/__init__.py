"""Customer blueprint: home (screen 4), order confirmed (screen 9) and track order.

Each order type (fuel, emergency, generator, vehicle assistance) has its own
route module below, all registered on this same blueprint.
"""

from flask import Blueprint, abort, g, render_template

from app import money
from app.customer import presentation
from app.db import get_db
from app.queries import orders as order_queries
from app.queries import services as service_queries
from app.security import login_required

bp = Blueprint("customer", __name__)


def _rate_limit_key():
    return f"user:{g.current_user['user_id']}"


@bp.get("/app")
@login_required
def home():
    db = get_db()
    user_id = g.current_user["user_id"]
    tiles = presentation.build_home_tiles(service_queries.list_active(db))
    active_order = presentation.active_order_card(order_queries.find_active_for_user(db, user_id))
    last_order = presentation.last_order_card(
        order_queries.find_last_finished_for_user(db, user_id)
    )
    open_emergency = order_queries.find_open_emergency_for_user(db, user_id)
    return render_template(
        "customer/home.html",
        first_name=g.current_user["name"].split()[0],
        tiles=tiles,
        active_order=active_order,
        last_order=last_order,
        has_active_order=active_order is not None,
        emergency_href=presentation.emergency_href(open_emergency),
    )


def _initials(name):
    words = name.split()
    return "".join(word[0] for word in words[:2]).upper()


def _driver_context(order):
    if order["driver_id"] is None:
        return {"assigned": False}
    distance = f"{float(money.from_db(order['distance_km'])):.1f}"
    return {
        "assigned": True,
        "driver_name": order["driver_name"],
        "initials": _initials(order["driver_name"]),
        "vehicle_no": order["vehicle_no"],
        "rating_label": f"{float(order['driver_rating']):.1f}",
        "eta_minutes": order["eta_minutes"],
        "distance_label": f"{distance} km away",
        "phone": order["driver_phone"],
    }


@bp.get("/app/orders/<int:order_id>/confirmed")
@login_required
def order_confirmed(order_id):
    db = get_db()
    order = order_queries.find_by_id_for_user(db, order_id, g.current_user["user_id"])
    if order is None:
        abort(404)
    return render_template(
        "customer/order_confirmed.html",
        order=presentation.order_confirmed_context(order),
        driver=_driver_context(order),
    )


@bp.get("/app/orders/<int:order_id>")
@login_required
def order_track(order_id):
    db = get_db()
    order = order_queries.find_by_id_for_user(db, order_id, g.current_user["user_id"])
    if order is None:
        abort(404)
    return render_template(
        "customer/order_track.html",
        order_number=f"ORD-{order['order_id']:04d}",
        status=order["status"],
        driver=_driver_context(order),
    )


# Each module registers its own routes on `bp` as a side effect of import.
from app.customer import assistance, emergency, fuel, generator  # noqa: E402, F401
