from decimal import Decimal

from app.db import get_db
from app.queries import drivers as driver_queries
from app.queries import orders as order_queries
from app.queries import services as service_queries

PASSWORD = "StrongPass1"  # noqa: S105 (test fixture password, not a secret)


def _seed_fuel_services(app):
    with app.app_context():
        db = get_db()
        service_queries.create_service(db, "Petrol", "Fuel", "litre", Decimal("252.00"))
        service_queries.create_service(db, "Diesel", "Fuel", "litre", Decimal("258.00"))
        db.commit()


def _seed_driver(app, name="Solo Driver", phone="03001119999", vehicle_no="LEA-0001", area="DHA"):
    with app.app_context():
        db = get_db()
        driver_queries.create_driver(
            db, name, phone, vehicle_no, area, "Available", 31.4697, 74.4140, Decimal("4.5")
        )
        db.commit()


def _login(client, email="user@example.com", password=PASSWORD):
    return client.post("/login", data={"email": email, "password": password})


def _payload(**overrides):
    payload = {
        "fuel_type": "Petrol",
        "litres": 5,
        "note": "White Corolla near exit 4",
        "area": "DHA",
        "latitude": None,
        "longitude": None,
        "order_key": "emergency-key-1",
        "price_snapshot": "252.00",
    }
    payload.update(overrides)
    return payload


def test_11_litre_emergency_is_refused(app, client, make_user):
    _seed_fuel_services(app)
    make_user()
    _login(client)
    response = client.post("/app/order/emergency", json=_payload(litres=11))
    assert response.status_code == 400
    assert "litres" in response.get_json()["errors"]


def test_second_open_emergency_is_refused(app, client, make_user):
    _seed_fuel_services(app)
    make_user()
    _login(client)
    first = client.post("/app/order/emergency", json=_payload(order_key="emergency-key-a"))
    assert first.status_code == 200

    second = client.post("/app/order/emergency", json=_payload(order_key="emergency-key-b"))
    assert second.status_code == 409
    body = second.get_json()
    assert body["status"] == "already_open"
    assert "track_url" in body

    with app.app_context():
        count = order_queries.count_for_user(get_db(), 1)
    assert count == 1


def test_emergency_order_is_dispatched_ahead_of_an_older_pending_order(app, client, make_user):
    _seed_fuel_services(app)
    make_user()
    _login(client)

    older = client.post(
        "/app/order/fuel",
        json={
            "fuel_type": "Petrol",
            "litres": 20,
            "address": "House 1",
            "area": "DHA",
            "note": "",
            "latitude": None,
            "longitude": None,
            "order_key": "older-normal-order",
            "price_snapshot": "252.00",
        },
    )
    older_id = int(older.get_json()["redirect"].split("/")[3])
    with app.app_context():
        db = get_db()
        older_order = order_queries.find_by_id_for_user(db, older_id, 1)
    assert older_order["status"] == "Pending"

    _seed_driver(app)
    emergency = client.post("/app/order/emergency", json=_payload())
    emergency_id = int(emergency.get_json()["redirect"].split("/")[3])

    with app.app_context():
        db = get_db()
        older_order = order_queries.find_by_id_for_user(db, older_id, 1)
        emergency_order = order_queries.find_by_id_for_user(db, emergency_id, 1)
    assert emergency_order["status"] == "Assigned"
    assert older_order["status"] == "Pending"


def test_another_users_emergency_confirmed_page_and_status_api_are_404(app, client, make_user):
    _seed_fuel_services(app)
    make_user(email="owner@example.com", phone="03001112222")
    make_user(email="intruder@example.com", phone="03003334444")
    _login(client, email="owner@example.com")
    response = client.post("/app/order/emergency", json=_payload())
    order_id = int(response.get_json()["redirect"].split("/")[3])

    client.post("/logout")
    _login(client, email="intruder@example.com")
    confirmed = client.get(f"/app/orders/{order_id}/confirmed")
    assert confirmed.status_code == 404
    status = client.get(f"/api/orders/{order_id}/status")
    assert status.status_code == 404
