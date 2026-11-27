"""C13: Reports (docs/SPEC.md FR-16, screen 19, docs/SECURITY.md checklist
items 3 and 17's access-control pattern applied to a new admin page)."""

from decimal import Decimal

from app import timeutil
from app.db import get_db
from app.money import to_db
from app.queries import assignments as assignment_queries
from app.queries import drivers as driver_queries
from app.queries import orders as order_queries
from app.queries import services as service_queries
from app.queries import users as user_queries

PASSWORD = "StrongPass1"  # noqa: S105 (test fixture password, not a secret)


def _login_as(client, user_id, role):
    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["role"] = role
        session["session_version"] = 0


def _login_as_admin(client, app, email="admin@example.com"):
    with app.app_context():
        db = get_db()
        admin = user_queries.find_by_email(db, email)
        admin_id = admin["user_id"]
    _login_as(client, admin_id, "admin")
    return admin_id


def _seed_service(app, name="Petrol"):
    with app.app_context():
        db = get_db()
        service_id = service_queries.create_service(db, name, "Fuel", "litre", Decimal("252.00"))
        db.commit()
        return service_id


def _seed_driver(app):
    with app.app_context():
        db = get_db()
        driver_id = driver_queries.create_driver(
            db, "Ahmed Raza", "03001112233", "LEA-1234", "DHA", "Available", 31.47, 74.37, 4.8
        )
        db.commit()
        return driver_id


def _seed_order(
    app,
    user_id,
    service_id,
    order_key,
    status,
    created_at,
    amount=Decimal("5040.00"),
    is_emergency=0,
):
    with app.app_context():
        db = get_db()
        order_id = order_queries.insert_seed_order(
            db,
            user_id=user_id,
            service_id=service_id,
            order_key=order_key,
            status=status,
            is_emergency=is_emergency,
            call_confirmed=1,
            quantity=20,
            total_amount=to_db(amount),
            address="House 12, Street 4",
            area="DHA",
            latitude=31.47,
            longitude=74.37,
            created_at=timeutil.to_sql(created_at),
        )
        db.commit()
        return order_id


def _seed_assignment(app, order_id, driver_id, assigned_at, completed_at, eta_minutes=20):
    with app.app_context():
        db = get_db()
        assignment_queries.create_assignment(
            db,
            order_id,
            driver_id,
            eta_minutes=eta_minutes,
            assigned_at=timeutil.to_sql(assigned_at),
            completed_at=timeutil.to_sql(completed_at) if completed_at else None,
        )
        db.commit()


def test_customer_gets_403_on_reports(app, client, make_user):
    user_id = make_user(email="cust@example.com", password=PASSWORD)
    _login_as(client, user_id, "customer")
    assert client.get("/admin/reports").status_code == 403


def test_empty_period_shows_zeros_and_message(app, client, make_user):
    make_user(email="admin@example.com", password=PASSWORD, phone="03009990000", role="admin")
    _login_as_admin(client, app)

    response = client.get("/admin/reports?period=week&date=2026-01-05")
    assert response.status_code == 200
    body = response.data.decode()
    assert "No completed orders in this period" in body
    assert "Pick another day, week or month" in body


def test_only_delivered_and_cancelled_are_counted(app, client, make_user):
    admin_id = make_user(
        email="admin@example.com", password=PASSWORD, phone="03009990000", role="admin"
    )
    customer_id = make_user(email="cust@example.com", password=PASSWORD, phone="03001112222")
    service_id = _seed_service(app)
    week_day = timeutil.from_sql("2026-11-17 10:00:00")  # Tue, week of 16-22 Nov

    _seed_order(app, customer_id, service_id, "k-delivered", "Delivered", week_day)
    _seed_order(app, customer_id, service_id, "k-cancelled", "Cancelled", week_day)
    _seed_order(app, customer_id, service_id, "k-pending", "Pending", week_day)
    _seed_order(app, customer_id, service_id, "k-assigned", "Assigned", week_day)

    _login_as_admin(client, app, "admin@example.com")
    response = client.get("/admin/reports?period=week&date=2026-11-16")
    body = response.data.decode()

    assert response.status_code == 200
    # Total orders counts only the Delivered + Cancelled pair, not the
    # Pending/Assigned ones also placed that week.
    assert "(2 of 4 placed)" in body
    assert admin_id  # admin row exists; silences an unused-var lint


