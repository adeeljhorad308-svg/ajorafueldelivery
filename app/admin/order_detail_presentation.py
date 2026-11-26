"""Turns an order row (and its driver/tracking rows) into the exact strings
Order details and pop-ups 2/3 show (docs/SPEC.md screen 14, docs/FIGMA.md
41:1797-41:2855, 42:2169-42:2814). No SQL, no Flask request object."""

from app import dispatch, money, phone, timeutil
from app.admin.presentation import generator_word, initials, quantity_label
from app.customer import scheduling
from app.customer.validation import GENERATOR_TYPES
from app.labels import order_status_label

CANCEL_REASONS = (
    ("Customer asked", "Customer asked"),
    ("No driver available", "No driver available"),
    ("Wrong address", "Wrong address"),
    ("Duplicate order", "Duplicate order"),
    ("Other", "Other (type the reason)"),
)
CANCEL_OTHER_MAX_LENGTH = 200


def _move(action, to, label, icon, style):
    return {"action": action, "to": to, "label": label, "icon": icon, "style": style}


# Status buttons shown on Order details, in order (docs/SPEC.md screen 14's
# table). "assign" opens pop-up 2 directly; "status" and "cancel" open pop-up 3.
NEXT_MOVES = {
    "Pending": (
        _move("assign", "Assigned", "Assign driver", "user-check", "brand"),
        _move("cancel", "Cancelled", "Cancel order", None, "danger"),
    ),
    "Assigned": (
        _move("status", "On the Way", "Mark on the way", "truck-fast", "brand"),
        _move("status", "Pending", "Back to pending", "rotate-right", "outline"),
        _move("cancel", "Cancelled", "Cancel order", None, "danger"),
    ),
    "On the Way": (_move("status", "Delivered", "Mark delivered", "circle-check", "brand"),),
    "Delivered": (),
    "Cancelled": (),
}

# Plain status moves (not assign, not cancel) - also the server's allow-list
# for POST /admin/orders/<id>/status, so an illegal move is refused even when
# it is posted by hand (CLAUDE.md security: never trust the client).
ALLOWED_STATUS_MOVES = {
    ("Assigned", "On the Way"),
    ("Assigned", "Pending"),
    ("On the Way", "Delivered"),
}
CANCELLABLE_STATUSES = ("Pending", "Assigned")


def order_number(order_id):
    return f"ORD-{order_id:04d}"


def _service_display(order_row):
    if order_row["note"] in GENERATOR_TYPES:
        word = "Generator fuel" if order_row["note"] == "Generator" else order_row["note"]
        return f"{word} · {order_row['service_name']}"
    return generator_word(order_row)


def header(order_row):
    created_at = timeutil.from_sql(order_row["created_at"])
    return {
        "order_id": order_row["order_id"],
        "order_number": order_number(order_row["order_id"]),
        "placed_label": (
            f"Placed {timeutil.format_datetime(created_at)} · "
            f"{_service_display(order_row)} · {quantity_label(order_row)}"
        ),
        "status": order_row["status"],
        "status_label": order_status_label(order_row["status"]),
        "is_emergency": bool(order_row["is_emergency"]),
        "show_call_needed": not order_row["call_confirmed"],
    }


def _slot_label(dt):
    hour = timeutil.to_karachi(dt).hour
    for slot_hour, label in scheduling.SLOTS:
        if slot_hour == hour:
            return label
    return None


def _delivery_time_label(order_row):
    if order_row["scheduled_at"] is None:
        return "As soon as possible"
    start = timeutil.from_sql(order_row["scheduled_at"])
    return f"{timeutil.format_weekday_day_month(start)}, {_slot_label(start)}"


def _payment_label(order_row):
    return "Cash on delivery · paid" if order_row["status"] == "Delivered" else "Cash on delivery"


def _amount_row_label(order_row):
    if order_row["service_unit"] != "litre":
        return quantity_label(order_row)
    unit_price = money.format_pkr(money.from_db(order_row["unit_price"]))
    return f"{quantity_label(order_row)} × {unit_price}"


def order_info(order_row):
    rows = [
        ("Service", _service_display(order_row)),
        ("Quantity", _amount_row_label(order_row)),
        ("Amount", money.format_pkr(money.from_db(order_row["total_amount"]))),
        ("Payment", _payment_label(order_row)),
    ]
    if order_row["scheduled_at"] is not None or not order_row["is_emergency"]:
        rows.append(("Delivery time", _delivery_time_label(order_row)))
    note = None
    if (
        order_row["note"]
        and not order_row["is_emergency"]
        and order_row["note"] not in GENERATOR_TYPES
    ):
        note = order_row["note"]
    return {"rows": rows, "note": note}


def customer_info(order_row):
    return {
        "name": order_row["customer_name"],
        "phone_label": phone.format_phone(order_row["customer_phone"]),
        "call_href": f"tel:{order_row['customer_phone']}",
    }


def location_info(order_row):
    if order_row["is_emergency"]:
        return {
            "is_emergency": True,
            "rows": [("Vehicle", order_row["note"] or "—"), ("Area", order_row["area"] or "—")],
        }
    rows = [("Address", order_row["address"])]
    if order_row["area"]:
        rows.append(("Area", order_row["area"]))
    has_gps = order_row["latitude"] is not None and order_row["longitude"] is not None
    coordinates = None
    if has_gps:
        coordinates = f"{order_row['latitude']}, {order_row['longitude']}"
    return {
        "is_emergency": False,
        "rows": rows,
        "coordinates": coordinates,
        "no_gps_caption": None if has_gps else "No GPS location shared - area chosen from the list",
    }


