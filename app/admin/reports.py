"""Reports screen (docs/SPEC.md FR-16, screen 19)."""

from flask import render_template, request

from app.admin import bp
from app.admin import reports_presentation as presentation
from app.admin.reports_filters import parse_report_period
from app.db import get_db
from app.queries import reports as report_queries


@bp.get("/admin/reports")
def reports():
    db = get_db()
    parsed = parse_report_period(request.args)
    row = report_queries.stat_cards(db, parsed["start_sql"], parsed["end_sql"])
    is_empty = not (row["total_orders"] or 0)

    charts = None
    if not is_empty:
        per_day_rows = report_queries.orders_per_day(db, parsed["start_sql"], parsed["end_sql"])
        by_service_rows = report_queries.orders_by_service(
            db, parsed["start_sql"], parsed["end_sql"]
        )
        predicted_rows = report_queries.predicted_vs_actual_minutes(
            db, parsed["start_sql"], parsed["end_sql"]
        )
        charts = {
            "orders_per_day": presentation.orders_per_day_chart(parsed, per_day_rows),
            "orders_by_service": presentation.orders_by_service_chart(by_service_rows),
            "predicted_vs_actual": presentation.predicted_vs_actual_chart(parsed, predicted_rows),
            "predicted_vs_actual_note": presentation.predicted_vs_actual_note(row),
        }

    return render_template(
        "admin/reports.html",
        period_controls=presentation.period_controls(parsed),
        stat_cards=presentation.stat_cards(row),
        is_empty=is_empty,
        counting_note=presentation.counting_note(row, parsed),
        charts=charts,
    )
