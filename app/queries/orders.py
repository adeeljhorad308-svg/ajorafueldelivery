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
):
    cursor = db.execute(
        """
        INSERT INTO orders
            (user_id, service_id, order_key, quantity, total_amount, address, area,
             latitude, longitude, note, is_emergency, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending')
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
        ),
    )
    return cursor.lastrowid


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
           drivers.name AS driver_name, drivers.vehicle_no AS vehicle_no
    FROM orders
    JOIN services ON services.service_id = orders.service_id
    LEFT JOIN assignments ON assignments.order_id = orders.order_id
    LEFT JOIN drivers ON drivers.driver_id = assignments.driver_id
"""


def find_active_for_user(db, user_id):
    """The customer's one open order (Pending/Assigned/On the Way), newest first."""
    return db.execute(
        f"""
        {_ORDER_WITH_ASSIGNMENT}
        WHERE orders.user_id = ? AND orders.status IN ('Pending', 'Assigned', 'On the Way')
        ORDER BY orders.created_at DESC
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
