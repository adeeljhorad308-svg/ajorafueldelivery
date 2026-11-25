"""Parses and validates All orders' query-string filters (docs/SPEC.md screen
13: filters live in the URL). No SQL here - app/queries/orders.py turns the
result into a parameterised WHERE clause."""

import re
from datetime import date, timedelta

from app import timeutil

ALLOWED_STATUSES = ("Pending", "Assigned", "On the Way", "Delivered", "Cancelled")
ALLOWED_SERVICES = ("fuel", "emergency", "generator", "assistance")
ALLOWED_DATES = ("today", "7days", "30days", "custom")
DEFAULT_DATE = "30days"
PER_PAGE = 20

_ORDER_NUMBER_RE = re.compile(r"(?i)^ord-?0*(\d+)$")


def _parse_search(raw):
    value = (raw or "").strip()
    if not value:
        return None, None
    match = _ORDER_NUMBER_RE.match(value)
    if match:
        return "order", int(match.group(1))
    digits = re.sub(r"\D", "", value)
    if digits:
        return "phone", digits
    return None, None


def _parse_custom_range(from_raw, to_raw, now):
    try:
        from_date = date.fromisoformat(from_raw) if from_raw else None
        to_date = date.fromisoformat(to_raw) if to_raw else None
    except ValueError:
        from_date = to_date = None
    if from_date is None and to_date is None:
        return timeutil.to_sql(now - timedelta(days=30)), None
    date_from = (
        timeutil.to_sql(timeutil.from_karachi_date_and_hour(from_date, 0)) if from_date else None
    )
    date_to = (
        timeutil.to_sql(timeutil.from_karachi_date_and_hour(to_date + timedelta(days=1), 0))
        if to_date
        else None
    )
    return date_from, date_to


def _date_bounds(mode, from_raw, to_raw, now):
    if mode == "today":
        return timeutil.to_sql(timeutil.start_of_karachi_day(now)), None
    if mode == "7days":
        return timeutil.to_sql(now - timedelta(days=7)), None
    if mode == "custom":
        return _parse_custom_range(from_raw, to_raw, now)
    return timeutil.to_sql(now - timedelta(days=30)), None


def parse_order_filters(args, now=None):
    now = now or timeutil.utcnow()
    statuses = tuple(value for value in args.getlist("status") if value in ALLOWED_STATUSES)
    service = args.get("service") or ""
    if service not in ALLOWED_SERVICES:
        service = ""
    date_mode = args.get("date") or DEFAULT_DATE
    if date_mode not in ALLOWED_DATES:
        date_mode = DEFAULT_DATE
    from_raw = args.get("from") or ""
    to_raw = args.get("to") or ""
    date_from, date_to = _date_bounds(date_mode, from_raw, to_raw, now)
    emergency_only = args.get("emergency") == "1"
    search_raw = (args.get("q") or "").strip()
    search_kind, search_value = _parse_search(search_raw)
    page = args.get("page", 1, type=int) or 1

    return {
        "statuses": statuses,
        "service": service,
        "date_mode": date_mode,
        "date_from": date_from,
        "date_to": date_to,
        "from_raw": from_raw,
        "to_raw": to_raw,
        "emergency_only": emergency_only,
        "search_kind": search_kind,
        "search_value": search_value,
        "search_raw": search_raw,
        "page": max(page, 1),
    }


def active_filter_count(filters):
    """How many filters the admin has changed from the defaults - the "Filters
    - N" button badge on tablet and mobile."""
    count = len(filters["statuses"])
    if filters["service"]:
        count += 1
    if filters["date_mode"] != DEFAULT_DATE:
        count += 1
    if filters["emergency_only"]:
        count += 1
    return count


def query_args(filters, **overrides):
    """This filter set as a query-string dict, for building page/column links
    that keep every other filter (docs/SPEC.md: filters live in the URL)."""
    args = {}
    if filters["statuses"]:
        args["status"] = list(filters["statuses"])
    if filters["service"]:
        args["service"] = filters["service"]
    if filters["date_mode"] != DEFAULT_DATE:
        args["date"] = filters["date_mode"]
    if filters["date_mode"] == "custom":
        if filters["from_raw"]:
            args["from"] = filters["from_raw"]
        if filters["to_raw"]:
            args["to"] = filters["to_raw"]
    if filters["emergency_only"]:
        args["emergency"] = "1"
    if filters["search_raw"]:
        args["q"] = filters["search_raw"]
    args.update(overrides)
    return args
