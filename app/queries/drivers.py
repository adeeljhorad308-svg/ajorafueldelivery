"""SQL for the drivers table. Always parameterised with `?`."""


def create_driver(
    db, name, phone, vehicle_no, area, status, latitude, longitude, rating, is_active=1
):
    # rating is not money (DECIMAL(2,1)); str() avoids sqlite3's "Decimal not
    # supported" bind error without going through app/money.py's paisa rules.
    cursor = db.execute(
        """
        INSERT INTO drivers
            (name, phone, vehicle_no, area, status, latitude, longitude, rating, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (name, phone, vehicle_no, area, status, latitude, longitude, str(rating), is_active),
    )
    return cursor.lastrowid


def find_by_vehicle_no(db, vehicle_no):
    return db.execute("SELECT * FROM drivers WHERE vehicle_no = ?", (vehicle_no,)).fetchone()


def count_by_status(db, status):
    row = db.execute(
        "SELECT COUNT(*) AS n FROM drivers WHERE status = ? AND is_active = 1", (status,)
    ).fetchone()
    return row["n"]


def list_available(db):
    return db.execute(
        "SELECT * FROM drivers WHERE status = 'Available' AND is_active = 1"
    ).fetchall()


def set_status(db, driver_id, status):
    db.execute("UPDATE drivers SET status = ? WHERE driver_id = ?", (status, driver_id))


def update_location(db, driver_id, latitude, longitude):
    db.execute(
        "UPDATE drivers SET latitude = ?, longitude = ? WHERE driver_id = ?",
        (latitude, longitude, driver_id),
    )


def find_by_id(db, driver_id):
    return db.execute("SELECT * FROM drivers WHERE driver_id = ?", (driver_id,)).fetchone()


def count_active(db):
    row = db.execute("SELECT COUNT(*) AS n FROM drivers WHERE is_active = 1").fetchone()
    return row["n"]


def list_active_all(db):
    """Every active driver, name order - admin Drivers screen."""
    return db.execute("SELECT * FROM drivers WHERE is_active = 1 ORDER BY name").fetchall()


def find_by_phone(db, phone):
    return db.execute("SELECT * FROM drivers WHERE phone = ?", (phone,)).fetchone()


def find_by_vehicle_no_excluding(db, vehicle_no, driver_id):
    return db.execute(
        "SELECT * FROM drivers WHERE vehicle_no = ? AND driver_id != ?", (vehicle_no, driver_id)
    ).fetchone()


def update_driver(db, driver_id, name, phone, vehicle_no, area, status):
    """Edit (pop-up 6): area is a label only here - it sets the starting
    location just once, at creation (create_driver); moving it afterwards
    would make live dispatch distances wrong for a driver who has since
    travelled, so latitude/longitude are never touched by an edit."""
    db.execute(
        "UPDATE drivers SET name = ?, phone = ?, vehicle_no = ?, area = ?, status = ? "
        "WHERE driver_id = ?",
        (name, phone, vehicle_no, area, status, driver_id),
    )


def soft_remove(db, driver_id):
    db.execute("UPDATE drivers SET is_active = 0 WHERE driver_id = ?", (driver_id,))
