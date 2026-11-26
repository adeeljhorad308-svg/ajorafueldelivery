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


def find_by_id(db, service_id):
    return db.execute("SELECT * FROM services WHERE service_id = ?", (service_id,)).fetchone()


def list_active(db):
    return db.execute("SELECT * FROM services WHERE available = 1 ORDER BY service_id").fetchall()


def list_all(db):
    """Every service, active or not - the All orders Service filter needs to
    match historical orders placed against a service since turned off."""
    return db.execute("SELECT * FROM services ORDER BY name").fetchall()


def count_active(db):
    row = db.execute("SELECT COUNT(*) AS n FROM services WHERE available = 1").fetchone()
    return row["n"]


def find_by_name_ci(db, name, exclude_id=None):
    """Case-insensitive name match for the Add/edit service uniqueness check
    (docs/SPEC.md pop-up 5: Name unique) - the schema's UNIQUE constraint is
    case-sensitive, so this is the real guard; the constraint is only a
    backstop against a race between the check and the insert."""
    if exclude_id is None:
        return db.execute(
            "SELECT * FROM services WHERE name = ? COLLATE NOCASE", (name,)
        ).fetchone()
    return db.execute(
        "SELECT * FROM services WHERE name = ? COLLATE NOCASE AND service_id != ?",
        (name, exclude_id),
    ).fetchone()


def update_service(db, service_id, name, category, unit, unit_price, available):
    db.execute(
        "UPDATE services SET name = ?, category = ?, unit = ?, unit_price = ?, available = ? "
        "WHERE service_id = ?",
        (name, category, unit, to_db(unit_price), available, service_id),
    )
