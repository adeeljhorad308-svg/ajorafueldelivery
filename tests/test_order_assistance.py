from datetime import UTC, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from app import timeutil
from app.db import get_db
from app.queries import services as service_queries

KARACHI = ZoneInfo("Asia/Karachi")
PASSWORD = "StrongPass1"  # noqa: S105 (test fixture password, not a secret)


def _seed_car_wash(app):
    with app.app_context():
        db = get_db()
        service_queries.create_service(db, "Car wash", "Assistance", "service", Decimal("1000.00"))
        db.commit()


def _login(client, email="user@example.com", password=PASSWORD):
    return client.post("/login", data={"email": email, "password": password})


def _payload(**overrides):
    payload = {
        "service": "Car wash",
        "vehicle_type": "Car",
        "address": "55-B Model Town, near Link Road",
        "area": "Model Town",
        "latitude": None,
        "longitude": None,
        "timing": "scheduled",
        "slot": "14",
        "note": "",
        "order_key": "assistance-key-1",
        "price_snapshot": "1000.00",
    }
    payload.update(overrides)
    return payload


def _freeze(monkeypatch, karachi_dt):
    monkeypatch.setattr(timeutil, "utcnow", lambda: karachi_dt.astimezone(UTC))


def test_car_wash_in_one_hour_is_refused(app, client, make_user, monkeypatch):
    _seed_car_wash(app)
    make_user()
    _login(client)
    # 1:30 pm Karachi, booking the 2-4 pm slot: only 30 minutes away.
    _freeze(monkeypatch, datetime(2026, 6, 15, 13, 30, tzinfo=KARACHI))

    response = client.post("/app/order/assistance", json=_payload(slot="14"))
    assert response.status_code == 400
    error = response.get_json()["errors"]["timing"]
    assert "Car wash must be booked at least 2 hours ahead" in error


def test_car_wash_near_midnight_does_not_wrap_to_tomorrow(app, client, make_user, monkeypatch):
    _seed_car_wash(app)
    make_user()
    _login(client)
    # 11:50 pm Karachi: every slot today (8 am-8 pm) has already passed.
    _freeze(monkeypatch, datetime(2026, 6, 15, 23, 50, tzinfo=KARACHI))

    response = client.post("/app/order/assistance", json=_payload(slot="18"))
    assert response.status_code == 400
    error = response.get_json()["errors"]["timing"]
    assert "Car wash must be booked at least 2 hours ahead" in error


def test_car_wash_two_hours_ahead_is_accepted(app, client, make_user, monkeypatch):
    _seed_car_wash(app)
    make_user()
    _login(client)
    # 10 am Karachi, booking the 12-2 pm slot: 2 hours away, exactly the minimum.
    _freeze(monkeypatch, datetime(2026, 6, 15, 10, 0, tzinfo=KARACHI))

    response = client.post("/app/order/assistance", json=_payload(slot="12"))
    assert response.status_code == 200
