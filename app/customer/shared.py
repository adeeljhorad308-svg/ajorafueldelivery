"""Helpers reused by every order-placement route (fuel, emergency, generator, assistance)."""

from decimal import InvalidOperation

from flask import jsonify, url_for

from app import money
from app.queries import services as service_queries


def fuel_services(db):
    rows = (service_queries.find_by_name(db, "Petrol"), service_queries.find_by_name(db, "Diesel"))
    return [row for row in rows if row and row["available"]]


def find_fuel_service(db, fuel_type):
    if fuel_type not in ("Petrol", "Diesel"):
        return None
    return service_queries.find_by_name(db, fuel_type)


def fuel_options(rows):
    return [
        {
            "name": row["name"],
            "unit_price": money.to_db(money.from_db(row["unit_price"])),
            "price_label": f"{money.format_pkr(money.from_db(row['unit_price']))} / litre",
        }
        for row in rows
    ]


def price_snapshot_matches(payload, current_price):
    raw = payload.get("price_snapshot")
    if not raw:
        return False
    try:
        return money.parse_amount(raw) == current_price
    except InvalidOperation:
        return False


def price_updated_response(current_price, quantity, unit_label="litre"):
    total = money.from_db(current_price * quantity)
    return jsonify(
        status="price_updated",
        unit_price=money.to_db(current_price),
        formatted_price=f"{money.format_pkr(current_price)} / {unit_label}",
        total=money.to_db(total),
        formatted_total=money.format_pkr(total),
    ), 409


def confirmed_url(order_id):
    return url_for("customer.order_confirmed", order_id=order_id)
