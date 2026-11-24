"""SQL for the tracking table. Always parameterised with `?`."""


def add_tracking(db, order_id, status, created_at, note=None):
    cursor = db.execute(
        "INSERT INTO tracking (order_id, status, note, created_at) VALUES (?, ?, ?, ?)",
        (order_id, status, note, created_at),
    )
    return cursor.lastrowid


def list_for_order(db, order_id):
    return db.execute(
        "SELECT * FROM tracking WHERE order_id = ? ORDER BY created_at", (order_id,)
    ).fetchall()
