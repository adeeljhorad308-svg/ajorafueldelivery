from decimal import Decimal

from app.db import get_db
from app.queries import orders as order_queries
from app.queries import services as service_queries

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


def _seed_many_orders(app, service_id, user_id, count, status="Delivered"):
    with app.app_context():
        db = get_db()
        for i in range(count):
            _make_order(
                db,
                user_id,
                service_id,
                f"key-{status}-{i}",
                status=status,
                created_at=f"2026-06-{i % 28 + 1:02d} 08:00:00",
            )
        db.commit()


def test_empty_state_when_customer_has_no_orders(app, client, make_user):
    _seed_petrol(app)
    make_user()
    _login(client)
    response = client.get("/app/orders")
    assert response.status_code == 200
    assert b"No orders yet" in response.data


def test_page_2_shows_the_next_ten_orders(app, client, make_user):
    service_id = _seed_petrol(app)
    user_id = make_user()
    _seed_many_orders(app, service_id, user_id, 15)
    _login(client)

    page_1 = client.get("/app/orders?page=1")
    page_2 = client.get("/app/orders?page=2")
    assert page_1.status_code == 200
    assert page_2.status_code == 200
    assert b"Showing 1" in page_1.data
    assert b"Showing 11" in page_2.data


def test_filter_shows_only_matching_status(app, client, make_user):
    service_id = _seed_petrol(app)
    user_id = make_user()
    _seed_many_orders(app, service_id, user_id, 3, status="Delivered")
    _seed_many_orders(app, service_id, user_id, 2, status="Cancelled")
    _login(client)

    with app.app_context():
        db = get_db()
        cancelled_count = order_queries.count_for_user_show(db, user_id, "cancelled")
        delivered_count = order_queries.count_for_user_show(db, user_id, "delivered")
    assert cancelled_count == 2
    assert delivered_count == 3

    response = client.get("/app/orders?show=cancelled")
    assert response.status_code == 200
    assert b"Showing 1\xe2\x80\x931 of 2 orders" not in response.data  # sanity: not stale text
    assert b"Cancelled" in response.data


def test_repeat_redirects_without_creating_an_order(app, client, make_user):
    service_id = _seed_petrol(app)
    user_id = make_user()
    with app.app_context():
        db = get_db()
        order_id = _make_order(
            db, user_id, service_id, "key-repeat", address="House 9, DHA", area="DHA", note="Gate 2"
        )
        db.commit()
        before_count = order_queries.count_for_user(db, user_id)
    _login(client)

    response = client.get(f"/app/orders/{order_id}/repeat")
    assert response.status_code == 302
    assert "/app/order/fuel" in response.headers["Location"]
    assert (
        "address=House" in response.headers["Location"]
        or "address=House+9" in response.headers["Location"]
    )

    with app.app_context():
        after_count = order_queries.count_for_user(get_db(), user_id)
    assert after_count == before_count


def test_repeat_on_another_users_order_is_404(app, client, make_user):
    service_id = _seed_petrol(app)
    make_user(email="owner@example.com", phone="03001112222")
    make_user(email="intruder@example.com", phone="03003334444")
    with app.app_context():
        db = get_db()
        from app.queries import users as user_queries

        owner_id = user_queries.find_by_email(db, "owner@example.com")["user_id"]
        order_id = _make_order(db, owner_id, service_id, "key-repeat-owner")
        db.commit()

    _login(client, email="intruder@example.com")
    response = client.get(f"/app/orders/{order_id}/repeat")
    assert response.status_code == 404
