"""Turns DB rows into the exact strings Customer home (screen 4) shows.
No SQL, no Flask request object."""

from flask import url_for

from app import money, timeutil
from app.labels import order_status_label

SERVICE_ICONS = {
    "Petrol": "gas-pump",
    "Diesel": "gas-pump",
    "Generator fuel": "plug-circle-bolt",
    "Engine oil delivery": "oil-can",
    "Battery help": "car-battery",
    "Tyre help": "custom-tyre",
    "Car wash": "spray-can-sparkles",
}
# Routes not built yet this session still 404 cleanly through the app's own
# error page, rather than crashing url_for() for an unregistered endpoint.
FUTURE_ORDER_ROUTES = {
    "Generator fuel": "/app/order/generator",
    "Engine oil delivery": "/app/order/assistance",
    "Battery help": "/app/order/assistance",
    "Tyre help": "/app/order/assistance",
    "Car wash": "/app/order/assistance",
}


def build_home_tiles(services):
    """Figma's Customer home shows 7 fixed tiles: Petrol+Diesel share one tile
    and Generator fuel's price is reused for a second, routeless Machinery
    fuel tile (screen 7 covers both types from the same services row)."""
    by_name = {row["name"]: row for row in services}
    tiles = []
    fuel = by_name.get("Petrol") or by_name.get("Diesel")
    if fuel:
        tiles.append(_fuel_tile(fuel))
    generator = by_name.get("Generator fuel")
    if generator:
        tiles.append(_service_tile(generator, "Generator fuel", "From {price} / litre"))
        tiles.append(_service_tile(generator, "Machinery fuel", "From {price} / litre", "tractor"))
    for name in ("Engine oil delivery", "Battery help", "Tyre help", "Car wash"):
        row = by_name.get(name)
        if row:
            label = "Engine oil" if name == "Engine oil delivery" else name
            tiles.append(_service_tile(row, label, "{price} / service"))
    return tiles


def _fuel_tile(service):
    price = money.format_pkr(money.from_db(service["unit_price"]))
    return {
        "name": "Petrol and diesel",
        "icon": "gas-pump",
        "price": f"From {price} / litre",
        "href": url_for("customer.order_fuel"),
    }


def _service_tile(service, label, price_template, icon=None):
    price = money.format_pkr(money.from_db(service["unit_price"]))
    return {
        "name": label,
        "icon": icon or SERVICE_ICONS.get(service["name"], "gas-pump"),
        "price": price_template.format(price=price),
        "href": FUTURE_ORDER_ROUTES.get(service["name"], "/app"),
    }


def active_order_card(order_row):
    if order_row is None:
        return None
    created_at = timeutil.from_sql(order_row["created_at"])
    card = {
        "order_number": f"ORD-{order_row['order_id']:04d}",
        "service_name": order_row["service_name"],
        "quantity_label": f"{int(round(order_row['quantity']))} L",
        "placed_label": f"placed {timeutil.format_time(created_at)}",
        "status": order_row["status"],
        "status_label": order_status_label(order_row["status"]),
        "track_url": f"/app/orders/{order_row['order_id']}",
        "has_assignment": order_row["driver_id"] is not None,
    }
    if card["has_assignment"]:
        distance = f"{float(money.from_db(order_row['distance_km'])):.1f}"
        card["eta_minutes"] = order_row["eta_minutes"]
        card["driver_line"] = (
            f"{order_row['driver_name']} · {order_row['vehicle_no']} · {distance} km away"
        )
    return card


def last_order_card(order_row):
    if order_row is None:
        return None
    created_at = timeutil.from_sql(order_row["created_at"])
    total = money.format_pkr(money.from_db(order_row["total_amount"]))
    if order_row["service_unit"] == "litre":
        quantity = f"{int(round(order_row['quantity']))} L · "
    else:
        quantity = ""
    return {
        "date_label": timeutil.format_date(created_at),
        "summary": f"{order_row['service_name']} · {quantity}{total}",
        "repeat_href": url_for("customer.order_fuel")
        if order_row["service_name"] in ("Petrol", "Diesel")
        else None,
    }
