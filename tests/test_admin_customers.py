"""C11: customers (docs/SPEC.md screen 16, pop-up 4)."""

from decimal import Decimal

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


def test_customer_gets_403_on_every_new_route(app, client, make_user):
    user_id = make_user(email="cust@example.com", password=PASSWORD)
    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["role"] = "customer"
        session["session_version"] = 0
    assert client.get("/admin/customers").status_code == 403
    assert client.get(f"/admin/customers/{user_id}").status_code == 403
    assert client.post(f"/admin/customers/{user_id}/block", data={}).status_code == 403


def test_search_by_name_email_or_phone(app, client, make_user):
    make_user(email="admin@example.com", password=PASSWORD, phone="03000000001", role="admin")
    make_user(
        email="ali.raza@example.com",
        password=PASSWORD,
        phone="03001234567",
        full_name="Ali Raza",
    )
    make_user(
        email="bilal.khan@example.com",
        password=PASSWORD,
        phone="03009998888",
        full_name="Bilal Khan",
    )
    _login_as_admin(client, app)

    by_name = client.get("/admin/customers?q=Ali").data.decode()
    assert "Ali Raza" in by_name
    assert "Bilal Khan" not in by_name

    by_phone = client.get("/admin/customers?q=03009998888").data.decode()
    assert "Bilal Khan" in by_phone
    assert "Ali Raza" not in by_phone

    by_email = client.get("/admin/customers?q=bilal.khan@example.com").data.decode()
    assert "Bilal Khan" in by_email


def test_search_sql_injection_returns_no_error(app, client, make_user):
    make_user(email="admin@example.com", password=PASSWORD, role="admin")
    make_user(email="ali@example.com", password=PASSWORD, phone="03001234567", full_name="Ali Raza")
    _login_as_admin(client, app)

    response = client.get("/admin/customers?q=' OR 1=1 --")
    assert response.status_code == 200
    with app.app_context():
        db = get_db()
        assert db.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"] == 2

    response = client.get("/admin/customers?q=1; DROP TABLE users; --")
    assert response.status_code == 200
    with app.app_context():
        db = get_db()
        assert db.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"] == 2


def test_admins_never_appear_in_customer_list_or_panel(app, client, make_user):
    admin_id = make_user(
        email="admin@example.com", password=PASSWORD, phone="03000000001", role="admin"
    )
    make_user(email="other-admin@example.com", password=PASSWORD, phone="03000000002", role="admin")
    _login_as_admin(client, app)

    body = client.get("/admin/customers").data.decode()
    assert "admin@example.com" not in body
    assert "other-admin@example.com" not in body
    assert client.get(f"/admin/customers/{admin_id}").status_code == 404


def test_admin_cannot_block_an_admin_or_self(app, client, make_user):
    admin_id = make_user(
        email="admin@example.com", password=PASSWORD, phone="03000000001", role="admin"
    )
    _login_as_admin(client, app)
    response = client.post(f"/admin/customers/{admin_id}/block", data={"action": "block"})
    assert response.status_code == 404
    with app.app_context():
        db = get_db()
        admin = user_queries.find_by_id(db, admin_id)
        assert admin["is_active"] == 1


def test_block_logs_customer_out_on_next_click(app, client, make_user):
    make_user(email="admin@example.com", password=PASSWORD, phone="03000000001", role="admin")
    customer_id = make_user(email="cust@example.com", password=PASSWORD, phone="03001112223")
    _login_as_admin(client, app)

    customer_client = app.test_client()
    with customer_client.session_transaction() as session:
        session["user_id"] = customer_id
        session["role"] = "customer"
        session["session_version"] = 0
    assert customer_client.get("/app").status_code == 200

    response = client.post(
        f"/admin/customers/{customer_id}/block", data={"action": "block"}, follow_redirects=True
    )
    assert response.status_code == 200
    with app.app_context():
        db = get_db()
        customer = user_queries.find_by_id(db, customer_id)
        assert customer["is_active"] == 0
        assert customer["session_version"] == 1

    # Same session cookie as before blocking - the next click still finds it
    # stale (is_active/session_version checked on every request) and is sent
    # back to the landing/login flow instead of the page it asked for.
    next_response = customer_client.get("/app", follow_redirects=False)
    assert next_response.status_code in (302, 303)


def test_unblock_makes_customer_active_again(app, client, make_user):
    make_user(email="admin@example.com", password=PASSWORD, phone="03000000001", role="admin")
    customer_id = make_user(
        email="cust@example.com", password=PASSWORD, phone="03001112223", is_active=0
    )
    _login_as_admin(client, app)

    response = client.post(
        f"/admin/customers/{customer_id}/block",
        data={"action": "unblock"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        db = get_db()
        customer = user_queries.find_by_id(db, customer_id)
        assert customer["is_active"] == 1


def test_customer_panel_shows_orders_count_and_total_spent(app, client, make_user):
    make_user(email="admin@example.com", password=PASSWORD, phone="03000000001", role="admin")
    customer_id = make_user(
        email="cust@example.com", password=PASSWORD, phone="03001112223", full_name="Ali Raza"
    )
    with app.app_context():
        db = get_db()
        service_id = service_queries.create_service(
            db, "Petrol", "Fuel", "litre", Decimal("252.00")
        )
        order_queries.insert_order(
            db,
            customer_id,
            service_id,
            "k1",
            20,
            "5040.00",
            "addr",
            "DHA",
            31.47,
            74.41,
            None,
            call_confirmed=1,
        )
        delivered_id = order_queries.insert_order(
            db,
            customer_id,
            service_id,
            "k2",
            10,
            "2520.00",
            "addr",
            "DHA",
            31.47,
            74.41,
            None,
        )
        order_queries.update_status(db, delivered_id, "Delivered")
        db.commit()
    _login_as_admin(client, app)

    body = client.get(f"/admin/customers/{customer_id}").data.decode()
    assert "Ali Raza" in body
    assert "PKR 2,520" in body  # total spent: only the Delivered order counts
