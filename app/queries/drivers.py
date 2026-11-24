"""SQL for the drivers table. Always parameterised with `?`."""


def create_driver(db, name, phone, vehicle_number, area, status, lat, lng, rating):
    cursor = db.execute(
        """
        INSERT INTO drivers (name, phone, vehicle_number, area, status, lat, lng, rating)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (name, phone, vehicle_number, area, status, lat, lng, rating),
    )
    return cursor.lastrowid


def find_by_vehicle_number(db, vehicle_number):
    return db.execute(
        "SELECT * FROM drivers WHERE vehicle_number = ?", (vehicle_number,)
    ).fetchone()


def count_by_status(db, status):
    row = db.execute("SELECT COUNT(*) AS n FROM drivers WHERE status = ?", (status,)).fetchone()
    return row["n"]
