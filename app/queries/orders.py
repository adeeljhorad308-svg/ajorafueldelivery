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
