from decimal import Decimal

from app.db import get_db
from app.demo_data import seed_demo
from app.money import from_db


def test_seed_creates_no_admin(app):
    with app.app_context():
        db = get_db()
        seed_demo(db, "demo-pass-1234")
        row = db.execute("SELECT COUNT(*) AS n FROM users WHERE role = 'admin'").fetchone()
        assert row["n"] == 0


def test_seed_exact_ali_raza_orders(app):
    with app.app_context():
        db = get_db()
        seed_demo(db, "demo-pass-1234")

        ali = db.execute(
            "SELECT * FROM users WHERE email = ?", ("ali.raza@example.com",)
        ).fetchone()
        assert ali["phone"] == "03001234567"

        order_42 = db.execute("SELECT * FROM orders WHERE order_key = 'seed-ord-0042'").fetchone()
        assert order_42["order_id"] == 42
        assert order_42["status"] == "On the Way"
        assert order_42["quantity"] == 20
        assert from_db(order_42["total_amount"]) == Decimal("5040.00")

        assignment = db.execute(
            "SELECT * FROM assignments WHERE order_id = ?", (order_42["order_id"],)
        ).fetchone()
        assert assignment is not None
        assert assignment["completed_at"] is None
        driver = db.execute(
            "SELECT * FROM drivers WHERE driver_id = ?", (assignment["driver_id"],)
        ).fetchone()
        assert driver["name"] == "Ahmed Raza"
        assert driver["vehicle_no"] == "LEA-1234"

        order_43 = db.execute("SELECT * FROM orders WHERE order_key = 'seed-ord-0043'").fetchone()
        assert order_43["order_id"] == 43
        assert order_43["quantity"] == 250
        assert from_db(order_43["total_amount"]) == Decimal("64500.00")
        assert order_43["call_confirmed"] == 0

        total_orders = db.execute(
            "SELECT COUNT(*) AS n FROM orders WHERE user_id = ?", (ali["user_id"],)
        ).fetchone()["n"]
        assert total_orders == 23


def test_seed_open_emergencies(app):
    with app.app_context():
        db = get_db()
        seed_demo(db, "demo-pass-1234")

        sana = db.execute(
            "SELECT * FROM users WHERE email = ?", ("sana.iqbal@example.com",)
        ).fetchone()
        bilal = db.execute(
            "SELECT * FROM users WHERE email = ?", ("bilal.khan@example.com",)
        ).fetchone()

        emergency_sana = db.execute(
            "SELECT * FROM orders WHERE user_id = ? AND is_emergency = 1", (sana["user_id"],)
        ).fetchone()
        assert emergency_sana["order_id"] == 46
        assert emergency_sana["quantity"] == 10
        assert emergency_sana["status"] == "Pending"

        emergency_bilal = db.execute(
            "SELECT * FROM orders WHERE user_id = ? AND is_emergency = 1", (bilal["user_id"],)
        ).fetchone()
        assert emergency_bilal["order_id"] == 47
        assert emergency_bilal["quantity"] == 5


def test_seed_services_and_drivers(app):
    with app.app_context():
        db = get_db()
        seed_demo(db, "demo-pass-1234")

        services = db.execute("SELECT name, unit_price FROM services").fetchall()
        assert len(services) == 7
        prices = {row["name"]: from_db(row["unit_price"]) for row in services}
        assert prices["Petrol"] == Decimal("252.00")
        assert prices["Diesel"] == Decimal("258.00")

        drivers = db.execute("SELECT name, status FROM drivers").fetchall()
        assert len(drivers) == 9
        statuses = {row["name"]: row["status"] for row in drivers}
        assert statuses["Ahmed Raza"] == "Busy"
        assert statuses["Adnan Raza"] == "Off Duty"


def test_seed_is_deterministic(app):
    with app.app_context():
        db = get_db()
        seed_demo(db, "demo-pass-1234")
        total = db.execute("SELECT COUNT(*) AS n FROM orders").fetchone()["n"]
        assert total == 300
