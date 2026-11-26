"""Turns open-emergency order rows into the strings the Emergency requests
screen shows (docs/SPEC.md screen 15, docs/FIGMA.md 44:2614-44:3275). No SQL,
no Flask request object (except url_for, needed for Call/Assign/Open links)."""

from flask import url_for

from app import money, phone, timeutil
from app.admin.presentation import initials, quantity_label
from app.labels import order_status_label

OVERDUE_MINUTES = 5


def _waiting_minutes(created_at, now):
    return max(0, round((now - created_at).total_seconds() / 60))


def emergency_card(order_row, now):
    created_at = timeutil.from_sql(order_row["created_at"])
    waiting_minutes = _waiting_minutes(created_at, now)
    is_overdue = waiting_minutes > OVERDUE_MINUTES
    order_number = f"ORD-{order_row['order_id']:04d}"
    # sqlite3.Row has no real dict `in`: `"x" in row` checks row *values*, not
    # column names, so the column list is the only correct way to ask this.
    has_driver = "driver_name" in order_row.keys()  # noqa: SIM118
    return {
        "order_id": order_row["order_id"],
        "order_number": order_number,
        "created_at_iso": created_at.isoformat(),
        "waiting_minutes": waiting_minutes,
        "waiting_label": f"Waiting {waiting_minutes} min",
        "is_overdue": is_overdue,
        "overdue_label": "Waiting over 5 min · assign a driver now",
        "status": order_row["status"],
        "status_label": order_status_label(order_row["status"]),
        "title": f"{order_number} · {order_row['service_name']} · {quantity_label(order_row)}",
        "placed_meta": (
            f"Placed {timeutil.format_time(created_at)} · "
            f"{money.format_pkr(money.from_db(order_row['total_amount']))}"
        ),
        "customer_initials": initials(order_row["customer_name"]),
        "customer_name": order_row["customer_name"],
        "customer_phone_label": phone.format_phone(order_row["customer_phone"]),
        "call_href": f"tel:{order_row['customer_phone']}",
        "address_line": (
            f"{order_row['address']} · {order_row['area']}"
            if order_row["address"]
            else (order_row["area"] or "—")
        ),
        "vehicle_note": order_row["note"] or None,
        "driver_name": order_row["driver_name"] if has_driver else None,
        "detail_url": url_for("admin.order_detail", order_id=order_row["order_id"]),
    }


def header_summary(cards):
    """(title, caption) for the page header - docs/FIGMA.md 44:2614 shows a
    bold count + oldest-wait line next to a lighter explainer; the empty
    state (44:3275) has no count to show, so it only has the explainer."""
    if not cards:
        return None, "Updates every 15 seconds"
    oldest_wait = max(card["waiting_minutes"] for card in cards)
    # "open" is an adjective here ("N open [requests]"), not a noun, so it
    # never takes a plural "s" (docs/FIGMA.md 44:2614: "2 open ...").
    title = f"{len(cards)} open · oldest waiting {oldest_wait} min"
    return title, "Oldest first · unassigned over 5 min goes to the top"


def sort_cards(cards):
    """Oldest first, but a request waiting over 5 minutes always moves to the
    top (docs/SPEC.md screen 15's 5-minute rule) - oldest-first within each
    group is "waited longest first", not insertion order, since a card's
    created_at can be backdated independently of its order_id."""
    return sorted(
        cards, key=lambda card: (not card["is_overdue"], -card["waiting_minutes"], card["order_id"])
    )
