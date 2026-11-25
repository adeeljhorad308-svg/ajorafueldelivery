"""Turns DB rows into the exact strings Customer home (screen 4) shows.
No SQL, no Flask request object."""

from flask import url_for

from app import money, timeutil
from app.customer import scheduling, validation
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
# Home tile -> (endpoint, query args) so the right type/service is pre-picked
# on arrival (docs/SPEC.md screen 4 reactions).
ORDER_ROUTE_PRESETS = {
    "Generator fuel": ("customer.order_generator", {"type": "Generator"}),
    "Machinery fuel": ("customer.order_generator", {"type": "Tractor or harvester"}),
    "Engine oil delivery": ("customer.order_assistance", {"service": "Engine oil delivery"}),
    "Battery help": ("customer.order_assistance", {"service": "Battery help"}),
    "Tyre help": ("customer.order_assistance", {"service": "Tyre help"}),
    "Car wash": ("customer.order_assistance", {"service": "Car wash"}),
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
        tiles.append(
            _service_tile(
                generator, "Generator fuel", "From {price} / litre", preset_key="Generator fuel"
            )
        )
        tiles.append(
            _service_tile(
                generator,
                "Machinery fuel",
                "From {price} / litre",
                "tractor",
                preset_key="Machinery fuel",
            )
        )
    for name in ("Engine oil delivery", "Battery help", "Tyre help", "Car wash"):
        row = by_name.get(name)
        if row:
            label = "Engine oil" if name == "Engine oil delivery" else name
            tiles.append(_service_tile(row, label, "{price} / service", preset_key=name))
    return tiles


def _fuel_tile(service):
    price = money.format_pkr(money.from_db(service["unit_price"]))
    return {
        "name": "Petrol and diesel",
        "icon": "gas-pump",
        "price": f"From {price} / litre",
        "href": url_for("customer.order_fuel"),
    }


def _service_tile(service, label, price_template, icon=None, preset_key=None):
    price = money.format_pkr(money.from_db(service["unit_price"]))
    preset = ORDER_ROUTE_PRESETS.get(preset_key)
    href = url_for(preset[0], **preset[1]) if preset else "/app"
    return {
        "name": label,
        "icon": icon or SERVICE_ICONS.get(service["name"], "gas-pump"),
        "price": price_template.format(price=price),
        "href": href,
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


def emergency_href(open_emergency_row):
    """Customer home's Emergency button: an open emergency's own Track page,
    otherwise the Emergency fuel form (docs/SPEC.md screen 4 reactions)."""
    if open_emergency_row is None:
        return url_for("customer.order_emergency")
    return url_for("customer.order_track", order_id=open_emergency_row["order_id"])


def _slot_label_for(dt):
    hour = timeutil.to_karachi(dt).hour
    for slot_hour, label in scheduling.SLOTS:
        if slot_hour == hour:
            return label
    return None


def _service_line(order_row):
    quantity = order_row["quantity"]
    if order_row["service_unit"] != "litre":
        return order_row["service_name"]
    if order_row["note"] in validation.GENERATOR_TYPES:
        kind = order_row["note"].lower()
        return f"{order_row['service_name']} for {kind} · {int(round(quantity))} L"
    return f"{order_row['service_name']} · {int(round(quantity))} L"


def order_confirmed_context(order_row):
    """Order confirmed (screen 9): the order summary and which "what happens
    next" banners apply (they are additive, not mutually exclusive - a
    scheduled, above-200-litre generator order shows both)."""
    scheduled_at = order_row["scheduled_at"]
    scheduled_label = None
    if scheduled_at is not None:
        start = timeutil.from_sql(scheduled_at)
        slot_label = _slot_label_for(start)
        scheduled_label = f"Scheduled for {timeutil.format_weekday_day_month(start)}, {slot_label}"
    return {
        "order_id": order_row["order_id"],
        "order_number": f"ORD-{order_row['order_id']:04d}",
        "placed_label": timeutil.format_datetime(timeutil.from_sql(order_row["created_at"])),
        "status": order_row["status"],
        "status_label": order_status_label(order_row["status"]),
        "service_line": _service_line(order_row),
        "total_label": money.format_pkr(money.from_db(order_row["total_amount"])),
        "address": order_row["address"],
        "is_emergency": bool(order_row["is_emergency"]),
        "show_call_needed": not order_row["call_confirmed"],
        "show_scheduled": scheduled_at is not None,
        "scheduled_label": scheduled_label,
        "show_searching": (
            order_row["driver_id"] is None and order_row["call_confirmed"] and scheduled_at is None
        ),
        "status_api_url": url_for("api.order_status", order_id=order_row["order_id"]),
    }
