"""SQL for the orders table. Always parameterised with `?`."""


def insert_seed_order(db, **fields):
    """Insert a fully-formed order row for seed/demo data (sets its own timestamps).

    Column names come from our own code's keyword arguments, never from a
    request; values are still passed as `?` parameters.
    """
    columns = ", ".join(fields)
    placeholders = ", ".join("?" for _ in fields)
    cursor = db.execute(
        f"INSERT INTO orders ({columns}) VALUES ({placeholders})",  # noqa: S608
        tuple(fields.values()),
    )
    return cursor.lastrowid


def find_by_order_key(db, order_key):
    return db.execute("SELECT * FROM orders WHERE order_key = ?", (order_key,)).fetchone()


def count_for_user(db, user_id):
    row = db.execute("SELECT COUNT(*) AS n FROM orders WHERE user_id = ?", (user_id,)).fetchone()
    return row["n"]


def insert_order(
    db,
    user_id,
    service_id,
    order_key,
    quantity,
    total_amount,
    address,
    area,
    latitude,
    longitude,
    note,
    is_emergency=0,
    call_confirmed=1,
    scheduled_at=None,
):
    cursor = db.execute(
        """
        INSERT INTO orders
            (user_id, service_id, order_key, quantity, total_amount, address, area,
             latitude, longitude, note, is_emergency, call_confirmed, scheduled_at, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending')
        """,
        (
            user_id,
            service_id,
            order_key,
            quantity,
            total_amount,
            address,
            area,
            latitude,
            longitude,
            note,
            is_emergency,
            call_confirmed,
            scheduled_at,
        ),
    )
    return cursor.lastrowid


def find_open_emergency_for_user(db, user_id):
    return db.execute(
        "SELECT * FROM orders WHERE user_id = ? AND is_emergency = 1 "
        "AND status IN ('Pending', 'Assigned', 'On the Way') LIMIT 1",
        (user_id,),
    ).fetchone()


_ORDER_WITH_SERVICE = """
    SELECT orders.*, services.name AS service_name, services.unit_price AS unit_price,
           services.unit AS service_unit
    FROM orders
    JOIN services ON services.service_id = orders.service_id
"""

_ORDER_WITH_ASSIGNMENT = """
    SELECT orders.*, services.name AS service_name, services.unit_price AS unit_price,
           services.unit AS service_unit, assignments.driver_id AS driver_id,
           assignments.eta_minutes AS eta_minutes, assignments.distance_km AS distance_km,
           assignments.assigned_at AS assigned_at,
           drivers.name AS driver_name, drivers.vehicle_no AS vehicle_no,
           drivers.rating AS driver_rating, drivers.phone AS driver_phone
    FROM orders
    JOIN services ON services.service_id = orders.service_id
    LEFT JOIN assignments ON assignments.order_id = orders.order_id
    LEFT JOIN drivers ON drivers.driver_id = assignments.driver_id
"""


def find_active_for_user(db, user_id):
    """The customer's one open order to feature on Customer home: whichever is
    furthest along (On the Way > Assigned > Pending), newest first among ties."""
    return db.execute(
        f"""
        {_ORDER_WITH_ASSIGNMENT}
        WHERE orders.user_id = ? AND orders.status IN ('Pending', 'Assigned', 'On the Way')
        ORDER BY
            CASE orders.status
                WHEN 'On the Way' THEN 0
                WHEN 'Assigned' THEN 1
                WHEN 'Pending' THEN 2
            END,
            orders.created_at DESC
        LIMIT 1
        """,  # noqa: S608 (static SQL text, no interpolated values)
        (user_id,),
    ).fetchone()


def find_last_finished_for_user(db, user_id):
    return db.execute(
        f"""
        {_ORDER_WITH_SERVICE}
        WHERE orders.user_id = ? AND orders.status IN ('Delivered', 'Cancelled')
        ORDER BY orders.created_at DESC
        LIMIT 1
        """,  # noqa: S608 (static SQL text, no interpolated values)
        (user_id,),
    ).fetchone()


def find_by_id_for_user(db, order_id, user_id):
    return db.execute(
        f"{_ORDER_WITH_ASSIGNMENT} WHERE orders.order_id = ? AND orders.user_id = ?",  # noqa: S608
        (order_id, user_id),
    ).fetchone()


def find_by_id(db, order_id):
    """Admin lookup: any order, no owner filter."""
    return db.execute(
        f"{_ORDER_WITH_ASSIGNMENT} WHERE orders.order_id = ?",  # noqa: S608
        (order_id,),
    ).fetchone()


STATUS_FILTERS = {
    "active": ("Pending", "Assigned", "On the Way"),
    "delivered": ("Delivered",),
    "cancelled": ("Cancelled",),
}


def count_for_user_show(db, user_id, show):
    """Row count for My orders' filter chips (show: all/active/delivered/cancelled)."""
    if show not in STATUS_FILTERS:
        row = db.execute(
            "SELECT COUNT(*) AS n FROM orders WHERE user_id = ?", (user_id,)
        ).fetchone()
        return row["n"]
    statuses = STATUS_FILTERS[show]
    placeholders = ", ".join("?" for _ in statuses)
    row = db.execute(
        f"SELECT COUNT(*) AS n FROM orders WHERE user_id = ? AND status IN ({placeholders})",  # noqa: S608
        (user_id, *statuses),
    ).fetchone()
    return row["n"]


def list_for_user_show(db, user_id, show, limit, offset):
    """My orders (FR-08): one page, newest first."""
    if show not in STATUS_FILTERS:
        return db.execute(
            f"""
            {_ORDER_WITH_SERVICE}
            WHERE orders.user_id = ?
            ORDER BY orders.created_at DESC
            LIMIT ? OFFSET ?
            """,  # noqa: S608
            (user_id, limit, offset),
        ).fetchall()
    statuses = STATUS_FILTERS[show]
    placeholders = ", ".join("?" for _ in statuses)
    return db.execute(
        f"""
        {_ORDER_WITH_SERVICE}
        WHERE orders.user_id = ? AND orders.status IN ({placeholders})
        ORDER BY orders.created_at DESC
        LIMIT ? OFFSET ?
        """,  # noqa: S608
        (user_id, *statuses, limit, offset),
    ).fetchall()


def list_pending_asap(db):
    """Orders waiting for dispatch: not scheduled, and not an above-200 L
    order still waiting on the admin's call."""
    return db.execute(
        "SELECT * FROM orders WHERE status = 'Pending' AND scheduled_at IS NULL "
        "AND call_confirmed = 1"
    ).fetchall()


def update_status(db, order_id, status):
    db.execute("UPDATE orders SET status = ? WHERE order_id = ?", (status, order_id))
