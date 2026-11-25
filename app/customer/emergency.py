"""Emergency fuel (screen 6, FR-04): max 10 L, one open emergency per
customer, top priority in dispatch."""

import secrets
import sqlite3

from flask import abort, g, jsonify, render_template, request, url_for

from app import dispatch, money, timeutil
from app.areas import area_names
from app.customer import bp, shared, validation
from app.db import get_db
from app.labels import order_status_label
from app.phone import format_phone
from app.queries import orders as order_queries
from app.queries import tracking as tracking_queries
from app.security import limiter, login_required


def _rate_limit_key():
    return f"user:{g.current_user['user_id']}"


def _open_emergency_context(order_row):
    if order_row is None:
        return None
    return {
        "order_number": f"ORD-{order_row['order_id']:04d}",
        "status_phrase": order_status_label(order_row["status"]).lower(),
        "track_url": url_for("customer.order_track", order_id=order_row["order_id"]),
    }


@bp.get("/app/order/emergency")
@login_required
def order_emergency():
    db = get_db()
    user_id = g.current_user["user_id"]
    fuel_services = shared.fuel_services(db)
    if not fuel_services:
        abort(404)
    return render_template(
        "customer/order_emergency.html",
        fuel_options=shared.fuel_options(fuel_services),
        areas=area_names(),
        order_key=secrets.token_urlsafe(24),
        phone=format_phone(g.current_user["phone"]),
        open_emergency=_open_emergency_context(
            order_queries.find_open_emergency_for_user(db, user_id)
        ),
        prefill_litres=shared.prefill_litres(request.args, 2, 10, 5),
        prefill_note=shared.prefill_text(request.args, "note", 200),
        prefill_area=shared.prefill_area(request.args),
        active_order_url=shared.active_order_url(db, user_id),
    )


def _emergency_order_errors(payload, litres):
    errors = {}
    if not validation.is_valid_emergency_litres(litres):
        errors["litres"] = "Emergency orders are limited to 10 litres"
    note = (payload.get("note") or "").strip()
    if not note or not validation.is_valid_note(note):
        errors["note"] = "Tell us your vehicle and where it is"
    has_location = payload.get("latitude") is not None and payload.get("longitude") is not None
    if not has_location and not validation.is_valid_area((payload.get("area") or "").strip()):
        errors["area"] = "We need your location to send the nearest driver"
    if not (payload.get("order_key") or "").strip():
        errors["order_key"] = "Reload the page and try again"
    return errors


@bp.post("/app/order/emergency")
@login_required
@limiter.limit("10/10 minutes", key_func=_rate_limit_key)
def order_emergency_submit():
    db = get_db()
    payload = request.get_json(silent=True) or {}

    fuel_type = payload.get("fuel_type")
    service = shared.find_fuel_service(db, fuel_type)
    if service is None or not service["available"]:
        return jsonify(status="error", errors={"fuel_type": "Choose petrol or diesel"}), 400

    litres = validation.parse_litres(payload.get("litres"))
    errors = _emergency_order_errors(payload, litres)
    if errors:
        return jsonify(status="error", errors=errors), 400

    current_price = money.from_db(service["unit_price"])
    if not shared.price_snapshot_matches(payload, current_price):
        return shared.price_updated_response(current_price, litres)

    order_key = payload.get("order_key", "").strip()
    existing = order_queries.find_by_order_key(db, order_key)
    if existing is not None:
        return jsonify(status="ok", redirect=shared.confirmed_url(existing["order_id"]))

    return _place_emergency_order(db, service, litres, payload, order_key)


def _already_open_response(order_row):
    return jsonify(
        status="already_open",
        message="You already have an open emergency request.",
        track_url=url_for("customer.order_track", order_id=order_row["order_id"]),
    ), 409


def _place_emergency_order(db, service, litres, payload, order_key):
    user_id = g.current_user["user_id"]
    area = (payload.get("area") or "").strip() or None
    note = (payload.get("note") or "").strip()
    latitude = payload.get("latitude")
    longitude = payload.get("longitude")
    address = area or "Current location (GPS)"
    total = money.from_db(money.from_db(service["unit_price"]) * litres)
    now = timeutil.utcnow()
    try:
        # IMMEDIATE so the one-open-emergency check and the dispatch read of
        # free drivers both see a consistent, locked snapshot.
        db.execute("BEGIN IMMEDIATE")
        already_open = order_queries.find_open_emergency_for_user(db, user_id)
        if already_open is not None:
            db.rollback()
            return _already_open_response(already_open)

        order_id = order_queries.insert_order(
            db,
            user_id=user_id,
            service_id=service["service_id"],
            order_key=order_key,
            quantity=litres,
            total_amount=money.to_db(total),
            address=address,
            area=area,
            latitude=latitude,
            longitude=longitude,
            note=note,
            is_emergency=1,
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
                "is_emergency": 1,
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
