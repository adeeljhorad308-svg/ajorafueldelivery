"""SQL for the services table. Always parameterised with `?`."""

from app.money import to_db


def create_service(db, name, category, unit, unit_price, available=1):
    cursor = db.execute(
        """
        INSERT INTO services (name, category, unit, unit_price, available)
        VALUES (?, ?, ?, ?, ?)
        """,
        (name, category, unit, to_db(unit_price), available),
    )
    return cursor.lastrowid


def find_by_name(db, name):
    return db.execute("SELECT * FROM services WHERE name = ?", (name,)).fetchone()


def list_active(db):
    return db.execute("SELECT * FROM services WHERE available = 1 ORDER BY service_id").fetchall()
