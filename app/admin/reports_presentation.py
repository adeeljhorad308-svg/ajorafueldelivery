"""Turns Reports query rows into the exact strings/shapes the template and
its Chart.js data blocks need (docs/SPEC.md screen 19). No SQL, no Flask
request object (except url_for, needed for the period/prev/next links)."""

from datetime import timedelta

from flask import url_for

from app import money, timeutil

PERIOD_LABELS = (("day", "Day"), ("week", "Week"), ("month", "Month"))
COUNTING_NOTE = (
    "Only Delivered and Cancelled orders from {range} are counted ({counted} of {placed} placed)."
    " Open orders join when they finish."
)


def period_controls(parsed):
    segments = [
        {
            "key": key,
            "label": label,
            "href": url_for("admin.reports", period=key),
            "selected": key == parsed["period"],
        }
        for key, label in PERIOD_LABELS
    ]
    return {
        "segments": segments,
        "previous_href": url_for(
            "admin.reports", period=parsed["period"], date=parsed["previous_date"]
        ),
        "next_href": url_for("admin.reports", period=parsed["period"], date=parsed["next_date"]),
        "range_label": _range_label(parsed),
    }


def _range_label(parsed):
    if parsed["period"] == "day":
        return timeutil.format_weekday_day_month_year(parsed["start"])
    if parsed["period"] == "month":
        return timeutil.format_report_month_label(parsed["start"])
    return timeutil.format_report_week_label(parsed["start"])


def _short_range_label(parsed):
    """Shorter form for the counting-rule note ("16 to 22 Nov"), vs. the
    period header's own "16–22 Nov 2026"."""
    if parsed["period"] == "day":
        return timeutil.format_date(parsed["start"])
    if parsed["period"] == "month":
        return timeutil.format_report_month_label(parsed["start"])
    last_day = parsed["start"] + timedelta(days=6)
    return f"{timeutil.to_karachi(parsed['start']).day} to {timeutil.format_date(last_day)}"


def stat_cards(row):
    avg_minutes = row["avg_delivery_minutes"]
    avg_label = f"{round(avg_minutes)} min" if avg_minutes is not None else "—"
    sales = money.from_db(row["sales"] if row["sales"] is not None else 0)
    return [
        {
            "label": "Total orders",
            "value": str(row["total_orders"] or 0),
            "note": "Delivered + Cancelled",
            "tone": "default",
            "icon": "clipboard-list",
        },
        {
            "label": "Delivered",
            "value": str(row["delivered"] or 0),
            "note": "Completed",
            "tone": "default",
            "icon": "circle-check",
        },
        {
            "label": "Cancelled",
            "value": str(row["cancelled"] or 0),
            "note": "By the admin",
            "tone": "default",
            "icon": "circle-xmark",
        },
        {
            "label": "Emergency",
            "value": str(row["emergency"] or 0),
            "note": "Of the counted orders",
            "tone": "default",
            "icon": "triangle-exclamation",
        },
        {
            "label": "Sales (PKR)",
            "value": money.format_pkr(sales),
            "note": "Delivered only",
            "tone": "default",
            "icon": "money-bill-wave",
        },
        {
            "label": "Avg delivery",
            "value": avg_label,
            "note": "Assigned to delivered",
            "tone": "default",
            "icon": "clock",
        },
    ]


def counting_note(row, parsed):
    return COUNTING_NOTE.format(
        range=_short_range_label(parsed),
        counted=row["total_orders"] or 0,
        placed=row["placed_total"] or 0,
    )


def _period_dates(parsed):
    start_date = timeutil.to_karachi(parsed["start"]).date()
    end_date = timeutil.to_karachi(parsed["end"]).date()
    days = (end_date - start_date).days
    return [start_date + timedelta(days=i) for i in range(days)]


def orders_per_day_chart(parsed, rows):
    by_day = {row["day"]: row["n"] for row in rows}
    dates = _period_dates(parsed)
    use_day_number = parsed["period"] == "month"
    labels = [str(day.day) if use_day_number else timeutil.weekday_abbrev(day) for day in dates]
    values = [by_day.get(day.isoformat(), 0) for day in dates]
    return {
        "labels": labels,
        "values": values,
        "rows": list(zip(labels, values, strict=True)),
    }


def orders_by_service_chart(rows):
    labels = [row["label"] for row in rows]
    values = [row["n"] for row in rows]
    return {
        "labels": labels,
        "values": values,
        "rows": list(zip(labels, values, strict=True)),
    }


def predicted_vs_actual_note(row):
    """Figma 48:5193's footer sentence, generic - the narrative aside about
    which weekday ran late is mock flavour text, not something this
    generically derives (CLAUDE.md: real words from docs/SPEC.md only, no
    filler text)."""
    if row["avg_predicted_minutes"] is None or row["avg_delivery_minutes"] is None:
        return None
    predicted = round(row["avg_predicted_minutes"], 1)
    actual = round(row["avg_delivery_minutes"], 1)
    return f"Smart dispatch predicted {predicted} min on average; drivers took {actual} min."


def predicted_vs_actual_chart(parsed, rows):
    by_day = {row["day"]: row for row in rows}
    dates = _period_dates(parsed)
    use_day_number = parsed["period"] == "month"
    predicted, actual = [], []
    for day in dates:
        row = by_day.get(day.isoformat())
        predicted.append(round(row["predicted"], 1) if row and row["predicted"] is not None else 0)
        actual.append(round(row["actual"], 1) if row and row["actual"] is not None else 0)
    labels = [str(day.day) if use_day_number else timeutil.weekday_abbrev(day) for day in dates]
    return {
        "labels": labels,
        "predicted": predicted,
        "actual": actual,
        "rows": list(zip(labels, predicted, actual, strict=True)),
    }
