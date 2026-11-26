"""C12: drivers (docs/SPEC.md screen 18, pop-up 6)."""

from decimal import Decimal

from werkzeug.datastructures import MultiDict

from app import timeutil
from app.areas import AREAS
from app.db import get_db
from app.queries import assignments as assignment_queries
from app.queries import drivers as driver_queries
from app.queries import orders as order_queries
from app.queries import services as service_queries
from app.queries import users as user_queries

PASSWORD = "StrongPass1"  # noqa: S105 (test fixture password, not a secret)
_driver_sequence = iter(range(100_000))


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


def _make_driver(app, name="Driver", status="Available", area="DHA"):
    lat, lng = AREAS[area]
    n = next(_driver_sequence)
    with app.app_context():
        db = get_db()
        driver_id = driver_queries.create_driver(
            db, name, f"0300{n:07d}", f"LEA-{n:04d}", area, status, lat, lng, Decimal("4.5")
        )
        db.commit()
    return driver_id


def _driver_payload(**overrides):
    payload = {
        "name": "New Driver",
        "phone": "0300-5551234",
        "vehicle_no": "lea-9001",
        "area": "DHA",
        "status": "Available",
    }
    payload.update(overrides)
    return payload


def test_customer_gets_403_on_drivers_routes(app, client, make_user):
    driver_id = _make_driver(app)
    user_id = make_user(email="cust@example.com", password=PASSWORD)
    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["role"] = "customer"
        session["session_version"] = 0
    assert client.get("/admin/drivers").status_code == 403
    assert client.post("/admin/drivers", data=_driver_payload()).status_code == 403
    assert client.post(f"/admin/drivers/{driver_id}", data=_driver_payload()).status_code == 403
    assert client.post(f"/admin/drivers/{driver_id}/remove", data={}).status_code == 403


def test_add_driver_rejects_duplicate_phone(app, client, make_user):
    existing_id = _make_driver(app, name="Existing", status="Available")
    with app.app_context():
        db = get_db()
        existing = driver_queries.find_by_id(db, existing_id)
        phone_display = existing["phone"][:4] + "-" + existing["phone"][4:]
    make_user(email="admin@example.com", password=PASSWORD, phone="03000000001", role="admin")
    _login_as_admin(client, app)

    response = client.post("/admin/drivers", data=_driver_payload(phone=phone_display))
    assert response.status_code == 400
    assert "already used" in response.data.decode()


def test_add_driver_rejects_duplicate_vehicle_no(app, client, make_user):
    existing_id = _make_driver(app, name="Existing", status="Available")
    with app.app_context():
        db = get_db()
        vehicle_no = driver_queries.find_by_id(db, existing_id)["vehicle_no"]
    make_user(email="admin@example.com", password=PASSWORD, phone="03000000001", role="admin")
    _login_as_admin(client, app)

    response = client.post("/admin/drivers", data=_driver_payload(vehicle_no=vehicle_no.lower()))
    assert response.status_code == 400
    assert "already used" in response.data.decode()


def test_add_driver_normalises_phone_and_vehicle_no(app, client, make_user):
    make_user(email="admin@example.com", password=PASSWORD, phone="03000000001", role="admin")
    _login_as_admin(client, app)

    response = client.post(
        "/admin/drivers",
        data=_driver_payload(phone="0300-5559999", vehicle_no="lea-9999"),
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        db = get_db()
        driver = driver_queries.find_by_phone(db, "03005559999")
        assert driver is not None
        assert driver["vehicle_no"] == "LEA-9999"


def test_busy_driver_cannot_be_removed(app, client, make_user):
    driver_id = _make_driver(app, name="Busy Driver", status="Busy")
    service_id = None
    with app.app_context():
        db = get_db()
        service_id = service_queries.create_service(
            db, "Petrol", "Fuel", "litre", Decimal("252.00")
        )
        cust_id = user_queries.create_user(
            db, "Cust", "cust2@example.com", "03009998888", "x", "customer"
        )
        order_id = order_queries.insert_order(
            db, cust_id, service_id, "k-busy", 20, "5040.00", "addr", "DHA", 31.47, 74.41, None
        )
        assignment_queries.create_assignment(
            db, order_id, driver_id, 10, timeutil.to_sql(timeutil.utcnow())
        )
        order_queries.update_status(db, order_id, "Assigned")
        db.commit()
    make_user(email="admin@example.com", password=PASSWORD, phone="03000000001", role="admin")
    _login_as_admin(client, app)

    response = client.post(f"/admin/drivers/{driver_id}/remove", data={}, follow_redirects=True)
    assert response.status_code == 200
    assert "active order" in response.data.decode()
    with app.app_context():
        db = get_db()
        assert driver_queries.find_by_id(db, driver_id)["is_active"] == 1


def test_busy_driver_quick_switch_is_disabled(app, client, make_user):
    _make_driver(app, name="Busy Driver", status="Busy")
    make_user(email="admin@example.com", password=PASSWORD, phone="03000000001", role="admin")
    _login_as_admin(client, app)

    body = client.get("/admin/drivers").data.decode()
    assert "disabled" in body


def test_available_switch_triggers_dispatch_pending(app, client, make_user):
    driver_id = _make_driver(app, name="Off Driver", status="Off Duty")
    make_user(email="admin@example.com", password=PASSWORD, phone="03000000001", role="admin")
    cust_id = make_user(email="cust3@example.com", password=PASSWORD, phone="03007778888")
    with app.app_context():
        db = get_db()
        service_id = service_queries.create_service(
            db, "Petrol", "Fuel", "litre", Decimal("252.00")
        )
        order_id = order_queries.insert_order(
            db, cust_id, service_id, "k-waiting", 20, "5040.00", "addr", "DHA", 31.47, 74.41, None
        )
        db.commit()
    _login_as_admin(client, app)

    data = MultiDict(
        [
            ("name", "Off Driver"),
            ("phone", "0300-0000000"),
            ("vehicle_no", "LEA-0000"),
            ("area", "DHA"),
            ("status", "Off Duty"),
            ("status", "Available"),
        ]
    )
    with app.app_context():
        db = get_db()
        phone = driver_queries.find_by_id(db, driver_id)["phone"]
        vehicle_no = driver_queries.find_by_id(db, driver_id)["vehicle_no"]
    data["phone"] = f"{phone[:4]}-{phone[4:]}"
    data["vehicle_no"] = vehicle_no

    response = client.post(f"/admin/drivers/{driver_id}", data=data, follow_redirects=True)
    assert response.status_code == 200

    with app.app_context():
        db = get_db()
        driver = driver_queries.find_by_id(db, driver_id)
        order = order_queries.find_by_id(db, order_id)
        assert driver["status"] == "Busy"
        assert order["status"] == "Assigned"
        assert order["driver_id"] == driver_id


def test_removed_driver_never_dispatched(app, client, make_user):
    driver_id = _make_driver(app, name="Solo Driver", status="Available")
    make_user(email="admin@example.com", password=PASSWORD, phone="03000000001", role="admin")
    _login_as_admin(client, app)

    response = client.post(f"/admin/drivers/{driver_id}/remove", data={}, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        db = get_db()
        driver = driver_queries.find_by_id(db, driver_id)
        assert driver["is_active"] == 0
        available = driver_queries.list_available(db)
        assert all(row["driver_id"] != driver_id for row in available)

    body = client.get("/admin/drivers").data.decode()
    assert "Solo Driver" not in body
