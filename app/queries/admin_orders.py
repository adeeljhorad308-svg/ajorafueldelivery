"""SQL for the admin dashboard and All orders (C9). Always parameterised with
`?`. Split out of app/queries/orders.py (customer-facing order queries) so
neither file grows past the project's size guideline."""

OPEN_STATUSES = ("Pending", "Assigned", "On the Way")

_ADMIN_ORDER_SELECT = """
    SELECT orders.*, services.name AS service_name, services.category AS service_category,
           services.unit AS service_unit, services.unit_price AS unit_price,
           users.name AS customer_name, users.phone AS customer_phone,
           assignments.assign_id AS assign_id, assignments.driver_id AS driver_id,
           assignments.eta_minutes AS eta_minutes, assignments.distance_km AS distance_km,
           assignments.assigned_at AS assigned_at, assignments.completed_at AS completed_at,
           drivers.name AS driver_name, drivers.phone AS driver_phone,
           drivers.vehicle_no AS driver_vehicle_no, drivers.rating AS driver_rating,
           drivers.latitude AS driver_latitude, drivers.longitude AS driver_longitude
    FROM orders
    JOIN services ON services.service_id = orders.service_id
    JOIN users ON users.user_id = orders.user_id
    LEFT JOIN assignments ON assignments.order_id = orders.order_id
    LEFT JOIN drivers ON drivers.driver_id = assignments.driver_id
"""

_ADMIN_JOIN_ONLY = (
    "FROM orders JOIN services ON services.service_id = orders.service_id "
    "JOIN users ON users.user_id = orders.user_id"
)

_ADMIN_ORDER_BY = (
    " ORDER BY CASE WHEN orders.is_emergency = 1 AND orders.status IN "
    "('Pending', 'Assigned', 'On the Way') THEN 0 ELSE 1 END, orders.created_at DESC, "
    "orders.order_id DESC"
)


def _admin_where(filters):
    """Builds a parameterised WHERE clause from an already-validated filter
    dict (app/admin/filters.py chose every value from a fixed allow-list, so
    only `?` placeholders ever carry request data)."""
    clauses = []
    params = []
    if filters.get("statuses"):
        placeholders = ", ".join("?" for _ in filters["statuses"])
        clauses.append(f"orders.status IN ({placeholders})")
        params.extend(filters["statuses"])
    if filters.get("service"):
        clauses.append("orders.service_id = ?")
        params.append(filters["service"])
    if filters.get("emergency_only"):
        clauses.append("orders.is_emergency = 1")
    if filters.get("date_from"):
        clauses.append("orders.created_at >= ?")
        params.append(filters["date_from"])
    if filters.get("date_to"):
        clauses.append("orders.created_at < ?")
        params.append(filters["date_to"])
    search_kind = filters.get("search_kind")
    if search_kind == "order":
        clauses.append("orders.order_id = ?")
        params.append(filters["search_value"])
    elif search_kind == "phone":
        clauses.append("users.phone LIKE ?")
        params.append(f"%{filters['search_value']}%")
    where_sql = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    return where_sql, params


def find_admin_by_id(db, order_id):
    """Admin lookup with customer name/phone joined in (order_queries.find_by_id
    is the customer/track-order shape, which has no users join)."""
    return db.execute(
        f"{_ADMIN_ORDER_SELECT} WHERE orders.order_id = ?",  # noqa: S608
        (order_id,),
    ).fetchone()


def count_admin_filtered(db, filters):
    where_sql, params = _admin_where(filters)
    row = db.execute(
        f"SELECT COUNT(*) AS n {_ADMIN_JOIN_ONLY}{where_sql}",
        params,  # noqa: S608
    ).fetchone()
    return row["n"]


def list_admin_filtered(db, filters, limit, offset):
    where_sql, params = _admin_where(filters)
    sql = f"{_ADMIN_ORDER_SELECT}{where_sql}{_ADMIN_ORDER_BY} LIMIT ? OFFSET ?"  # noqa: S608
    return db.execute(sql, (*params, limit, offset)).fetchall()


def count_created_between(db, start, end):
    row = db.execute(
        "SELECT COUNT(*) AS n FROM orders WHERE created_at >= ? AND created_at < ?",
        (start, end),
    ).fetchone()
    return row["n"]


def count_created_since(db, start):
    """Open-ended version of count_created_between for "today so far": an
    exclusive upper bound of "now" would wrongly drop an order created in the
    same second the dashboard is loaded (SQLite timestamps only keep whole
    seconds), so "today" has no upper bound at all - nothing is ever created
    in the future."""
    row = db.execute("SELECT COUNT(*) AS n FROM orders WHERE created_at >= ?", (start,)).fetchone()
    return row["n"]


