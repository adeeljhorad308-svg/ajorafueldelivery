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