def _driver_not_assigned_message(order_row):
    if order_row["status"] == "Cancelled":
        return ("This order was cancelled.", "No driver was assigned.")
    if not order_row["call_confirmed"]:
        return (
            "Call the customer first.",
            "A driver can be assigned after you mark the call done.",
        )
    if order_row["is_emergency"]:
        return (
            "No driver was free within range.",
            "Assign one now — this order is first in the queue.",
        )
    return ("No driver assigned yet.", "Assign one so the order can move forward.")


def driver_panel(order_row):
    if order_row["driver_id"] is None:
        title, message = _driver_not_assigned_message(order_row)
        return {"assigned": False, "message_title": title, "message_body": message}
    distance_km = money.from_db(order_row["distance_km"]) if order_row["distance_km"] else None
    return {
        "assigned": True,
        "initials": initials(order_row["driver_name"]),
        "driver_name": order_row["driver_name"],
        "rating_label": f"{float(order_row['driver_rating']):.1f}",
        "vehicle_no": order_row["driver_vehicle_no"],
        "phone": order_row["driver_phone"],
        "distance_label": f"{distance_km} km away" if distance_km is not None else "—",
        "eta_minutes": order_row["eta_minutes"],
        "can_change": order_row["status"] == "Assigned",
        "delivered": order_row["status"] == "Delivered",
        "delivered_at_label": (
            timeutil.format_time(timeutil.from_sql(order_row["completed_at"]))
            if order_row["status"] == "Delivered" and order_row["completed_at"]
            else None
        ),
    }


def route_stops(db, order_row):
    """Stop list for a driver with more than one open order (docs/SPEC.md:
    "Stop 2 of 3" via the nearest-neighbour function) - only while this order
    itself is still open, not for a driver's later, unrelated deliveries."""
    if order_row["driver_id"] is None or order_row["status"] not in ("Assigned", "On the Way"):
        return None
    from app.queries import admin_orders as order_queries  # local: avoid a cycle at import time

    open_orders = order_queries.list_open_orders_for_driver(db, order_row["driver_id"])
    if len(open_orders) < 2:
        return None
    stops = [
        {
            "order_id": row["order_id"],
            "latitude": row["latitude"]
            if row["latitude"] is not None
            else dispatch.order_location(row)[0],
            "longitude": row["longitude"]
            if row["longitude"] is not None
            else dispatch.order_location(row)[1],
            "area": row["area"] or "—",
            "label": f"{row['service_name']} {quantity_label(row)}",
        }
        for row in open_orders
    ]
    ordered = dispatch.nearest_neighbour_route(
        order_row["driver_latitude"], order_row["driver_longitude"], stops
    )
    total = len(ordered)
    result = []
    current_position_label = None
    for position, stop in enumerate(ordered, start=1):
        is_current = stop["order_id"] == order_row["order_id"]
        if is_current:
            sub = "This order · next stop" if position == 1 else "This order"
            current_position_label = f"stop {position} of {total}"
        else:
            sub = stop["label"] + (" · after this one" if position == total else "")
        result.append(
            {
                "order_number": order_number(stop["order_id"]),
                "area": stop["area"],
                "subtitle": sub,
                "is_current": is_current,
            }
        )
    return {"current_position_label": current_position_label, "stops": result}


def _tracking_row_subtext(order_row, status, is_first_pending):
    if status == "Pending":
        return "By the customer" if is_first_pending else "By the admin"
    if status == "Assigned":
        if order_row["driver_name"] and order_row["distance_km"] is not None:
            distance_km = money.from_db(order_row["distance_km"])
            eta = order_row["eta_minutes"]
            return f"Assigned to {order_row['driver_name']} · {distance_km} km · about {eta} min"
        return (
            f"Assigned to {order_row['driver_name']}"
            if order_row["driver_name"]
            else "By the admin"
        )
    if status == "On the Way":
        return "By the admin"
    if status == "Delivered":
        return "By the admin · driver is free again"
    if status == "Cancelled":
        return (
            f"By the admin · {order_row['cancel_reason']}"
            if order_row["cancel_reason"]
            else "By the admin"
        )
    return None


def tracking_history(rows, order_row):
    seen_pending = False
    history = []
    for row in rows:
        is_first_pending = row["status"] == "Pending" and not seen_pending
        if row["status"] == "Pending":
            seen_pending = True
        history.append(
            {
                "time_label": timeutil.format_time(timeutil.from_sql(row["updated_at"])),
                "status_label": "Placed" if is_first_pending else order_status_label(row["status"]),
                "subtext": _tracking_row_subtext(order_row, row["status"], is_first_pending),
            }
        )
    return history


def move_dialog_id(move):
    if move["action"] == "assign":
        return "dialog-assign"
    if move["action"] == "cancel":
        return "dialog-cancel"
    return f"dialog-status-{move['to'].lower().replace(' ', '-')}"


def next_step(order_row):
    status = order_row["status"]
    moves = NEXT_MOVES.get(status, ())
    result_moves = []
    for move in moves:
        disabled = move["action"] == "assign" and not order_row["call_confirmed"]
        result_moves.append({**move, "disabled": disabled, "dialog_id": move_dialog_id(move)})
    if moves:
        subtext = f'Only the moves allowed from "{order_status_label(status)}" are shown.'
    else:
        subtext = "This order is finished, so its status can't be changed."
    return {"subtext": subtext, "moves": result_moves, "has_moves": bool(moves)}
