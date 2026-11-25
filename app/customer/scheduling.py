"""Delivery day/slot picker for generator (next 7 days) and car wash (today's
remaining slots) forms. Pure functions, Asia/Karachi wall-clock time."""

from datetime import date, timedelta

from app import timeutil

CAR_WASH_MIN_HOURS_AHEAD = 2

# Fixed 2-hour slots, 8 am to 8 pm (docs/SPEC.md screen 7).
SLOTS = (
    (8, "8–10 am"),
    (10, "10 am–12 pm"),
    (12, "12–2 pm"),
    (14, "2–4 pm"),
    (16, "4–6 pm"),
    (18, "6–8 pm"),
)

_DAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def generator_days(now):
    """Next 7 days (today included), as {value, label} for a day chip grid."""
    today = timeutil.to_karachi(now).date()
    days = []
    for offset in range(7):
        day = today + timedelta(days=offset)
        days.append({"value": day.isoformat(), "label": f"{_DAY_NAMES[day.weekday()]} {day.day}"})
    return days


def generator_slots():
    return [{"value": str(hour), "label": label} for hour, label in SLOTS]


def is_valid_slot_hour(hour):
    return any(hour == slot_hour for slot_hour, _ in SLOTS)


def slot_datetime(date_iso, hour):
    """UTC datetime for a selected (date, slot start hour), or None if invalid."""
    try:
        day = date.fromisoformat(date_iso)
    except (TypeError, ValueError):
        return None
    if not is_valid_slot_hour(hour):
        return None
    return timeutil.from_karachi_date_and_hour(day, hour)


def car_wash_slots(now):
    """Today's remaining 2-hour slots, each marked available once its start
    time is at least CAR_WASH_MIN_HOURS_AHEAD away (server re-checks too)."""
    today = timeutil.to_karachi(now).date()
    earliest = timeutil.to_karachi(now) + timedelta(hours=CAR_WASH_MIN_HOURS_AHEAD)
    slots = []
    for hour, label in SLOTS:
        slot_start = timeutil.from_karachi_date_and_hour(today, hour)
        if timeutil.to_karachi(slot_start) + timedelta(hours=2) <= timeutil.to_karachi(now):
            continue
        slots.append(
            {
                "value": str(hour),
                "label": label,
                "available": timeutil.to_karachi(slot_start) >= earliest,
            }
        )
    return slots


def is_car_wash_time_valid(scheduled_at, now):
    return scheduled_at >= now + timedelta(hours=CAR_WASH_MIN_HOURS_AHEAD)
