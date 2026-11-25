"""Turns DB rows into the exact strings the customer screens show.
No SQL, no Flask request object."""

import math
from datetime import timedelta

from flask import url_for

from app import money, timeutil
from app.customer import scheduling, validation
from app.labels import order_status_label

ORDERS_PER_PAGE = 10
SHORT_SERVICE_NAMES = {"Engine oil delivery": "Engine oil"}

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


def _initials(name):
    words = name.split()
    return "".join(word[0] for word in words[:2]).upper()


def driver_template_context(order_row):
    """Driver card context shared by Order confirmed and Track order."""
    if order_row["driver_id"] is None:
        return {"assigned": False}
    distance = f"{float(money.from_db(order_row['distance_km'])):.1f}"
    return {
        "assigned": True,
        "driver_name": order_row["driver_name"],
        "initials": _initials(order_row["driver_name"]),
        "vehicle_no": order_row["vehicle_no"],
        "rating_label": f"{float(order_row['driver_rating']):.1f}",
        "eta_minutes": order_row["eta_minutes"],
        "distance_label": f"{distance} km away",
        "phone": order_row["driver_phone"],
    }


def driver_api_payload(order_row):
    """Same driver facts as driver_template_context, shaped for the
    /api/orders/<id>/status JSON (app/api/__init__.py)."""
    if order_row["driver_id"] is None:
        return None
    distance = f"{float(money.from_db(order_row['distance_km'])):.1f}"
    return {
        "name": order_row["driver_name"],
        "initials": _initials(order_row["driver_name"]),
        "vehicle_no": order_row["vehicle_no"],
        "rating_label": f"{float(order_row['driver_rating']):.1f}",
        "eta_minutes": order_row["eta_minutes"],
        "distance_label": f"{distance} km away",
        "phone": order_row["driver_phone"],
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
        "status_api_url": url_for("api.order_status", order_id=order_row["order_id"]),
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


def order_icon_name(order_row):
    """My orders / Track order icon: emergency orders always show the
    triangle warning icon, whatever the underlying fuel type is."""
    if order_row["is_emergency"]:
        return "triangle-exclamation"
    return SERVICE_ICONS.get(order_row["service_name"], "gas-pump")


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


def _order_service_and_quantity(order_row):
    """My orders' service name and quantity, split so the table can show them
    in separate columns: emergency orders always say "Emergency fuel",
    whatever the underlying fuel type is (docs/FIGMA.md 36:3674)."""
    quantity = order_row["quantity"]
    if order_row["is_emergency"]:
        return "Emergency fuel", f"{int(round(quantity))} L"
    name = SHORT_SERVICE_NAMES.get(order_row["service_name"], order_row["service_name"])
    if order_row["service_unit"] != "litre":
        return name, "1 service"
    return name, f"{int(round(quantity))} L"


def my_orders_row(order_row):
    service_label, quantity_label = _order_service_and_quantity(order_row)
    return {
        "order_id": order_row["order_id"],
        "order_number": f"ORD-{order_row['order_id']:04d}",
        "service_label": service_label,
        "quantity_label": quantity_label,
        "title": f"{service_label} · {quantity_label}",
        "date_label": timeutil.format_date(timeutil.from_sql(order_row["created_at"])),
        "amount_label": money.format_pkr(money.from_db(order_row["total_amount"])),
        "status": order_row["status"],
        "status_label": order_status_label(order_row["status"]),
        "icon": order_icon_name(order_row),
        "is_emergency": bool(order_row["is_emergency"]),
        "track_url": url_for("customer.order_track", order_id=order_row["order_id"]),
    }


def my_orders_context(order_rows, show, page, total_count):
    """My orders (FR-08): filter chips, newest-first rows, 10 per page."""
    total_pages = max(1, math.ceil(total_count / ORDERS_PER_PAGE))
    page = min(max(page, 1), total_pages)
    showing_label = None
    if total_count:
        start = (page - 1) * ORDERS_PER_PAGE + 1
        end = min(page * ORDERS_PER_PAGE, total_count)
        showing_label = f"Showing {start}–{end} of {total_count} orders"
    return {
        "rows": [my_orders_row(row) for row in order_rows],
        "show": show,
        "page": page,
        "total_pages": total_pages,
        "showing_label": showing_label,
        "is_empty": total_count == 0,
    }


STATUS_ORDER = ("Pending", "Assigned", "On the Way", "Delivered")
STEP_LABELS = {
    "Pending": "Placed",
    "Assigned": "Assigned",
    "On the Way": "On the way",
    "Delivered": "Delivered",
}


def _step_times(tracking_rows):
    """First time each status was reached, keyed by the DB status word."""
    times = {}
    for row in tracking_rows:
        times.setdefault(row["status"], row["updated_at"])
    return times


def _build_steps(status, step_times):
    """Order progress (docs/FIGMA.md Status steps 11:566): done = passed,
    current = the order's status now, upcoming = not reached yet. Cancelled
    orders show an alert banner instead (no steps)."""
    if status == "Cancelled":
        return []
    current_index = STATUS_ORDER.index(status)
    steps = []
    for index, db_status in enumerate(STATUS_ORDER):
        if index < current_index:
            state = "done"
        elif index == current_index:
            state = "current"
        else:
            state = "upcoming"
        time_value = step_times.get(db_status)
        steps.append(
            {
                "key": db_status.lower().replace(" ", "_"),
                "label": STEP_LABELS[db_status],
                "state": state,
                "time_label": timeutil.format_time(timeutil.from_sql(time_value))
                if time_value
                else "Waiting",
            }
        )
    return steps


def _unit_price_label(order_row):
    unit = "litre" if order_row["service_unit"] == "litre" else "service"
    return f"{money.format_pkr(money.from_db(order_row['unit_price']))} / {unit}"


def _eta_target(order_row):
    if order_row["driver_id"] is None or order_row["assigned_at"] is None:
        return None
    return timeutil.from_sql(order_row["assigned_at"]) + timedelta(minutes=order_row["eta_minutes"])


def eta_text(eta_target, now):
    """'about 9 min', then 'Arriving any moment' once the predicted time has passed."""
    if eta_target is None:
        return None
    remaining = max(0, round((eta_target - now).total_seconds() / 60))
    return "Arriving any moment" if remaining <= 0 else f"about {remaining} min"


def blank_steps():
    """4-row skeleton for Track order's steps card when an order is already
    Cancelled at page load (no steps to show, but the card stays in the DOM
    in case a later page keeps the same layout)."""
    return [
        {
            "key": db_status.lower().replace(" ", "_"),
            "label": STEP_LABELS[db_status],
            "state": "upcoming",
            "time_label": "Waiting",
        }
        for db_status in STATUS_ORDER
    ]


def track_order_context(order_row, tracking_rows, now=None):
    """Track order (FR-07, screen 10): steps, ETA, driver and the finished states."""
    now = now or timeutil.utcnow()
    status = order_row["status"]
    is_cancelled = status == "Cancelled"
    is_delivered = status == "Delivered"
    step_times = _step_times(tracking_rows)
    eta_target = _eta_target(order_row)

    delivered_label = None
    delivered_sub_label = None
    if is_delivered:
        delivered_value = step_times.get("Delivered")
        if delivered_value is not None:
            delivered_label = (
                f"Delivered at {timeutil.format_time(timeutil.from_sql(delivered_value))}"
            )
        total_label = money.format_pkr(money.from_db(order_row["total_amount"]))
        delivered_sub_label = f"Paid cash · {total_label}. Thank you for using AJORA."

    cancelled_label = None
    reason_label = None
    if is_cancelled:
        cancelled_value = step_times.get("Cancelled")
        if cancelled_value is not None:
            cancelled_label = (
                f"Order cancelled at {timeutil.format_time(timeutil.from_sql(cancelled_value))}"
            )
        reason = order_row["cancel_reason"]
        reason_label = (
            f"Reason: {reason}. Nothing was charged." if reason else "Nothing was charged."
        )

    return {
        "order_id": order_row["order_id"],
        "order_number": f"ORD-{order_row['order_id']:04d}",
        "service_line": _service_line(order_row),
        "status": status,
        "status_label": order_status_label(status),
        "is_finished": is_cancelled or is_delivered,
        "is_cancelled": is_cancelled,
        "is_delivered": is_delivered,
        "steps": _build_steps(status, step_times),
        "show_eta": not (is_cancelled or is_delivered) and order_row["driver_id"] is not None,
        "show_searching": not (is_cancelled or is_delivered) and order_row["driver_id"] is None,
        "eta_text": eta_text(eta_target, now),
        "eta_target_iso": eta_target.isoformat() if eta_target else None,
        "eta_updated_label": timeutil.format_time(now),
        "delivered_label": delivered_label,
        "delivered_sub_label": delivered_sub_label,
        "cancelled_label": cancelled_label,
        "reason_label": reason_label,
        "summary_open": is_cancelled,
        "summary_price_label": _unit_price_label(order_row),
        "summary_total_label": money.format_pkr(money.from_db(order_row["total_amount"])),
        "summary_address": order_row["address"],
        "status_api_url": url_for("api.order_status", order_id=order_row["order_id"]),
        "repeat_url": url_for("customer.order_repeat", order_id=order_row["order_id"]),
    }


REPEAT_FUEL_FORM = "customer.order_fuel"
REPEAT_GENERATOR_FORM = "customer.order_generator"
REPEAT_ASSISTANCE_FORM = "customer.order_assistance"
REPEAT_EMERGENCY_FORM = "customer.order_emergency"


def repeat_target(order_row):
    """Which order form /app/orders/<id>/repeat should reopen, pre-filled
    with this order's service, quantity, address, area and note (location is
    asked again - CLAUDE.md business rules)."""
    args = {
        "address": order_row["address"] or "",
        "area": order_row["area"] or "",
        "note": order_row["note"] or "",
        "litres": int(round(order_row["quantity"])),
    }
    if order_row["is_emergency"]:
        return REPEAT_EMERGENCY_FORM, {"litres": args["litres"], "note": args["note"]}
    name = order_row["service_name"]
    if name in ("Petrol", "Diesel"):
        return REPEAT_FUEL_FORM, {**args, "fuel_type": name}
    if name == "Generator fuel":
        generator_type = (
            order_row["note"] if order_row["note"] in validation.GENERATOR_TYPES else None
        )
        args.pop("note")
        if generator_type:
            args["type"] = generator_type
        return REPEAT_GENERATOR_FORM, args
    args.pop("litres")
    return REPEAT_ASSISTANCE_FORM, {**args, "service": name}


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
