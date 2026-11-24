import sqlite3

import pytest

from app.db import get_db


def _table_names(db):
    rows = db.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {row["name"] for row in rows}


def _index_names(db):
    rows = db.execute("SELECT name FROM sqlite_master WHERE type = 'index'").fetchall()
    return {row["name"] for row in rows}


def test_all_tables_exist(app):
    with app.app_context():
        tables = _table_names(get_db())
    assert {"users", "services", "drivers", "orders", "tracking"} <= tables


def test_required_indexes_exist(app):
    with app.app_context():
        indexes = _index_names(get_db())
    assert {
        "idx_orders_user_created",
        "idx_orders_status",
        "idx_orders_emergency_status",
        "idx_drivers_status",
        "idx_tracking_order",
    } <= indexes


def test_users_role_check_constraint(app):
    with app.app_context():
        db = get_db()
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO users (full_name, email, phone, password_hash, role) "
                "VALUES ('X', 'x@example.com', '03001112222', 'hash', 'superadmin')"
            )


def test_orders_status_check_constraint(app):
    with app.app_context():
        db = get_db()
        db.execute(
            "INSERT INTO users (full_name, email, phone, password_hash, role) "
            "VALUES ('X', 'x@example.com', '03001112222', 'hash', 'customer')"
        )
        db.execute(
            "INSERT INTO services (name, category, unit, price_paisa) "
            "VALUES ('Petrol', 'Fuel', 'litre', 25200)"
        )
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO orders "
                "(user_id, service_id, order_key, status, quantity, unit_price_paisa, total_paisa) "
                "VALUES (1, 1, 'k1', 'Done', 10, 25200, 252000)"
            )


def test_order_key_is_unique(app):
    with app.app_context():
        db = get_db()
        db.execute(
            "INSERT INTO users (full_name, email, phone, password_hash, role) "
            "VALUES ('X', 'x@example.com', '03001112222', 'hash', 'customer')"
        )
        db.execute(
            "INSERT INTO services (name, category, unit, price_paisa) "
            "VALUES ('Petrol', 'Fuel', 'litre', 25200)"
        )
        db.execute(
            "INSERT INTO orders "
            "(user_id, service_id, order_key, quantity, unit_price_paisa, total_paisa) "
            "VALUES (1, 1, 'dup-key', 10, 25200, 252000)"
        )
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO orders "
                "(user_id, service_id, order_key, quantity, unit_price_paisa, total_paisa) "
                "VALUES (1, 1, 'dup-key', 20, 25200, 504000)"
            )
