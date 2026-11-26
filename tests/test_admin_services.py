"""C12: services and prices (docs/SPEC.md screen 17, pop-up 5)."""

from decimal import Decimal

from app import money
from app.db import get_db
from app.queries import orders as order_queries
from app.queries import services as service_queries
from app.queries import users as user_queries

PASSWORD = "StrongPass1"  # noqa: S105 (test fixture password, not a secret)


def _login_as_admin(client, app, email="admin@example.com"):
    with app.app_context():
        db = get_db()
        admin = user_queries.find_by_email(db, email)
        admin_id = admin["user_id"]
    with client.session_transaction() as session:
        session["user_id"] = admin_id
        session["role"] = "admin"
        session["session_version"] = 0
    return admin_id


def _seed_petrol(app):
    with app.app_context():
        db = get_db()
        service_id = service_queries.create_service(
            db, "Petrol", "Fuel", "litre", Decimal("252.00")
        )
        db.commit()
        return service_id


def _service_payload(**overrides):
    payload = {
        "name": "Petrol",
        "category": "Fuel",
        "unit": "litre",
        "unit_price": "252.00",
        "available": "1",
    }
    payload.update(overrides)
    return payload


def test_customer_gets_403_on_services_routes(app, client, make_user):
    service_id = _seed_petrol(app)
    user_id = make_user(email="cust@example.com", password=PASSWORD)
    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["role"] = "customer"
        session["session_version"] = 0
    assert client.get("/admin/services").status_code == 403
    assert client.post("/admin/services", data=_service_payload()).status_code == 403
    assert client.post(f"/admin/services/{service_id}", data=_service_payload()).status_code == 403


def test_add_service_rejects_duplicate_name(app, client, make_user):
    _seed_petrol(app)
    make_user(email="admin@example.com", password=PASSWORD, phone="03000000001", role="admin")
    _login_as_admin(client, app)

    response = client.post("/admin/services", data=_service_payload(name="Petrol"))
    assert response.status_code == 400
    assert "A service with this name already exists" in response.data.decode()
    with app.app_context():
        db = get_db()
        assert db.execute("SELECT COUNT(*) AS n FROM services").fetchone()["n"] == 1


def test_add_service_rejects_duplicate_name_case_insensitive(app, client, make_user):
    _seed_petrol(app)
    make_user(email="admin@example.com", password=PASSWORD, phone="03000000001", role="admin")
    _login_as_admin(client, app)

    response = client.post("/admin/services", data=_service_payload(name="PETROL"))
    assert response.status_code == 400
    assert "A service with this name already exists" in response.data.decode()


def test_add_service_rejects_zero_and_negative_price(app, client, make_user):
    make_user(email="admin@example.com", password=PASSWORD, phone="03000000001", role="admin")
    _login_as_admin(client, app)

    for bad_price in ("0", "-5", "-5.00"):
        response = client.post(
            "/admin/services", data=_service_payload(name="Tyre help", unit_price=bad_price)
        )
        assert response.status_code == 400
        assert "Price must be above 0" in response.data.decode()
    with app.app_context():
        db = get_db()
        assert db.execute("SELECT COUNT(*) AS n FROM services").fetchone()["n"] == 0


def test_add_service_rejects_three_decimal_places(app, client, make_user):
    make_user(email="admin@example.com", password=PASSWORD, phone="03000000001", role="admin")
    _login_as_admin(client, app)

    response = client.post(
        "/admin/services", data=_service_payload(name="Tyre help", unit_price="5.123")
    )
    assert response.status_code == 400
    assert "at most 2 decimals" in response.data.decode()


def test_add_service_success_shows_in_list(app, client, make_user):
    make_user(email="admin@example.com", password=PASSWORD, phone="03000000001", role="admin")
    _login_as_admin(client, app)

    response = client.post(
        "/admin/services",
        data=_service_payload(
            name="Tyre help", category="Assistance", unit="service", unit_price="600"
        ),
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "Tyre help" in response.data.decode()
    with app.app_context():
        db = get_db()
        row = service_queries.find_by_name(db, "Tyre help")
        assert row is not None
        assert row["available"] == 1


def test_turning_off_hides_service_from_customers_and_order_post(app, client, make_user):
    service_id = _seed_petrol(app)
    make_user(email="admin@example.com", password=PASSWORD, phone="03000000001", role="admin")
    make_user(email="cust@example.com", password=PASSWORD)
    _login_as_admin(client, app)

    response = client.post(
        f"/admin/services/{service_id}",
        data=_service_payload(available="0"),
        follow_redirects=True,
    )
    assert response.status_code == 200

    with app.app_context():
        db = get_db()
        row = service_queries.find_by_id(db, service_id)
        assert row["available"] == 0

    # A second client session: the customer no longer sees Petrol, and
    # placing an order against it is refused server-side either way.
    customer_client = app.test_client()
    with app.app_context():
        db = get_db()
        cust = user_queries.find_by_email(db, "cust@example.com")
    with customer_client.session_transaction() as session:
        session["user_id"] = cust["user_id"]
        session["role"] = "customer"
        session["session_version"] = 0

    home = customer_client.get("/app")
    assert "Petrol" not in home.data.decode()

    order_response = customer_client.post(
        "/app/order/fuel",
        json={
            "fuel_type": "Petrol",
            "litres": 20,
            "address": "House 1",
            "area": "DHA",
            "order_key": "test-off-key",
            "price_snapshot": "252.00",
        },
    )
    assert order_response.status_code == 400


def test_price_change_does_not_touch_existing_order_totals(app, client, make_user):
    service_id = _seed_petrol(app)
    make_user(email="admin@example.com", password=PASSWORD, phone="03000000001", role="admin")
    user_id = make_user(email="cust@example.com", password=PASSWORD)
    with app.app_context():
        db = get_db()
        order_id = order_queries.insert_order(
            db, user_id, service_id, "k1", 20, "5040.00", "addr", "DHA", 31.47, 74.41, None
        )
        db.commit()
    _login_as_admin(client, app)

    response = client.post(
        f"/admin/services/{service_id}",
        data=_service_payload(unit_price="300.00"),
        follow_redirects=True,
    )
    assert response.status_code == 200

    with app.app_context():
        db = get_db()
        order = order_queries.find_by_id(db, order_id)
        assert money.from_db(order["total_amount"]) == Decimal("5040.00")
        service = service_queries.find_by_id(db, service_id)
        assert money.from_db(service["unit_price"]) == Decimal("300.00")
