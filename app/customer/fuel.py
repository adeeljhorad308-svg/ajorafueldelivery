"""Order fuel (screen 5): petrol or diesel, 5-100 litres, dispatched at once."""

import secrets
import sqlite3

from flask import abort, g, jsonify, render_template, request

from app import dispatch, money, timeutil
from app.areas import area_names
from app.customer import bp, shared, validation
from app.db import get_db
from app.queries import orders as order_queries
from app.queries import tracking as tracking_queries
from app.security import limiter, login_required


def _rate_limit_key():
    return f"user:{g.current_user['user_id']}"


@bp.get("/app/order/fuel")
@login_required
def order_fuel():
    db = get_db()
    fuel_services = shared.fuel_services(db)
    if not fuel_services:
        abort(404)
    return render_template(
        "customer/order_fuel.html",
        fuel_options=shared.fuel_options(fuel_services),
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


@bp.post("/app/order/fuel")
@login_required
@limiter.limit("10/10 minutes", key_func=_rate_limit_key)
def order_fuel_submit():
    db = get_db()
    payload = request.get_json(silent=True) or {}

    fuel_type = payload.get("fuel_type")
    service = shared.find_fuel_service(db, fuel_type)
    if service is None or not service["available"]:
        return jsonify(status="error", errors={"fuel_type": "Choose petrol or diesel"}), 400

    litres = validation.parse_litres(payload.get("litres"))
    errors = _fuel_order_errors(payload, litres)
    if errors:
        return jsonify(status="error", errors=errors), 400

    current_price = money.from_db(service["unit_price"])
    if not shared.price_snapshot_matches(payload, current_price):
        return shared.price_updated_response(current_price, litres)

    order_key = payload.get("order_key", "").strip()
    existing = order_queries.find_by_order_key(db, order_key)
    if existing is not None:
        return jsonify(status="ok", redirect=shared.confirmed_url(existing["order_id"]))

    return _place_fuel_order(db, service, litres, payload, order_key)


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
        return jsonify(status="ok", redirect=shared.confirmed_url(existing["order_id"]))
    return jsonify(status="ok", redirect=shared.confirmed_url(order_id))
