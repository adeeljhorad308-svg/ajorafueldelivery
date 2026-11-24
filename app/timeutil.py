"""UTC-aware datetime helpers matching SQLite's CURRENT_TIMESTAMP text format.

Every time comparison in the app (session idle/absolute checks, lockouts,
order and tracking history) goes through to_sql()/from_sql() so storage and
Python always agree on format. Asia/Karachi is used only for business rules
that depend on local time of day (dispatch) and for display formatting -
never for comparisons or storage.
"""

from datetime import UTC, datetime
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
