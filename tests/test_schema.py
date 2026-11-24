import sqlite3

import pytest

from app.db import get_db

# (name, declared type) pairs, matching the FYP document (Tables 35-40) plus
# the extra columns listed in CLAUDE.md. Order matches CREATE TABLE.
EXPECTED_COLUMNS = {
    "users": [
        ("user_id", "INTEGER"),
        ("name", "VARCHAR(60)"),
        ("email", "VARCHAR(80)"),
        ("phone", "VARCHAR(15)"),
        ("password_hash", "VARCHAR(255)"),
        ("role", "VARCHAR(10)"),
        ("is_active", "BOOLEAN"),
        ("created_at", "DATETIME"),
        ("failed_attempts", "INTEGER"),
        ("locked_until", "DATETIME"),
        ("session_version", "INTEGER"),
    ],
    "services": [
        ("service_id", "INTEGER"),
        ("name", "VARCHAR(50)"),
        ("category", "VARCHAR(30)"),
        ("unit_price", "DECIMAL(10, 2)"),
        ("unit", "VARCHAR(10)"),
        ("available", "BOOLEAN"),
    ],
    "drivers": [
        ("driver_id", "INTEGER"),
        ("name", "VARCHAR(60)"),
        ("phone", "VARCHAR(15)"),
        ("vehicle_no", "VARCHAR(15)"),
        ("status", "VARCHAR(15)"),
        ("latitude", "DECIMAL(9, 6)"),
        ("longitude", "DECIMAL(9, 6)"),
        ("rating", "DECIMAL(2, 1)"),
        ("area", "VARCHAR(50)"),
        ("is_active", "BOOLEAN"),
    ],
    "orders": [
        ("order_id", "INTEGER"),
        ("user_id", "INTEGER"),
        ("service_id", "INTEGER"),
        ("quantity", "DECIMAL(8, 2)"),
        ("total_amount", "DECIMAL(10, 2)"),
        ("address", "VARCHAR(200)"),
        ("latitude", "DECIMAL(9, 6)"),
        ("longitude", "DECIMAL(9, 6)"),
        ("is_emergency", "BOOLEAN"),
        ("note", "VARCHAR(200)"),
        ("scheduled_at", "DATETIME"),
        ("status", "VARCHAR(20)"),
        ("created_at", "DATETIME"),
        ("order_key", "TEXT"),
        ("call_confirmed", "BOOLEAN"),
        ("cancel_reason", "VARCHAR(200)"),
        ("area", "VARCHAR(50)"),
    ],
    "assignments": [
        ("assign_id", "INTEGER"),
        ("order_id", "INTEGER"),
        ("driver_id", "INTEGER"),
        ("eta_minutes", "INTEGER"),
        ("assigned_at", "DATETIME"),
        ("completed_at", "DATETIME"),
        ("distance_km", "DECIMAL(6, 2)"),
    ],
    "tracking": [
        ("track_id", "INTEGER"),
        ("order_id", "INTEGER"),
        ("status", "VARCHAR(20)"),
        ("latitude", "DECIMAL(9, 6)"),
        ("longitude", "DECIMAL(9, 6)"),
        ("updated_at", "DATETIME"),
    ],
}


def _table_names(db):
    rows = db.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {row["name"] for row in rows}


def _index_names(db):
    rows = db.execute("SELECT name FROM sqlite_master WHERE type = 'index'").fetchall()
    return {row["name"] for row in rows}


def _column_specs(db, table):
    rows = db.execute(f"PRAGMA table_info({table})").fetchall()
    return [(row["name"], row["type"]) for row in rows]


def test_all_tables_exist(app):
    with app.app_context():
        tables = _table_names(get_db())
    assert set(EXPECTED_COLUMNS) <= tables


@pytest.mark.parametrize("table", list(EXPECTED_COLUMNS))
def test_pragma_table_info_matches_document(app, table):
    with app.app_context():
        columns = _column_specs(get_db(), table)
    assert columns == EXPECTED_COLUMNS[table]


def test_required_indexes_exist(app):
    with app.app_context():
        indexes = _index_names(get_db())
    assert {
        "idx_orders_user_created",
        "idx_orders_status",
        "idx_orders_emergency_status",
        "idx_assignments_driver",
        "idx_drivers_status",
        "idx_tracking_order",
    } <= indexes


def test_users_role_check_constraint(app):
    with app.app_context():
        db = get_db()
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO users (name, email, phone, password_hash, role) "
                "VALUES ('X', 'x@example.com', '03001112222', 'hash', 'superadmin')"
            )


def test_orders_status_check_constraint(app):
    with app.app_context():
        db = get_db()
        db.execute(
            "INSERT INTO users (name, email, phone, password_hash, role) "
            "VALUES ('X', 'x@example.com', '03001112222', 'hash', 'customer')"
        )
        db.execute(
            "INSERT INTO services (name, category, unit, unit_price) "
            "VALUES ('Petrol', 'Fuel', 'litre', 252.00)"
        )
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO orders "
                "(user_id, service_id, order_key, status, quantity, total_amount, address) "
                "VALUES (1, 1, 'k1', 'Done', 10, 2520.00, 'Test address')"
            )


def test_order_key_is_unique(app):
    with app.app_context():
        db = get_db()
        db.execute(
            "INSERT INTO users (name, email, phone, password_hash, role) "
            "VALUES ('X', 'x@example.com', '03001112222', 'hash', 'customer')"
        )
        db.execute(
            "INSERT INTO services (name, category, unit, unit_price) "
            "VALUES ('Petrol', 'Fuel', 'litre', 252.00)"
        )
        db.execute(
            "INSERT INTO orders (user_id, service_id, order_key, quantity, total_amount, address) "
            "VALUES (1, 1, 'dup-key', 10, 2520.00, 'Test address')"
        )
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO orders "
                "(user_id, service_id, order_key, quantity, total_amount, address) "
                "VALUES (1, 1, 'dup-key', 20, 5040.00, 'Test address')"
            )


def test_assignments_order_id_is_unique(app):
    with app.app_context():
        db = get_db()
        db.execute(
            "INSERT INTO users (name, email, phone, password_hash, role) "
            "VALUES ('X', 'x@example.com', '03001112222', 'hash', 'customer')"
        )
        db.execute(
            "INSERT INTO services (name, category, unit, unit_price) "
            "VALUES ('Petrol', 'Fuel', 'litre', 252.00)"
        )
        db.execute(
            "INSERT INTO orders (user_id, service_id, order_key, quantity, total_amount, address) "
            "VALUES (1, 1, 'k1', 10, 2520.00, 'Test address')"
        )
        db.execute(
            "INSERT INTO drivers (name, phone, vehicle_no) VALUES ('D', '03009990000', 'LEA-0001')"
        )
        db.execute("INSERT INTO assignments (order_id, driver_id, eta_minutes) VALUES (1, 1, 10)")
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO assignments (order_id, driver_id, eta_minutes) VALUES (1, 1, 20)"
            )
