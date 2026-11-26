"""C11: emergency requests (docs/SPEC.md screen 15)."""

from datetime import timedelta
from decimal import Decimal

from app import timeutil
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


def _make_emergency(app, service_id, user_id, key, minutes_ago):
    with app.app_context():
        db = get_db()
        created_at = timeutil.to_sql(timeutil.utcnow() - timedelta(minutes=minutes_ago))
        order_id = order_queries.insert_order(
            db,
            user_id,
            service_id,
            key,
            5,
            "1260.00",
            "Roadside",
            "Gulberg",
            31.52,
            74.35,
            None,
            is_emergency=1,
        )
        db.execute("UPDATE orders SET created_at = ? WHERE order_id = ?", (created_at, order_id))
        db.commit()
    return order_id


def test_customer_gets_403_on_emergency_route(app, client, make_user):
    user_id = make_user(email="cust@example.com", password=PASSWORD)
    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["role"] = "customer"
        session["session_version"] = 0
    assert client.get("/admin/emergency").status_code == 403


def test_empty_state_shown_when_no_open_emergencies(app, client, make_user):
    make_user(email="admin@example.com", password=PASSWORD, phone="03000000001", role="admin")
    _login_as_admin(client, app)
    body = client.get("/admin/emergency").data.decode()
    assert "No open emergencies" in body
    assert "Updates every 15 seconds" in body


def test_overdue_request_moves_to_top_and_is_marked(app, client, make_user):
    service_id = _seed_petrol(app)
    make_user(email="admin@example.com", password=PASSWORD, phone="03000000001", role="admin")
    cust_id = make_user(email="cust@example.com", password=PASSWORD)
    recent_id = _make_emergency(app, service_id, cust_id, "k-recent", minutes_ago=2)
    old_id = _make_emergency(app, service_id, cust_id, "k-old", minutes_ago=8)
    _login_as_admin(client, app)

    body = client.get("/admin/emergency").data.decode()
    old_number = f"ORD-{old_id:04d}"
    recent_number = f"ORD-{recent_id:04d}"
    assert body.index(old_number) < body.index(recent_number)
    # "open" is an adjective here, never pluralised ("2 opens" would be wrong).
    assert "2 open · oldest waiting 8 min" in body
    assert "Waiting over 5 min" in body


def test_oldest_first_when_none_overdue(app, client, make_user):
    service_id = _seed_petrol(app)
    make_user(email="admin@example.com", password=PASSWORD, phone="03000000001", role="admin")
    cust_id = make_user(email="cust@example.com", password=PASSWORD)
    newer_id = _make_emergency(app, service_id, cust_id, "k-newer", minutes_ago=1)
    older_id = _make_emergency(app, service_id, cust_id, "k-older", minutes_ago=3)
    _login_as_admin(client, app)

    body = client.get("/admin/emergency").data.decode()
    assert body.index(f"ORD-{older_id:04d}") < body.index(f"ORD-{newer_id:04d}")


def test_assign_driver_link_opens_order_detail_with_assign_dialog(app, client, make_user):
    service_id = _seed_petrol(app)
    make_user(email="admin@example.com", password=PASSWORD, phone="03000000001", role="admin")
    cust_id = make_user(email="cust@example.com", password=PASSWORD)
    order_id = _make_emergency(app, service_id, cust_id, "k1", minutes_ago=1)
    _login_as_admin(client, app)

    body = client.get("/admin/emergency").data.decode()
    assert f"/admin/orders/{order_id}?open=assign" in body

    detail_body = client.get(f"/admin/orders/{order_id}?open=assign").data.decode()
    assert 'data-open-dialog="dialog-assign"' in detail_body
