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


def _payload(**overrides):
    payload = {
        "fuel_type": "Diesel",
        "litres": 250,
        "generator_type": "Generator",
        "address": "Farm 7, Mauza Kot",
        "area": "Township",
        "latitude": None,
        "longitude": None,
        "timing": "asap",
        "order_key": "generator-key-1",
        "price_snapshot": "258.00",
    }
    payload.update(overrides)
    return payload


def test_19_litres_is_refused(app, client, make_user):
    _seed_fuel_services(app)
    make_user()
    _login(client)
    response = client.post("/app/order/generator", json=_payload(litres=19))
    assert response.status_code == 400
    assert "litres" in response.get_json()["errors"]


def test_501_litres_is_refused(app, client, make_user):
    _seed_fuel_services(app)
    make_user()
    _login(client)
    response = client.post("/app/order/generator", json=_payload(litres=501))
    assert response.status_code == 400
    assert "litres" in response.get_json()["errors"]


def test_201_litres_sets_call_confirmed_false_and_stays_pending(app, client, make_user):
    _seed_fuel_services(app)
    make_user()
    _login(client)
    response = client.post("/app/order/generator", json=_payload(litres=201))
    assert response.status_code == 200
    order_id = int(response.get_json()["redirect"].split("/")[3])
    with app.app_context():
        order = order_queries.find_by_id_for_user(get_db(), order_id, 1)
    assert order["status"] == "Pending"
    assert order["call_confirmed"] == 0
