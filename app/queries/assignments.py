"""SQL for the assignments table. Always parameterised with `?`."""

from app.money import to_db


def create_assignment(
    db, order_id, driver_id, eta_minutes, assigned_at, distance_km=None, completed_at=None
):
    cursor = db.execute(
        """
        INSERT INTO assignments
            (order_id, driver_id, eta_minutes, assigned_at, distance_km, completed_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            order_id,
            driver_id,
            eta_minutes,
            assigned_at,
            to_db(distance_km) if distance_km is not None else None,
            completed_at,
        ),
    )
    return cursor.lastrowid


def find_by_order_id(db, order_id):
    return db.execute("SELECT * FROM assignments WHERE order_id = ?", (order_id,)).fetchone()


def delete_by_order_id(db, order_id):
    db.execute("DELETE FROM assignments WHERE order_id = ?", (order_id,))


def mark_completed(db, assign_id, completed_at):
    db.execute(
        "UPDATE assignments SET completed_at = ? WHERE assign_id = ?",
        (completed_at, assign_id),
    )
