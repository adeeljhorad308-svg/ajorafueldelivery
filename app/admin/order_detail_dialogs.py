"""Turns an order row into the exact strings pop-ups 2 (assign/change driver)
and 3 (update status / cancel) show (docs/SPEC.md Pop-ups 2-3, docs/FIGMA.md
42:2169-42:2814). No SQL, no Flask request object."""

from app.admin.order_detail_presentation import (
    CANCEL_OTHER_MAX_LENGTH,
    CANCEL_REASONS,
    NEXT_MOVES,
    order_number,
)
from app.admin.presentation import initials
from app.labels import order_status_label


def _driver_row(ranked_entry):
    driver = ranked_entry["driver"]
    return {
        "driver_id": driver["driver_id"],
        "initials": initials(driver["name"]),
        "name": driver["name"],
        "area": driver["area"] or "—",
        "rating_label": f"{float(driver['rating']):.1f}",
        "distance_label": f"{ranked_entry['distance_km']} km",
        "eta_label": f"{ranked_entry['eta_minutes']} min",
    }


def assign_dialog_context(order_row, ranked_drivers, total_drivers):
    rows = [_driver_row(entry) for entry in ranked_drivers]
    is_change = order_row["driver_id"] is not None
    for index, row in enumerate(rows):
        row["recommended"] = index == 0
        row["selected"] = index == 0
        row["extra"] = index >= 3
    title_prefix = "Change driver" if is_change else "Assign a driver"
    return {
        "dialog_id": "dialog-assign",
        "title": f"{title_prefix} · {order_number(order_row['order_id'])}",
        "subtitle": (
            f"3 nearest free drivers, closest first. Now: {order_row['driver_name']}."
            if is_change
            else (
                "Emergency · first in the queue"
                if order_row["is_emergency"]
                else "3 nearest free drivers, closest first."
            )
        ),
        "drivers": rows,
        "extra_count": max(0, len(rows) - 3),
        "has_drivers": bool(rows),
        "total_drivers": total_drivers,
        "default_label": f"Assign {rows[0]['name']}" if rows else "Assign",
        "info_message": (
            f"{rows[0]['name']} becomes Busy. {order_row['driver_name']} becomes Available again. "
            "The customer sees the new driver within 30 seconds."
            if is_change and rows
            else None
        ),
    }


_STATUS_MOVE_INFO = {
    "On the Way": (
        "The time is saved, a row is added to the tracking history, and "
        '{customer} sees "On the way" within 30 seconds.'
    ),
    "Pending": (
        "{driver} becomes Available again. The time is saved and a row is "
        "added to the tracking history."
    ),
    "Delivered": (
        "{driver} becomes Available again, and their location updates to the "
        "customer's address. A row is added to the tracking history."
    ),
}
_STATUS_MOVE_QUESTION = {
    "On the Way": "Mark {order} on the way?",
    "Pending": "Move {order} back to pending?",
    "Delivered": "Mark {order} delivered?",
}


def status_dialog_context(order_row, move):
    to_status = move["to"]
    info_template = _STATUS_MOVE_INFO[to_status]
    info_message = info_template.format(
        customer=order_row["customer_name"], driver=order_row["driver_name"] or "The driver"
    )
    return {
        "dialog_id": move["dialog_id"],
        "title": _STATUS_MOVE_QUESTION[to_status].format(order=order_number(order_row["order_id"])),
        "from_status": order_row["status"],
        "from_label": order_status_label(order_row["status"]),
        "to_status": to_status,
        "to_label": order_status_label(to_status),
        "info_message": info_message,
        "confirm_label": next(
            m["label"]
            for m in NEXT_MOVES[order_row["status"]]
            if m.get("to") == to_status and m["action"] == "status"
        ),
        "keep_label": f"Keep as {order_status_label(order_row['status'])}",
    }


def cancel_dialog_context(order_row):
    frees_driver = order_row["driver_id"] is not None
    info_message = "The customer sees the reason within 30 seconds."
    if frees_driver:
        info_message = f"{order_row['driver_name']} becomes Available again. {info_message}"
    return {
        "dialog_id": "dialog-cancel",
        "title": f"Cancel {order_number(order_row['order_id'])}?",
        "from_status": order_row["status"],
        "from_label": order_status_label(order_row["status"]),
        "reasons": CANCEL_REASONS,
        "other_max_length": CANCEL_OTHER_MAX_LENGTH,
        "info_message": info_message,
    }