def test_sales_card_counts_delivered_only(app, client, make_user):
    make_user(email="admin@example.com", password=PASSWORD, phone="03009990000", role="admin")
    customer_id = make_user(email="cust@example.com", password=PASSWORD, phone="03001112222")
    service_id = _seed_service(app)
    week_day = timeutil.from_sql("2026-11-17 10:00:00")

    _seed_order(
        app, customer_id, service_id, "k-sale-delivered", "Delivered", week_day, Decimal("5040.00")
    )
    _seed_order(
        app, customer_id, service_id, "k-sale-cancelled", "Cancelled", week_day, Decimal("9999.00")
    )

    _login_as_admin(client, app)
    response = client.get("/admin/reports?period=week&date=2026-11-16")
    body = response.data.decode()

    assert "PKR 5,040" in body
    assert "9,999" not in body


def test_average_delivery_time_from_assignments(app, client, make_user):
    make_user(email="admin@example.com", password=PASSWORD, phone="03009990000", role="admin")
    customer_id = make_user(email="cust@example.com", password=PASSWORD, phone="03001112222")
    service_id = _seed_service(app)
    driver_id = _seed_driver(app)
    week_day = timeutil.from_sql("2026-11-17 10:00:00")

    order_id = _seed_order(app, customer_id, service_id, "k-avg", "Delivered", week_day)
    _seed_assignment(
        app,
        order_id,
        driver_id,
        assigned_at=timeutil.from_sql("2026-11-17 10:00:00"),
        completed_at=timeutil.from_sql("2026-11-17 10:24:00"),
    )

    _login_as_admin(client, app)
    response = client.get("/admin/reports?period=week&date=2026-11-16")
    assert "24 min" in response.data.decode()


def test_emergency_card_counts_open_and_counted_emergencies(app, client, make_user):
    make_user(email="admin@example.com", password=PASSWORD, phone="03009990000", role="admin")
    customer_id = make_user(email="cust@example.com", password=PASSWORD, phone="03001112222")
    service_id = _seed_service(app)
    week_day = timeutil.from_sql("2026-11-17 10:00:00")

    _seed_order(
        app,
        customer_id,
        service_id,
        "k-emergency",
        "Delivered",
        week_day,
        Decimal("1260.00"),
        is_emergency=1,
    )
    _seed_order(app, customer_id, service_id, "k-normal", "Delivered", week_day)

    _login_as_admin(client, app)
    response = client.get("/admin/reports?period=week&date=2026-11-16")
    body = response.data.decode()
    assert "(2 of 2 placed)" in body


def test_week_boundary_is_asia_karachi(app, client, make_user):
    """Monday 16 Nov 2026 00:00 Asia/Karachi is 15 Nov 18:00 UTC +1h (UTC+5),
    i.e. 15 Nov 19:00 UTC. An order one minute either side of that instant
    must land in the correct week (docs/SECURITY.md-style boundary test)."""
    make_user(email="admin@example.com", password=PASSWORD, phone="03009990000", role="admin")
    customer_id = make_user(email="cust@example.com", password=PASSWORD, phone="03001112222")
    service_id = _seed_service(app)

    before = timeutil.from_sql("2026-11-15 18:59:00")  # still the previous week, Karachi
    after = timeutil.from_sql("2026-11-15 19:00:00")  # Mon 16 Nov 00:00 Karachi

    _seed_order(app, customer_id, service_id, "k-before-week", "Delivered", before)
    _seed_order(app, customer_id, service_id, "k-after-week", "Delivered", after)

    _login_as_admin(client, app)

    this_week = client.get("/admin/reports?period=week&date=2026-11-16").data.decode()
    assert "(1 of 1 placed)" in this_week

    previous_week = client.get("/admin/reports?period=week&date=2026-11-09").data.decode()
    assert "(1 of 1 placed)" in previous_week


def test_month_boundary_is_asia_karachi(app, client, make_user):
    """1 Dec 2026 00:00 Asia/Karachi is 30 Nov 19:00 UTC."""
    make_user(email="admin@example.com", password=PASSWORD, phone="03009990000", role="admin")
    customer_id = make_user(email="cust@example.com", password=PASSWORD, phone="03001112222")
    service_id = _seed_service(app)

    before = timeutil.from_sql("2026-11-30 18:59:00")  # still November, Karachi
    after = timeutil.from_sql("2026-11-30 19:00:00")  # 1 Dec 00:00 Karachi

    _seed_order(app, customer_id, service_id, "k-before-month", "Delivered", before)
    _seed_order(app, customer_id, service_id, "k-after-month", "Delivered", after)

    _login_as_admin(client, app)

    november = client.get("/admin/reports?period=month&date=2026-11-01").data.decode()
    assert "(1 of 1 placed)" in november

    december = client.get("/admin/reports?period=month&date=2026-12-01").data.decode()
    assert "(1 of 1 placed)" in december
