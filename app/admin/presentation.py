"""Turns DB rows into the exact strings the admin screens show (docs/SPEC.md
screens 12-13). No SQL, no Flask request object (except url_for/current_app,
needed for links and the sidebar's graceful degrade)."""

import math

from flask import current_app, url_for

from app import money, phone, timeutil
from app.admin.filters import ALLOWED_STATUSES
from app.customer.validation import GENERATOR_TYPES
from app.labels import order_status_label
from app.queries import admin_orders as order_queries

ALL_ORDERS_PER_PAGE = 20
DASHBOARD_LIST_LIMIT = 5

DATE_FILTER_OPTIONS = (
    ("today", "Today"),
    ("7days", "7 days"),
    ("30days", "30 days"),
    ("custom", "Custom"),
)


def sidebar_href(endpoint, **kwargs):
    """None while a sidebar page's route doesn't exist yet (later sessions),
    so the sidebar never guesses a URL or crashes url_for (CLAUDE.md design
    gate: never guess a layout or placeholder UI)."""
    if endpoint in current_app.view_functions:
        return url_for(endpoint, **kwargs)
    return None


def status_filter_options():
    return [(status, order_status_label(status)) for status in ALLOWED_STATUSES]


def service_filter_options(services):
    """Real services from the database for the All orders Service filter
    (docs/FIGMA.md 39:714) - Emergency has its own switch, so it is not a
    choice here even though it shares the Petrol/Diesel service rows."""
    return [("", "All services")] + [(row["service_id"], row["name"]) for row in services]


def _delta_note(today_count, yesterday_count):
    delta = today_count - yesterday_count
    if delta > 0:
        return f"{delta} more than yesterday"
    if delta < 0:
        return f"{abs(delta)} fewer than yesterday"
    return "Same as yesterday"


def dashboard_stat_cards(
    today_count,
    yesterday_count,
    emergencies_open,
    oldest_wait_minutes,
    sales_amount,
    available_drivers,
    busy_drivers,
    total_drivers,
):
    emergency_note = (
        f"Oldest waiting {oldest_wait_minutes} min"
        if emergencies_open
        else "No emergencies waiting"
    )
    free_note = f"{busy_drivers} are on a delivery" if busy_drivers else "All drivers are free"
    return [
        {
            "label": "Orders today",
            "value": str(today_count),
            "note": _delta_note(today_count, yesterday_count),
            "tone": "default",
            "icon": "clipboard-list",
        },
        {
            "label": "Open emergencies",
            "value": str(emergencies_open),
            "note": emergency_note,
            "tone": "alert" if emergencies_open else "default",
            "icon": "triangle-exclamation",
        },
        {
            "label": "Sales today",
            "value": money.format_pkr(sales_amount),
            "note": "Delivered orders only",
            "tone": "default",
            "icon": "money-bill-wave",
        },
        {
            "label": "Free drivers",
            "value": f"{available_drivers} of {total_drivers}",
            "note": free_note,
            "tone": "default",
            "icon": "id-card",
        },
    ]


def emergency_bar(emergencies_open, oldest_wait_minutes, action_href):
    if not emergencies_open:
        return None
    plural = "request" if emergencies_open == 1 else "requests"
    return {
        "title": f"{emergencies_open} emergency {plural} waiting",
        "message": f"Oldest is waiting {oldest_wait_minutes} min. Assign a driver now.",
        "action_href": action_href,
    }


def _service_label(order_row):
    return "Emergency fuel" if order_row["is_emergency"] else order_row["service_name"]


def _quantity_label(order_row):
    """All orders' Qty column (docs/FIGMA.md 39:714): just the count for a
    one-off service - "1 service" is the customer-side wording
    (app/customer/presentation.py), not this narrower admin column's."""
    if order_row["service_unit"] != "litre":
        return str(int(round(order_row["quantity"])))
    return f"{int(round(order_row['quantity']))} L"


def _generator_word(order_row):
    """Due soon / Call needed show the generator subtype ("Tube well",
    "Tractor or harvester") instead of the service name - every order above
    the 200 L call threshold is a generator/machinery order."""
    if order_row["service_name"] == "Generator fuel" and order_row["note"] in GENERATOR_TYPES:
        return order_row["note"]
    return order_row["service_name"]


def _driver_display(order_row):
    if order_row["driver_id"] is not None:
        return order_row["driver_name"], "normal"
    if not order_row["call_confirmed"]:
        return "Call needed", "warning"
    return "Not assigned", "muted"


