"""Turns service rows into the strings Services and prices shows (docs/SPEC.md
screen 17, pop-up 5, docs/FIGMA.md 46:3411-46:4788). No SQL, no Flask request
object (except url_for, needed for row/dialog action links)."""

from flask import url_for

from app import money
from app.customer.presentation import SERVICE_ICONS

UNIT_LABELS = {"litre": "per litre", "service": "per service"}


def _unit_price_plain(service_row):
    """Plain digits for a hidden form field (no 'PKR' prefix, no thousands
    separator) - the quick on/off switch resubmits this unchanged."""
    return str(money.from_db(service_row["unit_price"]))


def service_row(service_row):
    price_label = money.format_pkr(money.from_db(service_row["unit_price"]))
    return {
        "service_id": service_row["service_id"],
        "icon": SERVICE_ICONS.get(service_row["name"], "gas-pump"),
        "name": service_row["name"],
        "category": service_row["category"],
        "unit": service_row["unit"],
        "unit_label": UNIT_LABELS[service_row["unit"]],
        "price_label": price_label,
        "price_number_label": price_label.removeprefix("PKR "),
        "unit_price_plain": _unit_price_plain(service_row),
        "available": bool(service_row["available"]),
        "card_meta": (
            f"{money.format_pkr(money.from_db(service_row['unit_price']))} "
            f"{UNIT_LABELS[service_row['unit']]} · {service_row['category']}"
        ),
        "update_url": url_for("admin.service_update", service_id=service_row["service_id"]),
        "edit_dialog_id": f"dialog-edit-service-{service_row['service_id']}",
        "turnoff_dialog_id": f"dialog-turnoff-service-{service_row['service_id']}",
    }


def services_summary(rows):
    available_count = sum(1 for row in rows if row["available"])
    service_word = "service" if len(rows) == 1 else "services"
    return {
        "count": len(rows),
        "available_count": available_count,
        "summary_label": f"{len(rows)} {service_word} · {available_count} shown to customers",
    }


def price_reminder(service_rows):
    """Reminder bar detail line (docs/SPEC.md screen 17's reminder bar): the
    current fuel prices, since emergency fuel reuses the Petrol price - there
    is no "last changed" column in the schema (CLAUDE.md Tables 35-40), so
    this never claims a date the database doesn't have. Takes the already
    presentation-shaped rows (service_row()), not raw DB rows."""
    fuel_rows = {row["name"]: row for row in service_rows if row["name"] in ("Petrol", "Diesel")}
    if not fuel_rows:
        return None
    parts = [
        f"{name} {fuel_rows[name]['price_label']}"
        for name in ("Petrol", "Diesel")
        if name in fuel_rows
    ]
    return f"{', '.join(parts)} per litre. Emergency fuel uses these prices."


def turnoff_dialog_context(service_row_context):
    name = service_row_context["name"]
    return {
        "dialog_id": service_row_context["turnoff_dialog_id"],
        "title": f"Turn off {name}?",
        "message": f"Customers will not see {name}. Turn it off?",
        "info_message": (
            f"Open {name} orders are not affected. You can turn it on again at any time."
        ),
        "submit_url": service_row_context["update_url"],
    }
