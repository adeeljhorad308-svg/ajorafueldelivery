"""Turns driver rows into the strings the Drivers screen and pop-up 6 show
(docs/SPEC.md screen 18, pop-up 6, docs/FIGMA.md 47:4092-47:5720). No SQL, no
Flask request object (except url_for, needed for row/dialog action links)."""

from flask import url_for

from app.admin.presentation import initials
from app.labels import driver_status_label

_STATUS_TONES = {"Available": "success", "Busy": "warning", "Off Duty": "muted"}


def driver_row(row, open_orders_count):
    status = row["status"]
    return {
        "driver_id": row["driver_id"],
        "initials": initials(row["name"]),
        "name": row["name"],
        "phone_label": f"{row['phone'][:4]}-{row['phone'][4:]}",
        "phone": row["phone"],
        "vehicle_no": row["vehicle_no"],
        "area": row["area"] or "—",
        "status": status,
        "status_label": driver_status_label(status),
        "status_tone": _STATUS_TONES.get(status, "muted"),
        "open_orders": open_orders_count,
        "open_orders_label": (
            f"{open_orders_count} open order" + ("" if open_orders_count == 1 else "s")
        ),
        "rating_label": f"{float(row['rating']):.1f}" if row["rating"] is not None else "—",
        "on_duty": status == "Available",
        "can_toggle": status != "Busy",
        "update_url": url_for("admin.driver_update", driver_id=row["driver_id"]),
        "remove_url": url_for("admin.driver_remove", driver_id=row["driver_id"]),
        "edit_dialog_id": f"dialog-edit-driver-{row['driver_id']}",
        "remove_dialog_id": f"dialog-remove-driver-{row['driver_id']}",
    }


def drivers_summary(rows):
    available = sum(1 for row in rows if row["status"] == "Available")
    busy = sum(1 for row in rows if row["status"] == "Busy")
    off_duty = sum(1 for row in rows if row["status"] == "Off Duty")
    driver_word = "driver" if len(rows) == 1 else "drivers"
    return {
        "count": len(rows),
        "summary_label": (
            f"{len(rows)} {driver_word} · {available} available · {busy} busy · {off_duty} off duty"
        ),
    }


def remove_dialog_context(driver_row_context, open_order_rows):
    name = driver_row_context["name"]
    if open_order_rows:
        order_numbers = ", ".join(f"ORD-{row['order_id']:04d}" for row in open_order_rows)
        return {
            "dialog_id": driver_row_context["remove_dialog_id"],
            "title": f"Remove {name}?",
            "refused": True,
            "warning_title": f"{name} has an active order",
            "warning_message": f"Finish or reassign it first. Open orders: {order_numbers}.",
            "first_order_url": url_for(
                "admin.order_detail", order_id=open_order_rows[0]["order_id"]
            ),
            "first_order_number": f"ORD-{open_order_rows[0]['order_id']:04d}",
        }
    return {
        "dialog_id": driver_row_context["remove_dialog_id"],
        "title": f"Remove {name}?",
        "refused": False,
        "info_message": f"{name} will no longer be dispatched. Their order history stays.",
        "remove_url": driver_row_context["remove_url"],
    }