def _row_time_label(created_at, now):
    if timeutil.is_same_karachi_day(created_at, now):
        return timeutil.format_time(created_at)
    return timeutil.format_day_month(created_at)


def _chip_status(order_row):
    """Table rows show "Emergency" instead of the real status while the
    emergency is still open (docs/FIGMA.md Table row 14:936 / Status chip
    10:345) - the order's actual status still drives is_pinned and the
    allowed next moves on Order details."""
    if order_row["is_emergency"] and order_row["status"] in order_queries.OPEN_STATUSES:
        return "Emergency", "Emergency"
    return order_row["status"], order_status_label(order_row["status"])


def admin_order_row(order_row, now):
    """Shared row shape for the dashboard's Latest orders and All orders
    (table, tablet-folded table, and mobile cards all read from this one
    dict - only the template decides which fields to show)."""
    created_at = timeutil.from_sql(order_row["created_at"])
    driver_text, driver_variant = _driver_display(order_row)
    quantity_label = _quantity_label(order_row)
    amount_label = money.format_pkr(money.from_db(order_row["total_amount"]))
    time_label = _row_time_label(created_at, now)
    area = order_row["area"] or "—"
    is_pinned = (
        bool(order_row["is_emergency"]) and order_row["status"] in order_queries.OPEN_STATUSES
    )
    chip_status, chip_label = _chip_status(order_row)
    return {
        "order_id": order_row["order_id"],
        "order_number": f"ORD-{order_row['order_id']:04d}",
        "customer_name": order_row["customer_name"],
        "customer_phone": phone.format_phone(order_row["customer_phone"]),
        "service_label": _service_label(order_row),
        "quantity_label": quantity_label,
        "amount_label": amount_label,
        "area": area,
        "status": chip_status,
        "status_label": chip_label,
        "is_emergency": bool(order_row["is_emergency"]),
        "is_pinned": is_pinned,
        "driver_text": driver_text,
        "driver_variant": driver_variant,
        "time_label": time_label,
        "customer_meta": f"{area} · {time_label}",
        "service_meta": f"{quantity_label} · {amount_label}",
        "card_meta": f"{area} · {driver_text} · {time_label} · {amount_label}",
        "detail_url": url_for("admin.order_detail", order_id=order_row["order_id"]),
    }


def due_soon_item(order_row, now):
    scheduled_at = timeutil.from_sql(order_row["scheduled_at"])
    minutes_until = max(0, round((scheduled_at - now).total_seconds() / 60))
    slot_label = timeutil.format_time(scheduled_at)
    return {
        "title": (
            f"ORD-{order_row['order_id']:04d} · {_generator_word(order_row)} "
            f"{_quantity_label(order_row)}"
        ),
        "meta": f"{order_row['customer_name']} · {slot_label} · in {minutes_until} min",
        "detail_url": url_for("admin.order_detail", order_id=order_row["order_id"]),
    }


def call_needed_item(order_row):
    return {
        "title": (
            f"ORD-{order_row['order_id']:04d} · {_generator_word(order_row)} "
            f"{_quantity_label(order_row)}"
        ),
        "meta": f"{order_row['customer_name']} · {phone.format_phone(order_row['customer_phone'])}",
        "detail_url": url_for("admin.order_detail", order_id=order_row["order_id"]),
    }


def security_card(failed_logins_today, locked_rows, now):
    locked_count = len(locked_rows)
    if locked_count == 0:
        message = "No accounts are locked right now."
    else:
        until = timeutil.format_time(timeutil.from_sql(locked_rows[0]["locked_until"]))
        if locked_count == 1:
            message = f"1 customer account is locked until {until} after 5 wrong passwords."
        else:
            message = (
                f"{locked_count} customer accounts are locked, most recently until {until}, "
                "after 5 wrong passwords."
            )
    return {
        "failed_logins": failed_logins_today,
        "locked_count": locked_count,
        "message": message,
        "is_alert": locked_count > 0,
    }


def all_orders_pagination(total_count, page, per_page=ALL_ORDERS_PER_PAGE):
    total_pages = max(1, math.ceil(total_count / per_page))
    page = min(max(page, 1), total_pages)
    showing_label = None
    if total_count:
        start = (page - 1) * per_page + 1
        end = min(page * per_page, total_count)
        showing_label = f"Showing {start}–{end} of {total_count} orders"
    return {"page": page, "total_pages": total_pages, "showing_label": showing_label}
