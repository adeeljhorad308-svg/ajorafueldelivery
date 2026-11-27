"""UTC-aware datetime helpers matching SQLite's CURRENT_TIMESTAMP text format.

Every time comparison in the app (session idle/absolute checks, lockouts,
order and tracking history) goes through to_sql()/from_sql() so storage and
Python always agree on format. Asia/Karachi is used only for business rules
that depend on local time of day (dispatch) and for display formatting -
never for comparisons or storage.
"""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

KARACHI = ZoneInfo("Asia/Karachi")
SQL_FORMAT = "%Y-%m-%d %H:%M:%S"


def utcnow():
    return datetime.now(UTC)


def to_sql(dt):
    """Format a datetime the same way SQLite's CURRENT_TIMESTAMP does."""
    if dt.tzinfo is not None:
        dt = dt.astimezone(UTC).replace(tzinfo=None)
    return dt.strftime(SQL_FORMAT)


def from_sql(value):
    """Parse a CURRENT_TIMESTAMP-style (or isoformat) string as UTC-aware."""
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def to_karachi(dt):
    return dt.astimezone(KARACHI)


def from_karachi_date_and_hour(date_value, hour):
    """UTC-aware datetime for a Karachi wall-clock date and hour (delivery slot picker)."""
    local = datetime(date_value.year, date_value.month, date_value.day, hour, 0, tzinfo=KARACHI)
    return local.astimezone(UTC)


_MONTHS = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)  # fmt: skip


def format_date(dt):
    """'05 Oct 2026' in Asia/Karachi. Built by hand, not strftime, because the
    zero-padded day and un-padded hour (see format_time) have no portable
    strftime flag shared between Windows and Linux."""
    local = to_karachi(dt)
    return f"{local.day:02d} {_MONTHS[local.month - 1]} {local.year}"


def format_time(dt):
    """'7:40 pm' in Asia/Karachi."""
    local = to_karachi(dt)
    hour12 = local.hour % 12 or 12
    period = "am" if local.hour < 12 else "pm"
    return f"{hour12}:{local.minute:02d} {period}"


def format_datetime(dt):
    """'05 Oct 2026, 7:40 pm' in Asia/Karachi."""
    return f"{format_date(dt)}, {format_time(dt)}"


_WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def format_weekday_day_month(dt):
    """'Tue 24 Nov' in Asia/Karachi (scheduled delivery slot text)."""
    local = to_karachi(dt)
    return f"{_WEEKDAYS[local.weekday()]} {local.day} {_MONTHS[local.month - 1]}"


def format_weekday_date(dt):
    """'Sun, 22 Nov 2026' in Asia/Karachi (admin top bar)."""
    local = to_karachi(dt)
    return f"{_WEEKDAYS[local.weekday()]}, {format_date(dt)}"


def format_day_month(dt):
    """'19 Nov' in Asia/Karachi (admin tables, rows older than today)."""
    local = to_karachi(dt)
    return f"{local.day} {_MONTHS[local.month - 1]}"


def is_same_karachi_day(first, second):
    return to_karachi(first).date() == to_karachi(second).date()


def start_of_karachi_day(dt):
    """UTC-aware instant for local midnight on dt's Asia/Karachi calendar day."""
    local_date = to_karachi(dt).date()
    return from_karachi_date_and_hour(local_date, 0)


def start_of_karachi_week(dt):
    """UTC-aware instant for local midnight on the Monday of dt's Asia/Karachi
    calendar week (Reports screen, docs/SPEC.md FR-16)."""
    local_date = to_karachi(dt).date()
    monday = local_date - timedelta(days=local_date.weekday())
    return from_karachi_date_and_hour(monday, 0)


def start_of_karachi_month(dt):
    """UTC-aware instant for local midnight on the 1st of dt's Asia/Karachi
    calendar month (Reports screen)."""
    local_date = to_karachi(dt).date()
    return from_karachi_date_and_hour(local_date.replace(day=1), 0)


def add_karachi_months(dt, months):
    """Shift a Reports period anchor date by whole calendar months, clamped to
    the 1st (callers only ever pass a month's start, so there is no day to
    lose by clamping)."""
    local_date = to_karachi(dt).date()
    month_index = local_date.month - 1 + months
    year = local_date.year + month_index // 12
    month = month_index % 12 + 1
    return from_karachi_date_and_hour(local_date.replace(year=year, month=month, day=1), 0)


_FULL_MONTHS = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)  # fmt: skip


def format_weekday_day_month_year(dt):
    """'Mon 31 Aug 2026' in Asia/Karachi (Reports screen, Day period label)."""
    local = to_karachi(dt)
    return f"{_WEEKDAYS[local.weekday()]} {local.day} {_MONTHS[local.month - 1]} {local.year}"


def format_report_week_label(week_start):
    """'16–22 Nov 2026' in Asia/Karachi, spelling out the month(s)/year(s)
    again only where the week actually crosses that boundary."""
    start = to_karachi(week_start)
    end = to_karachi(week_start + timedelta(days=6))
    if start.year != end.year:
        return f"{format_date(week_start)} – {format_date(week_start + timedelta(days=6))}"
    if start.month != end.month:
        return (
            f"{start.day} {_MONTHS[start.month - 1]} – "
            f"{end.day} {_MONTHS[end.month - 1]} {end.year}"
        )
    return f"{start.day}–{end.day} {_MONTHS[start.month - 1]} {end.year}"


def weekday_abbrev(local_date):
    """'Mon'..'Sun' for a date object already in local (Karachi) terms
    (Reports screen chart axis labels)."""
    return _WEEKDAYS[local_date.weekday()]


def format_report_month_label(month_start):
    """'November 2026' in Asia/Karachi (Reports screen, Month period label)."""
    local = to_karachi(month_start)
    return f"{_FULL_MONTHS[local.month - 1]} {local.year}"
