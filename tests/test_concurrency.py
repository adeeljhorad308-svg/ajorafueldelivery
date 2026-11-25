"""Two customers ordering at the same instant must never get the same driver."""

import threading
from decimal import Decimal

from app.db import get_db
from app.queries import drivers as driver_queries
from app.queries import orders as order_queries
from app.queries import services as service_queries

PASSWORD = "StrongPass1"  # noqa: S105 (test fixture password, not a secret)


def _seed_one_driver(app):
    with app.app_context():
        db = get_db()
        service_queries.create_service(db, "Petrol", "Fuel", "litre", Decimal("252.00"))
        driver_queries.create_driver(
            db,
            "Solo Driver",
            "03001119999",
            "LEA-0001",
            "DHA",
            "Available",
            31.4697,
            74.4140,
            Decimal("4.5"),
        )
        db.commit()


def _order_payload(order_key):
    return {
        "fuel_type": "Petrol",
        "litres": 20,
        "address": "House 1, Block A",
        "area": "DHA",
        "note": "",
        "latitude": None,
        "longitude": None,
        "order_key": order_key,
        "price_snapshot": "252.00",
    }


def test_two_simultaneous_orders_with_one_free_driver_assign_only_one(app, make_user):
    _seed_one_driver(app)
    make_user(email="first@example.com", phone="03001112222")
    make_user(email="second@example.com", phone="03003334444")

    client_a = app.test_client()
    client_b = app.test_client()
    client_a.post("/login", data={"email": "first@example.com", "password": PASSWORD})
    client_b.post("/login", data={"email": "second@example.com", "password": PASSWORD})

    barrier = threading.Barrier(2)
    responses = {}

    def place(client, key, name):
        barrier.wait()
        responses[name] = client.post("/app/order/fuel", json=_order_payload(key))

    thread_a = threading.Thread(target=place, args=(client_a, "concurrent-key-a", "a"))
    thread_b = threading.Thread(target=place, args=(client_b, "concurrent-key-b", "b"))
    thread_a.start()
    thread_b.start()
    thread_a.join()
    thread_b.join()

    assert responses["a"].status_code == 200
    assert responses["b"].status_code == 200

    with app.app_context():
        db = get_db()
        order_a = order_queries.find_by_order_key(db, "concurrent-key-a")
        order_b = order_queries.find_by_order_key(db, "concurrent-key-b")
        statuses = sorted([order_a["status"], order_b["status"]])
        assert statuses == ["Assigned", "Pending"]
        assert driver_queries.count_by_status(db, "Busy") == 1
        assert driver_queries.count_by_status(db, "Available") == 0
