"""Vehicle assistance (screen 8, FR-06): engine oil, battery, tyre, car wash.
Battery/tyre default to Now; car wash needs a slot at least 2 hours ahead."""

import secrets
import sqlite3

from flask import abort, g, jsonify, render_template, request

from app import dispatch, money, timeutil
from app.areas import area_names
from app.customer import bp, presentation, scheduling, shared, validation
from app.db import get_db
from app.queries import orders as order_queries
from app.queries import services as service_queries
from app.queries import tracking as tracking_queries
from app.security import limiter, login_required

ASSISTANCE_SERVICES = ("Engine oil delivery", "Battery help", "Tyre help", "Car wash")


def _rate_limit_key():
    return f"user:{g.current_user['user_id']}"


def _available_services(db):
    rows = (service_queries.find_by_name(db, name) for name in ASSISTANCE_SERVICES)
    return [row for row in rows if row and row["available"]]


def _service_option(row):
    price = money.from_db(row["unit_price"])
    return {
        "name": row["name"],
        "unit_price": money.to_db(price),
        "price_label": f"{money.format_pkr(price)} / service",
        "icon": presentation.SERVICE_ICONS.get(row["name"], "gas-pump"),
    }


@bp.get("/app/order/assistance")
@login_required
def order_assistance():
    db = get_db()
    services = _available_services(db)
    if not services:
        abort(404)
    names = [row["name"] for row in services]
    preset_service = request.args.get("service")
    if preset_service not in names:
        preset_service = names[0]
    now = timeutil.utcnow()
    return render_template(
        "customer/order_assistance.html",
        services=[_service_option(row) for row in services],
        preset_service=preset_service,
        vehicle_types=validation.VEHICLE_TYPES,
        areas=area_names(),
        car_wash_slots=scheduling.car_wash_slots(now),
        order_key=secrets.token_urlsafe(24),
        has_active_order=order_queries.find_active_for_user(db, g.current_user["user_id"])
        is not None,
    )


def _assistance_order_errors(payload):
    errors = {}
    if not validation.is_valid_vehicle_type((payload.get("vehicle_type") or "").strip()):
        errors["vehicle_type"] = "Choose your vehicle type"
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


def _parse_assistance_time(payload, service_name, now):
    """Returns (scheduled_at_utc_or_None, error_or_None); None/None means ASAP."""
    timing = payload.get("timing")
    if timing == "now":
        if service_name == "Car wash":
            return None, "Car wash must be booked at least 2 hours ahead"
        return None, None
    if timing != "scheduled":
        return None, "Choose when you want it"
    try:
        hour = int(payload.get("slot"))
    except (TypeError, ValueError):
        return None, "Pick a time"
    if not scheduling.is_valid_slot_hour(hour):
        return None, "Pick a time"
    today = timeutil.to_karachi(now).date()
    scheduled_at = timeutil.from_karachi_date_and_hour(today, hour)
    if service_name == "Car wash" and not scheduling.is_car_wash_time_valid(scheduled_at, now):
        return None, "Car wash must be booked at least 2 hours ahead"
    return scheduled_at, None


@bp.post("/app/order/assistance")
@login_required
@limiter.limit("10/10 minutes", key_func=_rate_limit_key)
def order_assistance_submit():
    db = get_db()
    payload = request.get_json(silent=True) or {}

    service_name = payload.get("service")
    service = (
        service_queries.find_by_name(db, service_name)
        if service_name in ASSISTANCE_SERVICES
        else None
    )
    if service is None or not service["available"]:
        return jsonify(status="error", errors={"service": "Choose a service"}), 400

    errors = _assistance_order_errors(payload)
    now = timeutil.utcnow()
    scheduled_at, timing_error = _parse_assistance_time(payload, service_name, now)
    if timing_error:
        errors["timing"] = timing_error
    if errors:
        return jsonify(status="error", errors=errors), 400

    current_price = money.from_db(service["unit_price"])
    if not shared.price_snapshot_matches(payload, current_price):
        return shared.price_updated_response(current_price, 1, unit_label="service")

    order_key = payload.get("order_key", "").strip()
    existing = order_queries.find_by_order_key(db, order_key)
    if existing is not None:
        return jsonify(status="ok", redirect=shared.confirmed_url(existing["order_id"]))

    return _place_assistance_order(db, service, payload, order_key, scheduled_at)


def _place_assistance_order(db, service, payload, order_key, scheduled_at):
    address = (payload.get("address") or "").strip()
    area = (payload.get("area") or "").strip() or None
    vehicle_type = (payload.get("vehicle_type") or "").strip()
    problem = (payload.get("note") or "").strip()
    note = f"{vehicle_type} · {problem}" if problem else vehicle_type
    latitude = payload.get("latitude")
    longitude = payload.get("longitude")
    total = money.from_db(service["unit_price"])
    now = timeutil.utcnow()
    is_asap = scheduled_at is None
    try:
        db.execute("BEGIN IMMEDIATE")
        order_id = order_queries.insert_order(
            db,
            user_id=g.current_user["user_id"],
            service_id=service["service_id"],
            order_key=order_key,
            quantity=1,
            total_amount=money.to_db(total),
            address=address,
            area=area,
            latitude=latitude,
            longitude=longitude,
            note=note,
            scheduled_at=timeutil.to_sql(scheduled_at) if scheduled_at else None,
        )
        tracking_queries.add_tracking(
            db, order_id, "Pending", timeutil.to_sql(now), latitude, longitude
        )
        if is_asap:
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
