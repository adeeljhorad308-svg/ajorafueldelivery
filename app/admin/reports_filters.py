"""Parses and validates the Reports screen's query string (docs/SPEC.md
FR-16: ?period=day|week|month&date=YYYY-MM-DD). No SQL here -
app/queries/reports.py turns the result into parameterised queries."""

from datetime import date, timedelta

from app import timeutil

PERIODS = ("day", "week", "month")
DEFAULT_PERIOD = "week"


def _anchor_date(raw, now):
    if raw:
        try:
            return date.fromisoformat(raw)
        except ValueError:
            pass
    return timeutil.to_karachi(now).date()


def _period_start(period, anchor_date):
    anchor_dt = timeutil.from_karachi_date_and_hour(anchor_date, 0)
    if period == "day":
        return anchor_dt
    if period == "month":
        return timeutil.start_of_karachi_month(anchor_dt)
    return timeutil.start_of_karachi_week(anchor_dt)


def _period_end(period, start):
    if period == "day":
        return start + timedelta(days=1)
    if period == "month":
        return timeutil.add_karachi_months(start, 1)
    return start + timedelta(days=7)


def _adjacent_start(period, start, step):
    if period == "day":
        return start + timedelta(days=step)
    if period == "month":
        return timeutil.add_karachi_months(start, step)
    return start + timedelta(days=7 * step)


def parse_report_period(args, now=None):
    now = now or timeutil.utcnow()
    period = args.get("period") or DEFAULT_PERIOD
    if period not in PERIODS:
        period = DEFAULT_PERIOD

    anchor = _anchor_date(args.get("date"), now)
    start = _period_start(period, anchor)
    end = _period_end(period, start)
    previous_start = _adjacent_start(period, start, -1)
    next_start = _adjacent_start(period, start, 1)

    return {
        "period": period,
        "start": start,
        "end": end,
        "start_sql": timeutil.to_sql(start),
        "end_sql": timeutil.to_sql(end),
        "previous_date": timeutil.to_karachi(previous_start).date().isoformat(),
        "next_date": timeutil.to_karachi(next_start).date().isoformat(),
    }
