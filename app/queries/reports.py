"""SQL for the Reports screen (docs/SPEC.md FR-16). Always parameterised with
`?`. One query per card group or chart, filtered on orders.created_at (the
period's own date range, "orders placed in these dates") - indexed via
idx_orders_created_at."""


def stat_cards(db, start, end):
    """The 6 report cards plus the note's "of N placed" total, in one query:
    only Delivered and Cancelled orders placed in [start, end) are counted,
    sales only from Delivered, average delivery time from assignments
    (completed_at - assigned_at) for Delivered orders. assignments.order_id is
    UNIQUE, so the LEFT JOIN cannot duplicate an orders row."""
    return db.execute(
        """
        SELECT
          COUNT(*) AS placed_total,
          SUM(CASE WHEN orders.status IN ('Delivered', 'Cancelled') THEN 1 ELSE 0 END)
            AS total_orders,
          SUM(CASE WHEN orders.status = 'Delivered' THEN 1 ELSE 0 END) AS delivered,
          SUM(CASE WHEN orders.status = 'Cancelled' THEN 1 ELSE 0 END) AS cancelled,
          SUM(CASE WHEN orders.is_emergency = 1 AND orders.status IN ('Delivered', 'Cancelled')
                   THEN 1 ELSE 0 END) AS emergency,
          ROUND(SUM(CASE WHEN orders.status = 'Delivered' THEN orders.total_amount ELSE 0 END), 2)
            AS sales,
          AVG(CASE WHEN orders.status = 'Delivered' THEN
                (julianday(assignments.completed_at) - julianday(assignments.assigned_at)) * 1440
              END) AS avg_delivery_minutes,
          AVG(CASE WHEN orders.status = 'Delivered' THEN assignments.eta_minutes END)
            AS avg_predicted_minutes
        FROM orders
        LEFT JOIN assignments ON assignments.order_id = orders.order_id
        WHERE orders.created_at >= ? AND orders.created_at < ?
        """,
        (start, end),
    ).fetchone()


def orders_per_day(db, start, end):
    """Bar chart 1: counted orders placed each Asia/Karachi calendar day in
    the period (Karachi is UTC+5 year-round, no DST, so a fixed offset is
    exact)."""
    return db.execute(
        """
        SELECT date(orders.created_at, '+5 hours') AS day, COUNT(*) AS n
        FROM orders
        WHERE orders.created_at >= ? AND orders.created_at < ?
              AND orders.status IN ('Delivered', 'Cancelled')
        GROUP BY day
        ORDER BY day
        """,
        (start, end),
    ).fetchall()


def orders_by_service(db, start, end):
    """Bar chart 2: counted orders grouped by service, with emergency orders
    (which still use the Petrol/Diesel service row) broken out into their own
    "Emergency" bucket, same as the admin order list's service label."""
    return db.execute(
        """
        SELECT CASE WHEN orders.is_emergency = 1 THEN 'Emergency' ELSE services.name END AS label,
               COUNT(*) AS n
        FROM orders JOIN services ON services.service_id = orders.service_id
        WHERE orders.created_at >= ? AND orders.created_at < ?
              AND orders.status IN ('Delivered', 'Cancelled')
        GROUP BY label
        ORDER BY n DESC
        """,
        (start, end),
    ).fetchall()


def predicted_vs_actual_minutes(db, start, end):
    """Bar chart 3: predicted (assignments.eta_minutes) vs actual
    (completed_at - assigned_at) delivery minutes, averaged per Asia/Karachi
    calendar day, for Delivered orders only."""
    return db.execute(
        """
        SELECT date(orders.created_at, '+5 hours') AS day,
               AVG(assignments.eta_minutes) AS predicted,
               AVG((julianday(assignments.completed_at) - julianday(assignments.assigned_at))
                   * 1440) AS actual
        FROM orders JOIN assignments ON assignments.order_id = orders.order_id
        WHERE orders.created_at >= ? AND orders.created_at < ? AND orders.status = 'Delivered'
        GROUP BY day
        ORDER BY day
        """,
        (start, end),
    ).fetchall()
