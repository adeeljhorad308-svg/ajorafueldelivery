"""SQL for the services table. Always parameterised with `?`."""


def create_service(db, name, category, unit, price_paisa, is_active=1):
    cursor = db.execute(
        """
        INSERT INTO services (name, category, unit, price_paisa, is_active)
        VALUES (?, ?, ?, ?, ?)
        """,
        (name, category, unit, price_paisa, is_active),
    )
    return cursor.lastrowid


def find_by_name(db, name):
    return db.execute("SELECT * FROM services WHERE name = ?", (name,)).fetchone()


def list_active(db):
    return db.execute("SELECT * FROM services WHERE is_active = 1 ORDER BY id").fetchall()
