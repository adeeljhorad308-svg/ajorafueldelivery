"""Customer blueprint: home (screen 4) and order fuel (screen 5, pop-up 1)."""

import secrets
import sqlite3
from decimal import InvalidOperation

from flask import Blueprint, abort, g, jsonify, render_template, request, url_for

from app import dispatch, money, timeutil
from app.areas import area_names
from app.customer import presentation, validation
from app.db import get_db
from app.queries import orders as order_queries
from app.queries import services as service_queries
from app.queries import tracking as tracking_queries
from app.security import limiter, login_required

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
    return render_template(
        "customer/home.html",
        first_name=g.current_user["name"].split()[0],
        tiles=tiles,
        active_order=active_order,
        last_order=last_order,
        has_active_order=active_order is not None,
    )


def _fuel_services(db):
    rows = (service_queries.find_by_name(db, "Petrol"), service_queries.find_by_name(db, "Diesel"))
    return [row for row in rows if row and row["available"]]


@bp.get("/app/order/fuel")
@login_required
def order_fuel():
    db = get_db()
    fuel_services = _fuel_services(db)
    if not fuel_services:
        abort(404)
    options = [
        {
            "name": row["name"],
            "unit_price": money.to_db(money.from_db(row["unit_price"])),
            "price_label": f"{money.format_pkr(money.from_db(row['unit_price']))} / litre",
        }
        for row in fuel_services
    ]
    return render_template(
        "customer/order_fuel.html",
        fuel_options=options,
        areas=area_names(),
        order_key=secrets.token_urlsafe(24),
        has_active_order=order_queries.find_active_for_user(db, g.current_user["user_id"])
        is not None,
    )


def _fuel_order_errors(payload, litres):
    errors = {}
    if not validation.is_valid_fuel_litres(litres):
        errors["litres"] = "Enter between 5 and 100 litres"
    address = (payload.get("address") or "").strip()
    if not validation.is_valid_address(address):
        errors["address"] = "Add your address so the driver can find you"
    if not validation.is_valid_note(payload.get("note") or ""):
        errors["note"] = "Keep the note under 200 characters"
    has_location = payload.get("latitude") is not None and payload.get("longitude") is not None
    if not has_location and not validation.is_valid_area((payload.get("area") or "").strip()):
        errors["area"] = "Pick your area"
    if not (payload.get("order_key") or "").strip():
        errors["order_key"] = "Reload the page and try again"
    return errors


def _price_snapshot_matches(payload, current_price):
    raw = payload.get("price_snapshot")
    if not raw:
        return False
    try:
        return money.parse_amount(raw) == current_price
    except InvalidOperation:
        return False


def _price_updated_response(current_price, litres):
    total = money.from_db(current_price * litres)
    return jsonify(
        status="price_updated",
        unit_price=money.to_db(current_price),
        formatted_price=f"{money.format_pkr(current_price)} / litre",
        total=money.to_db(total),
        formatted_total=money.format_pkr(total),
    ), 409


@bp.post("/app/order/fuel")
@login_required
@limiter.limit("10/10 minutes", key_func=_rate_limit_key)
def order_fuel_submit():
    db = get_db()
    payload = request.get_json(silent=True) or {}

    fuel_type = payload.get("fuel_type")
    service = (
        service_queries.find_by_name(db, fuel_type) if fuel_type in ("Petrol", "Diesel") else None
    )
    if service is None or not service["available"]:
        return jsonify(status="error", errors={"fuel_type": "Choose petrol or diesel"}), 400

    litres = validation.parse_litres(payload.get("litres"))
    errors = _fuel_order_errors(payload, litres)
    if errors:
        return jsonify(status="error", errors=errors), 400

    current_price = money.from_db(service["unit_price"])
    if not _price_snapshot_matches(payload, current_price):
        return _price_updated_response(current_price, litres)

    order_key = payload.get("order_key", "").strip()
    existing = order_queries.find_by_order_key(db, order_key)
    if existing is not None:
        return jsonify(status="ok", redirect=_confirmed_url(existing["order_id"]))

    return _place_fuel_order(db, service, litres, payload, order_key)


def _confirmed_url(order_id):
    return url_for("customer.order_confirmed", order_id=order_id)


def _place_fuel_order(db, service, litres, payload, order_key):
    address = (payload.get("address") or "").strip()
    area = (payload.get("area") or "").strip() or None
    note = (payload.get("note") or "").strip() or None
    latitude = payload.get("latitude")
    longitude = payload.get("longitude")
    total = money.from_db(money.from_db(service["unit_price"]) * litres)
    now = timeutil.utcnow()
    try:
        # IMMEDIATE takes the write lock before dispatch reads free drivers, so a
        # second near-simultaneous order can't see the same driver as still free.
        db.execute("BEGIN IMMEDIATE")
        order_id = order_queries.insert_order(
            db,
            user_id=g.current_user["user_id"],
            service_id=service["service_id"],
            order_key=order_key,
            quantity=litres,
            total_amount=money.to_db(total),
            address=address,
            area=area,
            latitude=latitude,
            longitude=longitude,
            note=note,
        )
        tracking_queries.add_tracking(
            db, order_id, "Pending", timeutil.to_sql(now), latitude, longitude
        )
        dispatch.dispatch_order(
            db,
            {
                "order_id": order_id,
                "latitude": latitude,
                "longitude": longitude,
                "area": area,
                "is_emergency": 0,
            },
            now,
        )
        db.commit()
    except sqlite3.IntegrityError:
        db.rollback()
        existing = order_queries.find_by_order_key(db, order_key)
        if existing is None:
            raise
        return jsonify(status="ok", redirect=_confirmed_url(existing["order_id"]))
    return jsonify(status="ok", redirect=_confirmed_url(order_id))


def _driver_context(order):
    if order["driver_id"] is None:
        return {"assigned": False}
    distance = f"{float(money.from_db(order['distance_km'])):.1f}"
    return {
        "assigned": True,
        "driver_name": order["driver_name"],
        "vehicle_no": order["vehicle_no"],
        "eta_minutes": order["eta_minutes"],
        "distance_label": f"{distance} km away",
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
        order_number=f"ORD-{order['order_id']:04d}",
        service_name=order["service_name"],
        quantity_label=f"{int(round(order['quantity']))} L",
        total_label=money.format_pkr(money.from_db(order["total_amount"])),
        address=order["address"],
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
