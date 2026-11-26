"""Turns customer rows into the strings the Customers screen and pop-up 4
show (docs/SPEC.md screen 16, pop-up 4, docs/FIGMA.md 45:2913-45:4714). No
SQL, no Flask request object (except url_for, needed for row/panel links)."""

import math

from flask import url_for

from app import money, phone, timeutil
from app.admin.presentation import generator_word, initials, quantity_label
from app.labels import order_status_label

PER_PAGE = 20


def customer_row(row):
    last_order_label = (
        timeutil.format_date(timeutil.from_sql(row["last_order_at"]))
        if row["last_order_at"]
        else "—"
    )
    is_active = bool(row["is_active"])
    return {
        "user_id": row["user_id"],
        "initials": initials(row["name"]),
        "name": row["name"],
        "phone_label": phone.format_phone(row["phone"]),
        "email": row["email"],
        "orders_count": row["orders_count"],
        "last_order_label": last_order_label,
        "is_active": is_active,
        "status_label": "Active" if is_active else "Blocked",
        "status_tone": "success" if is_active else "error",
        "detail_url": url_for("admin.customer_detail", user_id=row["user_id"]),
    }


def customers_pagination(total_count, page, per_page=PER_PAGE):
    total_pages = max(1, math.ceil(total_count / per_page))
    page = min(max(page, 1), total_pages)
    showing_label = None
    if total_count:
        start = (page - 1) * per_page + 1
        end = min(page * per_page, total_count)
        showing_label = f"Showing {start}–{end} of {total_count} customers"
    return {"page": page, "total_pages": total_pages, "showing_label": showing_label}


def _panel_order_row(row):
    service_label = "Emergency fuel" if row["is_emergency"] else generator_word(row)
    return {
        "order_number": f"ORD-{row['order_id']:04d}",
        "title": f"{service_label} · {quantity_label(row)}",
        "amount_label": money.format_pkr(money.from_db(row["total_amount"])),
        "status": row["status"],
        "status_label": order_status_label(row["status"]),
        "detail_url": url_for("admin.order_detail", order_id=row["order_id"]),
    }


def customer_panel_context(row, total_spent_raw, last_orders_rows):
    total_spent = (
        money.from_db(total_spent_raw) if total_spent_raw is not None else money.parse_amount(0)
    )
    is_active = bool(row["is_active"])
    return {
        "user_id": row["user_id"],
        "name": row["name"],
        "initials": initials(row["name"]),
        "is_active": is_active,
        "status_label": "Active" if is_active else "Blocked",
        "status_tone": "success" if is_active else "error",
        "since_label": (
            f"Customer since {timeutil.format_date(timeutil.from_sql(row['created_at']))}"
        ),
        "phone_label": phone.format_phone(row["phone"]),
        "email": row["email"],
        "orders_count": row["orders_count"],
        "total_spent_label": money.format_pkr(total_spent),
        "last_orders": [_panel_order_row(r) for r in last_orders_rows],
        "action": "unblock" if not is_active else "block",
        "action_label": "Unblock customer" if not is_active else "Block customer",
        "confirm_title": (f"Unblock {row['name']}?" if not is_active else f"Block {row['name']}?"),
        "confirm_message": (
            f"{row['name']} can sign in again right away."
            if not is_active
            else f"Blocking logs {row['name']} out everywhere at once. Old orders stay."
        ),
        "block_url": url_for("admin.customer_block", user_id=row["user_id"]),
    }
