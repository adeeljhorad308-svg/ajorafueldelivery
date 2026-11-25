"""C9: admin dashboard and All orders (docs/SPEC.md screens 12-13)."""

from datetime import timedelta
from decimal import Decimal

from app import timeutil
from app.db import get_db
from app.queries import assignments as assignment_queries
from app.queries import drivers as driver_queries
from app.queries import orders as order_queries
from app.queries import services as service_queries
from app.queries import users as user_queries

PASSWORD = "StrongPass1"  # noqa: S105 (test fixture password, not a secret)
ADMIN_URLS = ("/admin", "/admin/orders", "/api/admin/live")


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
        "created_at": timeutil.to_sql(timeutil.utcnow()),
    }
    fields.update(overrides)
    return order_queries.insert_seed_order(db, **fields)


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


def test_guest_redirected_to_login_on_every_admin_url(client):
    for url in ADMIN_URLS:
        response = client.get(url, follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["Location"].startswith("/login")


def test_customer_gets_403_on_every_admin_url(client, make_user):
    user_id = make_user(email="customer@example.com", role="customer")
    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["role"] = "customer"
        session["session_version"] = 0
    for url in ADMIN_URLS:
        response = client.get(url)
        assert response.status_code == 403


def test_dashboard_counts_match_seeded_data(app, client, make_user):
    service_id = _seed_petrol(app)
    make_user(email="admin@example.com", password=PASSWORD, phone="03000000001", role="admin")
    ali_id = make_user(email="ali@example.com", password=PASSWORD, phone="03001112222")
    bilal_id = make_user(email="bilal@example.com", password=PASSWORD, phone="03003334444")

    with app.app_context():
        db = get_db()
        now = timeutil.utcnow()
        driver_id = driver_queries.create_driver(
            db, "Ahmed", "03005556666", "LEA-0001", "DHA", "Available", 31.47, 74.41, Decimal("4.5")
        )

        # Delivered today -> counts in "Sales today".
        delivered_id = _make_order(
            db, ali_id, service_id, "k-delivered", status="Delivered", total_amount="5040.00"
        )
        assignment_queries.create_assignment(
            db,
            delivered_id,
            driver_id,
            eta_minutes=10,
            assigned_at=timeutil.to_sql(now - timedelta(hours=1)),
            completed_at=timeutil.to_sql(now - timedelta(minutes=5)),
        )

        # Two open emergencies: Sana's is the older one.
        _make_order(
            db,
            bilal_id,
            service_id,
            "k-emergency-new",
            status="Pending",
            is_emergency=1,
            quantity=5,
            total_amount="1260.00",
            created_at=timeutil.to_sql(now - timedelta(minutes=3)),
        )
        _make_order(
            db,
            ali_id,
            service_id,
            "k-emergency-old",
            status="Pending",
            is_emergency=1,
            quantity=10,
            total_amount="2520.00",
            created_at=timeutil.to_sql(now - timedelta(minutes=6)),
        )

        # A call-needed generator-style order (call_confirmed = 0).
        _make_order(db, ali_id, service_id, "k-call-needed", status="Pending", call_confirmed=0)

        # Yesterday's order must not count towards "Orders today".
        _make_order(
            db,
            bilal_id,
            service_id,
            "k-yesterday",
            status="Delivered",
            created_at=timeutil.to_sql(now - timedelta(days=1, hours=1)),
        )
        db.commit()

    _login_as_admin(client, app)
    response = client.get("/admin")
    assert response.status_code == 200
    body = response.data.decode()

    assert '<p class="stat-card__value mono-stat">4</p>' in body  # 4 orders created today
    assert '<p class="stat-card__value mono-stat">2</p>' in body  # 2 open emergencies
    assert "PKR 5,040" in body  # sales today
    assert "Oldest waiting 6 min" in body
    assert "2 emergency requests waiting" in body
    assert "ORD-0004" in body  # the call-needed order appears in Call needed


def test_filters_combine_status_service_and_emergency(app, client, make_user):
    service_id = _seed_petrol(app)
    make_user(email="admin@example.com", password=PASSWORD, phone="03000000001", role="admin")
    user_id = make_user(email="cust@example.com", password=PASSWORD)

    with app.app_context():
        db = get_db()
        _make_order(
            db, user_id, service_id, "k-pending-emergency", status="Pending", is_emergency=1
        )
        _make_order(db, user_id, service_id, "k-pending-normal", status="Pending")
        _make_order(
            db, user_id, service_id, "k-delivered-emergency", status="Delivered", is_emergency=1
        )
        db.commit()

    _login_as_admin(client, app)
    response = client.get("/admin/orders?status=Pending&emergency=1")
    assert response.status_code == 200
    body = response.data.decode()
    assert "ORD-0001" in body
    assert "ORD-0002" not in body
    assert "ORD-0003" not in body


def test_open_emergency_is_always_pinned_first(app, client, make_user):
    service_id = _seed_petrol(app)
    make_user(email="admin@example.com", password=PASSWORD, phone="03000000001", role="admin")
    user_id = make_user(email="cust@example.com", password=PASSWORD)

    with app.app_context():
        db = get_db()
        now = timeutil.utcnow()
        # Newest first would normally put this on top, but it isn't an emergency.
        _make_order(
            db,
            user_id,
            service_id,
            "k-newest-normal",
            status="Pending",
            created_at=timeutil.to_sql(now),
        )
        _make_order(
            db,
            user_id,
            service_id,
            "k-older-emergency",
            status="Pending",
            is_emergency=1,
            created_at=timeutil.to_sql(now - timedelta(minutes=30)),
        )
        db.commit()

    _login_as_admin(client, app)
    response = client.get("/admin/orders")
    body = response.data.decode()
    assert body.index("ORD-0002") < body.index("ORD-0001")


def test_search_by_order_number_and_phone(app, client, make_user):
    service_id = _seed_petrol(app)
    make_user(email="admin@example.com", password=PASSWORD, role="admin")
    ali_id = make_user(email="ali@example.com", password=PASSWORD, phone="03001234567")
    bilal_id = make_user(email="bilal@example.com", password=PASSWORD, phone="03009998888")

    with app.app_context():
        db = get_db()
        _make_order(db, ali_id, service_id, "k-ali")
        _make_order(db, bilal_id, service_id, "k-bilal")
        db.commit()

    _login_as_admin(client, app)

    by_number = client.get("/admin/orders?q=ORD-0001").data.decode()
    assert "ORD-0001" in by_number
    assert "ORD-0002" not in by_number

    by_phone = client.get("/admin/orders?q=0300-999-8888").data.decode()
    assert "ORD-0002" in by_phone
    assert "ORD-0001" not in by_phone


def test_sql_injection_in_search_returns_no_error(app, client, make_user):
    """docs/SECURITY.md checklist 14: an injection attempt is just more
    unmatched search text - no SQL error, and the parameterised query never
    runs it as SQL (it has no digits, so the search is simply ignored and
    every other filter still applies normally)."""
    service_id = _seed_petrol(app)
    make_user(email="admin@example.com", password=PASSWORD, phone="03000000001", role="admin")
    user_id = make_user(email="cust@example.com", password=PASSWORD)
    with app.app_context():
        db = get_db()
        _make_order(db, user_id, service_id, "k1")
        db.commit()

    _login_as_admin(client, app)
    response = client.get("/admin/orders?q=' OR 1=1 --")
    assert response.status_code == 200
    assert "ORD-0001" in response.data.decode()

    response_with_digits = client.get("/admin/orders?q=1; DROP TABLE orders; --")
    assert response_with_digits.status_code == 200
    with app.app_context():
        db = get_db()
        assert db.execute("SELECT COUNT(*) AS n FROM orders").fetchone()["n"] == 1


def test_pagination_shows_20_per_page(app, client, make_user):
    service_id = _seed_petrol(app)
    make_user(email="admin@example.com", password=PASSWORD, phone="03000000001", role="admin")
    user_id = make_user(email="cust@example.com", password=PASSWORD)
    with app.app_context():
        db = get_db()
        for i in range(25):
            _make_order(db, user_id, service_id, f"k-{i}")
        db.commit()

    _login_as_admin(client, app)
    page1 = client.get("/admin/orders").data.decode()
    assert "Showing 1–20 of 25 orders" in page1
    assert "ORD-0025" in page1  # newest first
    assert "ORD-0001" not in page1

    page2 = client.get("/admin/orders?page=2").data.decode()
    assert "Showing 21–25 of 25 orders" in page2
    assert "ORD-0001" in page2


def test_empty_filters_show_clear_filters_action(app, client, make_user):
    _seed_petrol(app)
    make_user(email="admin@example.com", password=PASSWORD, role="admin")
    _login_as_admin(client, app)
    response = client.get("/admin/orders?status=Cancelled&emergency=1")
    assert response.status_code == 200
    assert "No orders match these filters" in response.data.decode()
    assert "Clear filters" in response.data.decode()
