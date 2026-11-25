from decimal import Decimal

from app import timeutil
from app.areas import AREAS
from app.db import get_db
from app.queries import drivers as driver_queries
from app.queries import orders as order_queries
from app.queries import services as service_queries
from app.queries import tracking as tracking_queries

PASSWORD = "StrongPass1"  # noqa: S105 (test fixture password, not a secret)


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


def _login(client, email="user@example.com", password=PASSWORD):
    return client.post("/login", data={"email": email, "password": password})


def test_status_api_reflects_a_change_on_the_very_next_poll(app, client, make_user):
    service_id = _seed_petrol(app)
    user_id = make_user()
    with app.app_context():
        db = get_db()
        order_id = _make_order(db, user_id, service_id, "key-poll")
        tracking_queries.add_tracking(db, order_id, "Pending", "2026-06-15 08:00:00")
        db.commit()
    _login(client)

    first = client.get(f"/api/orders/{order_id}/status")
    assert first.get_json()["status"] == "Pending"

    with app.app_context():
        db = get_db()
        order_queries.update_status(db, order_id, "Assigned")
        tracking_queries.add_tracking(db, order_id, "Assigned", "2026-06-15 08:05:00")
        db.commit()

    second = client.get(f"/api/orders/{order_id}/status")
    body = second.get_json()
    assert body["status"] == "Assigned"
    assert any(step["key"] == "assigned" and step["state"] == "current" for step in body["steps"])


def test_delivered_order_status_api_includes_delivered_text(app, client, make_user):
    service_id = _seed_petrol(app)
    user_id = make_user()
    with app.app_context():
        db = get_db()
        lat, lon = AREAS["DHA"]
        driver_id = driver_queries.create_driver(
            db, "Ahmed", "03001112233", "LEA-0001", "DHA", "Busy", lat, lon, Decimal("4.5")
        )
        order_id = _make_order(db, user_id, service_id, "key-delivered", status="On the Way")
        from app.queries import assignments as assignment_queries

        assignment_queries.create_assignment(
            db,
            order_id,
            driver_id,
            eta_minutes=10,
            assigned_at="2026-06-15 08:00:00",
            distance_km=Decimal("2.90"),
        )
        tracking_queries.add_tracking(db, order_id, "Pending", "2026-06-15 08:00:00")
        tracking_queries.add_tracking(db, order_id, "Assigned", "2026-06-15 08:01:00")
        tracking_queries.add_tracking(db, order_id, "On the Way", "2026-06-15 08:10:00")
        db.commit()
        order_queries.update_status(db, order_id, "Delivered")
        tracking_queries.add_tracking(db, order_id, "Delivered", "2026-06-15 08:30:00")
        db.commit()
    _login(client)

    response = client.get(f"/api/orders/{order_id}/status")
    body = response.get_json()
    assert body["status"] == "Delivered"
    assert body["is_finished"] is True
    expected_time = timeutil.format_time(timeutil.from_sql("2026-06-15 08:30:00"))
    assert body["delivered_label"] == f"Delivered at {expected_time}"


def test_another_users_track_page_is_404(app, client, make_user):
    service_id = _seed_petrol(app)
    make_user(email="owner@example.com", phone="03001112222")
    make_user(email="intruder@example.com", phone="03003334444")
    with app.app_context():
        db = get_db()
        from app.queries import users as user_queries

        owner_id = user_queries.find_by_email(db, "owner@example.com")["user_id"]
        order_id = _make_order(db, owner_id, service_id, "key-owner-only")
        db.commit()

    _login(client, email="intruder@example.com")
    response = client.get(f"/app/orders/{order_id}")
    assert response.status_code == 404

    api_response = client.get(f"/api/orders/{order_id}/status")
    assert api_response.status_code == 404