def sum_delivered_amount_between(db, start, end):
    """Cash collected from orders *delivered* in [start, end) - joined on
    assignments.completed_at, not orders.created_at (CLAUDE.md money rule:
    one ROUND(SUM()) in SQL, re-quantized through app/money.py by the caller)."""
    row = db.execute(
        """
        SELECT ROUND(SUM(orders.total_amount), 2) AS total
        FROM orders JOIN assignments ON assignments.order_id = orders.order_id
        WHERE orders.status = 'Delivered' AND assignments.completed_at >= ?
              AND assignments.completed_at < ?
        """,
        (start, end),
    ).fetchone()
    return row["total"]


def sum_delivered_amount_since(db, start):
    """Open-ended version of sum_delivered_amount_between - see
    count_created_since for why "today so far" has no upper bound."""
    row = db.execute(
        """
        SELECT ROUND(SUM(orders.total_amount), 2) AS total
        FROM orders JOIN assignments ON assignments.order_id = orders.order_id
        WHERE orders.status = 'Delivered' AND assignments.completed_at >= ?
        """,
        (start,),
    ).fetchone()
    return row["total"]


def count_open_emergencies(db):
    row = db.execute(
        "SELECT COUNT(*) AS n FROM orders WHERE is_emergency = 1 AND status IN "
        "('Pending', 'Assigned', 'On the Way')"
    ).fetchone()
    return row["n"]


def oldest_open_emergency_created_at(db):
    row = db.execute(
        "SELECT MIN(created_at) AS oldest FROM orders WHERE is_emergency = 1 AND status IN "
        "('Pending', 'Assigned', 'On the Way')"
    ).fetchone()
    return row["oldest"]


def list_open_emergencies_after_id(db, after_id):
    """Open emergencies the admin's browser hasn't rendered yet (order_id is
    monotonic, so this is robust to clock drift - /api/admin/live uses it to
    slide new rows into the Latest orders table)."""
    return db.execute(
        """
        SELECT orders.order_id, orders.total_amount, users.name AS customer_name
        FROM orders
        JOIN users ON users.user_id = orders.user_id
        WHERE orders.is_emergency = 1 AND orders.status IN ('Pending', 'Assigned', 'On the Way')
              AND orders.order_id > ?
        ORDER BY orders.order_id
        """,
        (after_id,),
    ).fetchall()


def list_latest(db, limit):
    return db.execute(
        f"{_ADMIN_ORDER_SELECT} ORDER BY orders.created_at DESC, orders.order_id DESC "  # noqa: S608
        "LIMIT ?",
        (limit,),
    ).fetchall()


def list_due_soon(db, now, until, limit):
    return db.execute(
        f"""
        {_ADMIN_ORDER_SELECT}
        WHERE orders.status = 'Pending' AND orders.scheduled_at IS NOT NULL
              AND orders.scheduled_at BETWEEN ? AND ?
        ORDER BY orders.scheduled_at
        LIMIT ?
        """,  # noqa: S608
        (now, until, limit),
    ).fetchall()


def count_due_soon(db, now, until):
    row = db.execute(
        "SELECT COUNT(*) AS n FROM orders WHERE status = 'Pending' AND scheduled_at IS NOT NULL "
        "AND scheduled_at BETWEEN ? AND ?",
        (now, until),
    ).fetchone()
    return row["n"]


def list_call_needed(db, limit):
    return db.execute(
        f"""
        {_ADMIN_ORDER_SELECT}
        WHERE orders.call_confirmed = 0
        ORDER BY orders.created_at
        LIMIT ?
        """,  # noqa: S608
        (limit,),
    ).fetchall()


def count_call_needed(db):
    row = db.execute("SELECT COUNT(*) AS n FROM orders WHERE call_confirmed = 0").fetchone()
    return row["n"]


def list_open_orders_for_driver(db, driver_id):
    """A driver's open stops (Order details' route list, Stop X of N) - every
    order assigned to them that is not yet finished."""
    return db.execute(
        """
        SELECT orders.order_id, orders.latitude, orders.longitude, orders.area,
               services.name AS service_name, services.unit AS service_unit,
               orders.quantity
        FROM orders
        JOIN assignments ON assignments.order_id = orders.order_id
        JOIN services ON services.service_id = orders.service_id
        WHERE assignments.driver_id = ? AND orders.status IN ('Assigned', 'On the Way')
        """,
        (driver_id,),
    ).fetchall()
