from decimal import Decimal

from app.db import get_db
from app.queries import orders as order_queries
from app.queries import services as service_queries

PASSWORD = "StrongPass1"  # noqa: S105 (test fixture password, not a secret)


def _seed_fuel_services(app):
    with app.app_context():
        db = get_db()
        service_queries.create_service(db, "Petrol", "Fuel", "litre", Decimal("252.00"))
        service_queries.create_service(db, "Diesel", "Fuel", "litre", Decimal("258.00"))
        db.commit()


def _login(client, email="user@example.com", password=PASSWORD):
    return client.post("/login", data={"email": email, "password": password})


def _order_payload(**overrides):
    payload = {
        "fuel_type": "Petrol",
        "litres": 20,
        "address": "House 12, Block C",
        "area": "Johar Town",
        "note": "",
        "latitude": None,
        "longitude": None,
        "order_key": "test-order-key-1",
        "price_snapshot": "252.00",
    }
    payload.update(overrides)
    return payload


def test_litres_below_minimum_is_refused(app, client, make_user):
    _seed_fuel_services(app)
    make_user()
    _login(client)
    response = client.post("/app/order/fuel", json=_order_payload(litres=4))
    assert response.status_code == 400
    assert "litres" in response.get_json()["errors"]


def test_litres_above_maximum_is_refused(app, client, make_user):
    _seed_fuel_services(app)
    make_user()
    _login(client)
    response = client.post("/app/order/fuel", json=_order_payload(litres=101))
    assert response.status_code == 400
    assert "litres" in response.get_json()["errors"]


def test_total_equals_quantity_times_db_price(app, client, make_user):
    _seed_fuel_services(app)
    make_user()
    _login(client)
    payload = _order_payload(fuel_type="Diesel", litres=35, price_snapshot="258.00")
    response = client.post("/app/order/fuel", json=payload)
    assert response.status_code == 200
    order_id = int(response.get_json()["redirect"].split("/")[3])
    with app.app_context():
        order = order_queries.find_by_id_for_user(get_db(), order_id, 1)
    assert Decimal(str(order["total_amount"])) == Decimal("9030.00")


def test_double_submit_with_same_order_key_makes_one_order(app, client, make_user):
    _seed_fuel_services(app)
    make_user()
    _login(client)
    first = client.post("/app/order/fuel", json=_order_payload())
    second = client.post("/app/order/fuel", json=_order_payload())
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.get_json()["redirect"] == second.get_json()["redirect"]
    with app.app_context():
        count = order_queries.count_for_user(get_db(), 1)
    assert count == 1


def test_another_users_order_is_404(app, client, make_user):
    _seed_fuel_services(app)
    make_user(email="owner@example.com", phone="03001112222")
    make_user(email="intruder@example.com", phone="03003334444")
    _login(client, email="owner@example.com")
    response = client.post("/app/order/fuel", json=_order_payload())
    order_id = int(response.get_json()["redirect"].split("/")[3])

    client.post("/logout")
    _login(client, email="intruder@example.com")
    confirmed = client.get(f"/app/orders/{order_id}/confirmed")
    assert confirmed.status_code == 404


def test_stale_price_shows_price_updated_state_and_does_not_place_order(app, client, make_user):
    _seed_fuel_services(app)
    make_user()
    _login(client)
    response = client.post("/app/order/fuel", json=_order_payload(price_snapshot="999.00"))
    assert response.status_code == 409
    body = response.get_json()
    assert body["status"] == "price_updated"
    assert body["unit_price"] == "252.00"
    assert body["total"] == "5040.00"
    with app.app_context():
        count = order_queries.count_for_user(get_db(), 1)
    assert count == 0
