"""Admin blueprint, deny by default (docs/SECURITY.md A01)."""

from datetime import timedelta

from flask import Blueprint, abort, g, render_template, request, url_for

from app import money, timeutil
from app.admin import filters as filter_parsing
from app.admin import presentation
from app.db import get_db
from app.queries import admin_orders as order_queries
from app.queries import drivers as driver_queries
from app.queries import services as service_queries
from app.queries import users as user_queries
from app.security import count_failed_logins_today, require_admin

bp = Blueprint("admin", __name__)


@bp.before_request
def guard():
    return require_admin()


_SIDEBAR_ITEMS = (
    ("dashboard", "Dashboard", "gauge-high", "admin.dashboard", None),
    ("orders", "Orders", "clipboard-list", "admin.orders", None),
    ("emergency", "Emergency", "triangle-exclamation", "admin.emergency", "emergency_count"),
    ("customers", "Customers", "users", "admin.customers", None),
    ("services", "Services", "tags", "admin.services", None),
    ("drivers", "Drivers", "id-card", "admin.drivers", None),
    ("reports", "Reports", "chart-column", "admin.reports", None),
)


@bp.context_processor
def inject_admin_chrome():
    """Sidebar links/badge and the top bar's date - every admin page needs
    them, so one place computes them instead of each view repeating it. A
    sidebar item whose route doesn't exist yet (built in a later session)
    degrades to inert text instead of a broken link (CLAUDE.md design gate:
    never guess a layout or placeholder UI)."""
    user = g.get("current_user")
    if user is None:
        return {}
    db = get_db()
    emergency_count = order_queries.count_open_emergencies(db)
    counts = {"emergency_count": emergency_count}
    sidebar_links = [
        {
            "key": key,
            "label": label,
            "icon": icon_name,
            "href": presentation.sidebar_href(endpoint),
            "badge": counts[badge_key] if badge_key else None,
        }
        for key, label, icon_name, endpoint, badge_key in _SIDEBAR_ITEMS
    ]
    return {
        "admin_name": user["name"],
        "admin_initials": "".join(part[0] for part in user["name"].split()[:2]).upper(),
        "admin_emergency_count": emergency_count,
        "admin_today_label": timeutil.format_weekday_date(timeutil.utcnow()),
        "admin_sidebar_links": sidebar_links,
    }


@bp.get("/admin")
def dashboard():
    db = get_db()
    now = timeutil.utcnow()
    today_start = timeutil.start_of_karachi_day(now)
    yesterday_start = today_start - timedelta(days=1)

    today_count = order_queries.count_created_since(db, timeutil.to_sql(today_start))
    yesterday_count = order_queries.count_created_between(
        db, timeutil.to_sql(yesterday_start), timeutil.to_sql(today_start)
    )

    emergencies_open = order_queries.count_open_emergencies(db)
    oldest_wait_minutes = 0
    if emergencies_open:
        oldest_created = timeutil.from_sql(order_queries.oldest_open_emergency_created_at(db))
        oldest_wait_minutes = max(0, round((now - oldest_created).total_seconds() / 60))

    sales_raw = order_queries.sum_delivered_amount_since(db, timeutil.to_sql(today_start))
    sales_amount = money.from_db(sales_raw) if sales_raw is not None else money.parse_amount(0)

    available = driver_queries.count_by_status(db, "Available")
    busy = driver_queries.count_by_status(db, "Busy")
    total_drivers = driver_queries.count_active(db)

    stat_cards = presentation.dashboard_stat_cards(
        today_count,
        yesterday_count,
        emergencies_open,
        oldest_wait_minutes,
        sales_amount,
        available,
        busy,
        total_drivers,
    )
    bar = presentation.emergency_bar(
        emergencies_open, oldest_wait_minutes, url_for("admin.orders", emergency="1")
    )

    latest_orders = [
        presentation.admin_order_row(row, now) for row in order_queries.list_latest(db, 10)
    ]

    due_soon_rows = order_queries.list_due_soon(
        db,
        timeutil.to_sql(now),
        timeutil.to_sql(now + timedelta(minutes=60)),
        presentation.DASHBOARD_LIST_LIMIT,
    )
    due_soon = [presentation.due_soon_item(row, now) for row in due_soon_rows]

    call_needed_rows = order_queries.list_call_needed(db, presentation.DASHBOARD_LIST_LIMIT)
    call_needed = [presentation.call_needed_item(row) for row in call_needed_rows]
    call_needed_count = order_queries.count_call_needed(db)

    locked_rows = user_queries.list_locked(db, timeutil.to_sql(now))
    failed_logins = count_failed_logins_today(now)
    security = presentation.security_card(failed_logins, locked_rows, now)

    open_emergency_rows = order_queries.list_open_emergencies_after_id(db, 0)
    max_emergency_id = max((row["order_id"] for row in open_emergency_rows), default=0)

    return render_template(
        "admin/dashboard.html",
        max_emergency_id=max_emergency_id,
        stat_cards=stat_cards,
        emergency_bar=bar,
        latest_orders=latest_orders,
        due_soon=due_soon,
        due_soon_count=len(due_soon_rows),
        call_needed=call_needed,
        call_needed_count=call_needed_count,
        security=security,
    )


@bp.get("/admin/orders")
def orders():
    db = get_db()
    now = timeutil.utcnow()
    services = service_queries.list_all(db)
    service_ids = tuple(row["service_id"] for row in services)
    parsed = filter_parsing.parse_order_filters(request.args, now, service_ids=service_ids)

    total_count = order_queries.count_admin_filtered(db, parsed)
    page_info = presentation.all_orders_pagination(total_count, parsed["page"])
    offset = (page_info["page"] - 1) * presentation.ALL_ORDERS_PER_PAGE
    rows = order_queries.list_admin_filtered(db, parsed, presentation.ALL_ORDERS_PER_PAGE, offset)
    order_rows = [presentation.admin_order_row(row, now) for row in rows]

    return render_template(
        "admin/orders.html",
        rows=order_rows,
        page_info=page_info,
        filters=parsed,
        active_filter_count=filter_parsing.active_filter_count(parsed),
        status_options=presentation.status_filter_options(),
        service_options=presentation.service_filter_options(services),
        date_options=presentation.DATE_FILTER_OPTIONS,
        page_url=lambda n: url_for("admin.orders", **filter_parsing.query_args(parsed, page=n)),
        clear_url=url_for("admin.orders"),
    )


@bp.get("/admin/orders/<int:order_id>")
def order_detail(order_id):
    db = get_db()
    order_row = order_queries.find_admin_by_id(db, order_id)
    if order_row is None:
        abort(404)
    return render_template(
        "admin/order_detail_placeholder.html",
        order=presentation.admin_order_row(order_row, timeutil.utcnow()),
    )
