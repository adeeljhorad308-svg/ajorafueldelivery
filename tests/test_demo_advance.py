from decimal import Decimal

import pytest

from app.areas import AREAS
from app.db import get_db
from app.queries import assignments as assignment_queries
from app.queries import drivers as driver_queries
from app.queries import orders as order_queries
from app.queries import services as service_queries
from app.queries import tracking as tracking_queries


def _seed_petrol(app):
    with app.app_context():
        db = get_db()
        service_id = service_queries.create_service(
            db, "Petrol", "Fuel", "litre", Decimal("252.00")
        )
        db.commit()
        return service_id


def _make_order(db, user_id, service_id, order_key, **overrides):
    fields = {
        "user_id": user_id,
        "service_id": service_id,
        "order_key": order_key,
        "status": "Pending",
        "is_emergency": 0,
        "call_confirmed": 1,
        "quantity": 20,
        "total_amount": "5040.00",
        "address": "Test address",
        "area": "DHA",
        "created_at": "2026-06-15 08:00:00",
    }
    fields.update(overrides)
    return order_queries.insert_seed_order(db, **fields)


def test_pending_order_with_no_driver_refuses_to_advance(app, make_user):
    service_id = _seed_petrol(app)
    user_id = make_user()
    with app.app_context():
        db = get_db()
        order_id = _make_order(db, user_id, service_id, "key-no-driver")
        db.commit()

    runner = app.test_cli_runner()
    result = runner.invoke(args=["demo-advance", f"ORD-{order_id:04d}"])
    assert result.exit_code != 0
    assert "No Available driver" in result.output


def test_pending_to_delivered_follows_each_allowed_step(app, make_user):
    service_id = _seed_petrol(app)
    user_id = make_user()
    with app.app_context():
        db = get_db()
        driver_lat, driver_lon = AREAS["Gulberg"]
        driver_queries.create_driver(
            db,
            "Ahmed",
            "03001112233",
            "LEA-0001",
            "Gulberg",
            "Available",
            driver_lat,
            driver_lon,
            Decimal("4.5"),
        )
        order_id = _make_order(db, user_id, service_id, "key-advance", area="DHA")
        tracking_queries.add_tracking(db, order_id, "Pending", "2026-06-15 08:00:00")
        db.commit()
    customer_lat, customer_lon = AREAS["DHA"]
    order_number = f"ORD-{order_id:04d}"
    runner = app.test_cli_runner()

    first = runner.invoke(args=["demo-advance", order_number])
    assert first.exit_code == 0
    assert "Assigned" in first.output
    with app.app_context():
        order = order_queries.find_by_id(get_db(), order_id)
        driver = driver_queries.find_by_id(get_db(), order["driver_id"])
    assert order["status"] == "Assigned"
    assert driver["status"] == "Busy"

    second = runner.invoke(args=["demo-advance", order_number])
    assert second.exit_code == 0
    assert "On the way" in second.output
    with app.app_context():
        order = order_queries.find_by_id(get_db(), order_id)
    assert order["status"] == "On the Way"

    third = runner.invoke(args=["demo-advance", order_number])
    assert third.exit_code == 0
    assert "Delivered" in third.output
    with app.app_context():
        db = get_db()
        order = order_queries.find_by_id(db, order_id)
        assignment = assignment_queries.find_by_order_id(db, order_id)
        driver = driver_queries.find_by_id(db, assignment["driver_id"])
    assert order["status"] == "Delivered"
    assert assignment["completed_at"] is not None
    assert driver["status"] == "Available"
    assert float(driver["latitude"]) == pytest.approx(customer_lat)
    assert float(driver["longitude"]) == pytest.approx(customer_lon)


def test_delivered_order_cannot_be_advanced_further(app, make_user):
    service_id = _seed_petrol(app)
    user_id = make_user()
    with app.app_context():
        db = get_db()
        order_id = _make_order(db, user_id, service_id, "key-delivered", status="Delivered")
        db.commit()

    runner = app.test_cli_runner()
    result = runner.invoke(args=["demo-advance", f"ORD-{order_id:04d}"])
    assert result.exit_code != 0
    assert "cannot be moved" in result.output


def test_unknown_order_number_is_refused(app):
    runner = app.test_cli_runner()
    result = runner.invoke(args=["demo-advance", "ORD-9999"])
    assert result.exit_code != 0
    assert "No order" in result.output


def test_refuses_in_production(app):
    app.config["ENV"] = "production"
    runner = app.test_cli_runner()
    result = runner.invoke(args=["demo-advance", "ORD-0001"])
    assert result.exit_code != 0
    assert "production" in result.output.lower()
