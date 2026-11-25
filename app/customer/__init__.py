"""Customer blueprint: home (screen 4), order confirmed (screen 9), track
order and my orders (screens 10-11).

Each order type (fuel, emergency, generator, vehicle assistance) has its own
route module below, all registered on this same blueprint.
"""

from flask import Blueprint, abort, g, redirect, render_template, request, url_for

from app.customer import presentation, shared
from app.db import get_db
from app.queries import orders as order_queries
from app.queries import services as service_queries
from app.queries import tracking as tracking_queries
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
        active_order_url=active_order["track_url"] if active_order else None,
        emergency_href=presentation.emergency_href(open_emergency),
    )


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
        driver=presentation.driver_template_context(order),
        active_order_url=url_for("customer.order_track", order_id=order_id),
    )


@bp.get("/app/orders/<int:order_id>")
@login_required
def order_track(order_id):
    db = get_db()
    order = order_queries.find_by_id_for_user(db, order_id, g.current_user["user_id"])
    if order is None:
        abort(404)
    tracking_rows = tracking_queries.list_for_order(db, order_id)
    return render_template(
        "customer/order_track.html",
        track=presentation.track_order_context(order, tracking_rows),
        driver=presentation.driver_template_context(order),
        default_steps=presentation.blank_steps(),
        active_order_url=shared.active_order_url(db, g.current_user["user_id"]),
    )


@bp.get("/app/orders")
@login_required
def my_orders():
    db = get_db()
    user_id = g.current_user["user_id"]
    show = request.args.get("show", "all")
    if show not in ("all", "active", "delivered", "cancelled"):
        show = "all"
    page = request.args.get("page", 1, type=int) or 1

    total_count = order_queries.count_for_user_show(db, user_id, show)
    total_pages = max(1, -(-total_count // presentation.ORDERS_PER_PAGE))
    page = min(max(page, 1), total_pages)
    offset = (page - 1) * presentation.ORDERS_PER_PAGE
    rows = order_queries.list_for_user_show(db, user_id, show, presentation.ORDERS_PER_PAGE, offset)

    return render_template(
        "customer/my_orders.html",
        my_orders=presentation.my_orders_context(rows, show, page, total_count),
        page_url=lambda n: url_for("customer.my_orders", page=n, show=show),
        active_order_url=shared.active_order_url(db, user_id),
    )


@bp.get("/app/orders/<int:order_id>/repeat")
@login_required
def order_repeat(order_id):
    db = get_db()
    order = order_queries.find_by_id_for_user(db, order_id, g.current_user["user_id"])
    if order is None:
        abort(404)
    endpoint, args = presentation.repeat_target(order)
    return redirect(url_for(endpoint, **args))


# Each module registers its own routes on `bp` as a side effect of import.
from app.customer import assistance, emergency, fuel, generator  # noqa: E402, F401
