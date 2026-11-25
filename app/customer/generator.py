"""Generator and machinery fuel (screen 7, FR-05): 20-500 L, scheduled or ASAP,
above 200 L waits for the admin's confirmation call."""

import secrets
import sqlite3

from flask import abort, g, jsonify, render_template, request

from app import dispatch, money, timeutil
from app.areas import area_names
from app.customer import bp, scheduling, shared, validation
from app.db import get_db
from app.queries import orders as order_queries
from app.queries import tracking as tracking_queries
from app.security import limiter, login_required


def _rate_limit_key():
    return f"user:{g.current_user['user_id']}"


@bp.get("/app/order/generator")
@login_required
def order_generator():
    db = get_db()
    fuel_services = shared.fuel_services(db)
    if not fuel_services:
        abort(404)
    preset_type = request.args.get("type")
    if preset_type not in validation.GENERATOR_TYPES:
        preset_type = validation.GENERATOR_TYPES[0]
    now = timeutil.utcnow()
    return render_template(
        "customer/order_generator.html",
        fuel_options=shared.fuel_options(fuel_services),
        generator_types=validation.GENERATOR_TYPES,
        preset_type=preset_type,
        areas=area_names(),
        days=scheduling.generator_days(now),
        slots=scheduling.generator_slots(),
        order_key=secrets.token_urlsafe(24),
        prefill_litres=shared.prefill_litres(request.args, 20, 500, 250),
        prefill_address=shared.prefill_text(request.args, "address", 200),
        prefill_area=shared.prefill_area(request.args),
        active_order_url=shared.active_order_url(db, g.current_user["user_id"]),
    )


def _generator_order_errors(payload, litres):
    errors = {}
    if not validation.is_valid_generator_type((payload.get("generator_type") or "").strip()):
        errors["generator_type"] = "Choose what the fuel is for"
    if not validation.is_valid_generator_litres(litres):
        errors["litres"] = "Between 20 and 500 litres"
    address = (payload.get("address") or "").strip()
    if not validation.is_valid_address(address):
        errors["address"] = "Add the site address so the driver can find it"
    has_location = payload.get("latitude") is not None and payload.get("longitude") is not None
    if not has_location and not validation.is_valid_area((payload.get("area") or "").strip()):
        errors["area"] = "Pick the area"
    if not (payload.get("order_key") or "").strip():
        errors["order_key"] = "Reload the page and try again"
    return errors


def _parse_delivery(payload):
    """Returns (scheduled_at_utc_or_None, error_or_None). "asap" needs nothing
    further; "scheduled" needs a valid day + 2-hour slot."""
    timing = payload.get("timing")
    if timing == "asap":
        return None, None
    if timing != "scheduled":
        return None, "Choose when you want it delivered"
    try:
        hour = int(payload.get("slot"))
    except (TypeError, ValueError):
        return None, "Pick a 2-hour slot"
    scheduled_at = scheduling.slot_datetime(payload.get("day"), hour)
    if scheduled_at is None:
        return None, "Pick a day and a 2-hour slot"
    return scheduled_at, None


@bp.post("/app/order/generator")
@login_required
@limiter.limit("10/10 minutes", key_func=_rate_limit_key)
def order_generator_submit():
    db = get_db()
    payload = request.get_json(silent=True) or {}

    fuel_type = payload.get("fuel_type")
    service = shared.find_fuel_service(db, fuel_type)
    if service is None or not service["available"]:
        return jsonify(status="error", errors={"fuel_type": "Choose petrol or diesel"}), 400

    litres = validation.parse_litres(payload.get("litres"))
    errors = _generator_order_errors(payload, litres)
    scheduled_at, delivery_error = _parse_delivery(payload)
    if delivery_error:
        errors["timing"] = delivery_error
    if errors:
        return jsonify(status="error", errors=errors), 400

    current_price = money.from_db(service["unit_price"])
    if not shared.price_snapshot_matches(payload, current_price):
        return shared.price_updated_response(current_price, litres)

    order_key = payload.get("order_key", "").strip()
    existing = order_queries.find_by_order_key(db, order_key)
    if existing is not None:
        return jsonify(status="ok", redirect=shared.confirmed_url(existing["order_id"]))

    return _place_generator_order(db, service, litres, payload, order_key, scheduled_at)


def _place_generator_order(db, service, litres, payload, order_key, scheduled_at):
    address = (payload.get("address") or "").strip()
    area = (payload.get("area") or "").strip() or None
    generator_type = (payload.get("generator_type") or "").strip()
    latitude = payload.get("latitude")
    longitude = payload.get("longitude")
    call_confirmed = 0 if litres > validation.GENERATOR_CALL_THRESHOLD else 1
    is_asap = scheduled_at is None
    total = money.from_db(money.from_db(service["unit_price"]) * litres)
    now = timeutil.utcnow()
    try:
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
            note=generator_type,
            call_confirmed=call_confirmed,
            scheduled_at=timeutil.to_sql(scheduled_at) if scheduled_at else None,
        )
        tracking_queries.add_tracking(
            db, order_id, "Pending", timeutil.to_sql(now), latitude, longitude
        )
        if is_asap and call_confirmed:
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
