"""C10: order details, assign driver, status moves (docs/SPEC.md screen 14,
pop-ups 2-3)."""

import re
from decimal import Decimal

from app import timeutil
from app.areas import AREAS
from app.db import get_db
from app.queries import assignments as assignment_queries
from app.queries import drivers as driver_queries
from app.queries import orders as order_queries
from app.queries import services as service_queries
from app.queries import tracking as tracking_queries
from app.queries import users as user_queries

PASSWORD = "StrongPass1"  # noqa: S105 (test fixture password, not a secret)
_driver_sequence = iter(range(100_000))


def _seed_petrol(app):
    with app.app_context():
        db = get_db()
        service_id = service_queries.create_service(
            db, "Petrol", "Fuel", "litre", Decimal("252.00")
        )
        db.commit()
        return service_id


def _make_driver(db, name="Driver", status="Available", area="DHA"):
    lat, lng = AREAS[area]
    n = next(_driver_sequence)
    return driver_queries.create_driver(
        db, name, f"0300{n:07d}", f"LEA-{n:04d}", area, status, lat, lng, Decimal("4.5")
    )


def _make_order(db, user_id, service_id, order_key, **overrides):
    lat, lng = AREAS["DHA"]
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
        "latitude": lat,
        "longitude": lng,
        "created_at": timeutil.to_sql(timeutil.utcnow()),
    }
    fields.update(overrides)
    order_id = order_queries.insert_seed_order(db, **fields)
    tracking_queries.add_tracking(
        db, order_id, "Pending", fields["created_at"], fields["latitude"], fields["longitude"]
    )
    return order_id


def _assign(db, order_id, driver_id, eta=10, distance=Decimal("1.00")):
    now_sql = timeutil.to_sql(timeutil.utcnow())
    assignment_queries.create_assignment(
        db, order_id, driver_id, eta, now_sql, distance_km=distance
    )
    order_queries.update_status(db, order_id, "Assigned")
    driver_queries.set_status(db, driver_id, "Busy")
    tracking_queries.add_tracking(db, order_id, "Assigned", now_sql, *AREAS["DHA"])


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


def _stale_token(client, order_id):
    body = client.get(f"/admin/orders/{order_id}").data.decode()
    match = re.search(r'name="stale_token" value="(\d+)"', body)
    return match.group(1)


def test_order_detail_404_for_missing_order(app, client, make_user):
    make_user(email="admin@example.com", password=PASSWORD, phone="03000000001", role="admin")
    _login_as_admin(client, app)
    assert client.get("/admin/orders/999999").status_code == 404


def test_customer_gets_403_on_every_new_route(app, client, make_user):
    service_id = _seed_petrol(app)
    user_id = make_user(email="cust@example.com", password=PASSWORD)
    with app.app_context():
        db = get_db()
        order_id = _make_order(db, user_id, service_id, "k1")
        db.commit()

    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["role"] = "customer"
        session["session_version"] = 0

    assert client.get(f"/admin/orders/{order_id}").status_code == 403
    assert client.post(f"/admin/orders/{order_id}/assign", data={}).status_code == 403
    assert client.post(f"/admin/orders/{order_id}/status", data={}).status_code == 403
    assert client.post(f"/admin/orders/{order_id}/call-done", data={}).status_code == 403


def test_assign_picks_the_nearest_driver(app, client, make_user):
    service_id = _seed_petrol(app)
    make_user(email="admin@example.com", password=PASSWORD, phone="03000000001", role="admin")
    user_id = make_user(email="cust@example.com", password=PASSWORD)
    with app.app_context():
        db = get_db()
        far_driver = _make_driver(db, "Far Driver", area="Bahria Town")
        near_driver = _make_driver(db, "Near Driver", area="DHA")
        order_id = _make_order(db, user_id, service_id, "k1")
        db.commit()

    _login_as_admin(client, app)
    body = client.get(f"/admin/orders/{order_id}").data.decode()
    assert body.index("Near Driver") < body.index("Far Driver")
    assert "Recommended" in body

    token = _stale_token(client, order_id)
    response = client.post(
        f"/admin/orders/{order_id}/assign",
        data={"driver_id": near_driver, "stale_token": token},
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        db = get_db()
        order = order_queries.find_by_id(db, order_id)
        assert order["status"] == "Assigned"
        assert order["driver_id"] == near_driver
        driver = driver_queries.find_by_id(db, near_driver)
        assert driver["status"] == "Busy"
        far = driver_queries.find_by_id(db, far_driver)
        assert far["status"] == "Available"


def test_change_driver_frees_the_old_one(app, client, make_user):
    service_id = _seed_petrol(app)
    make_user(email="admin@example.com", password=PASSWORD, phone="03000000001", role="admin")
    user_id = make_user(email="cust@example.com", password=PASSWORD)
    with app.app_context():
        db = get_db()
        old_driver = _make_driver(db, "Old Driver", status="Busy")
        new_driver = _make_driver(db, "New Driver")
        order_id = _make_order(db, user_id, service_id, "k1", status="Assigned")
        _assign(db, order_id, old_driver)
        db.commit()

    _login_as_admin(client, app)
    token = _stale_token(client, order_id)
    response = client.post(
        f"/admin/orders/{order_id}/assign",
        data={"driver_id": new_driver, "stale_token": token},
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        db = get_db()
        order = order_queries.find_by_id(db, order_id)
        assert order["driver_id"] == new_driver
        assert driver_queries.find_by_id(db, old_driver)["status"] == "Available"
        assert driver_queries.find_by_id(db, new_driver)["status"] == "Busy"


def test_assign_refused_when_driver_is_no_longer_free(app, client, make_user):
    service_id = _seed_petrol(app)
    make_user(email="admin@example.com", password=PASSWORD, phone="03000000001", role="admin")
    user_id = make_user(email="cust@example.com", password=PASSWORD)
    with app.app_context():
        db = get_db()
        busy_driver = _make_driver(db, "Busy Driver", status="Busy")
        order_id = _make_order(db, user_id, service_id, "k1")
        db.commit()

    _login_as_admin(client, app)
    token = _stale_token(client, order_id)
    response = client.post(
        f"/admin/orders/{order_id}/assign",
        data={"driver_id": busy_driver, "stale_token": token},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "no longer free" in response.data.decode()
    with app.app_context():
        db = get_db()
        assert order_queries.find_by_id(db, order_id)["status"] == "Pending"


def test_assign_refused_while_call_is_not_confirmed(app, client, make_user):
    service_id = _seed_petrol(app)
    make_user(email="admin@example.com", password=PASSWORD, phone="03000000001", role="admin")
    user_id = make_user(email="cust@example.com", password=PASSWORD)
    with app.app_context():
        db = get_db()
        driver_id = _make_driver(db)
        order_id = _make_order(db, user_id, service_id, "k1", call_confirmed=0)
        db.commit()

    _login_as_admin(client, app)
    token = _stale_token(client, order_id)
    response = client.post(
        f"/admin/orders/{order_id}/assign",
        data={"driver_id": driver_id, "stale_token": token},
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        db = get_db()
        assert order_queries.find_by_id(db, order_id)["status"] == "Pending"


def test_mark_on_the_way_then_delivered_frees_driver_and_moves_it_to_customer(
    app, client, make_user
):
    service_id = _seed_petrol(app)
    make_user(email="admin@example.com", password=PASSWORD, phone="03000000001", role="admin")
    user_id = make_user(email="cust@example.com", password=PASSWORD)
    customer_lat, customer_lng = AREAS["Gulberg"]
    with app.app_context():
        db = get_db()
        driver_id = _make_driver(db, "Driver", area="DHA", status="Busy")
        order_id = _make_order(
            db,
            user_id,
            service_id,
            "k1",
            status="Assigned",
            latitude=customer_lat,
            longitude=customer_lng,
            area="Gulberg",
        )
        _assign(db, order_id, driver_id)
        db.commit()

    _login_as_admin(client, app)

    token = _stale_token(client, order_id)
    response = client.post(
        f"/admin/orders/{order_id}/status",
        data={"new_status": "On the Way", "stale_token": token},
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        db = get_db()
        assert order_queries.find_by_id(db, order_id)["status"] == "On the Way"

    token = _stale_token(client, order_id)
    response = client.post(
        f"/admin/orders/{order_id}/status",
        data={"new_status": "Delivered", "stale_token": token},
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        db = get_db()
        order = order_queries.find_by_id(db, order_id)
        assert order["status"] == "Delivered"
        driver = driver_queries.find_by_id(db, driver_id)
        assert driver["status"] == "Available"
        assert float(driver["latitude"]) == customer_lat
        assert float(driver["longitude"]) == customer_lng


def test_delivered_triggers_dispatch_pending_for_a_waiting_order(app, client, make_user):
    service_id = _seed_petrol(app)
    make_user(email="admin@example.com", password=PASSWORD, phone="03000000001", role="admin")
    user_id = make_user(email="cust@example.com", password=PASSWORD)
    with app.app_context():
        db = get_db()
        driver_id = _make_driver(db, "Driver", status="Busy")
        delivering_order = _make_order(db, user_id, service_id, "k1", status="On the Way")
        _assign(db, delivering_order, driver_id)
        order_queries.update_status(db, delivering_order, "On the Way")
        waiting_order = _make_order(db, user_id, service_id, "k2")
        db.commit()

    _login_as_admin(client, app)
    token = _stale_token(client, delivering_order)
    client.post(
        f"/admin/orders/{delivering_order}/status",
        data={"new_status": "Delivered", "stale_token": token},
        follow_redirects=True,
    )
    with app.app_context():
        db = get_db()
        waiting = order_queries.find_by_id(db, waiting_order)
        assert waiting["status"] == "Assigned"
        assert waiting["driver_id"] == driver_id


def test_back_to_pending_deletes_assignment_and_frees_driver(app, client, make_user):
    """Scheduled, not ASAP, so dispatch_pending (run because the driver was
    freed) does not immediately re-grab this same order and mask the result."""
    service_id = _seed_petrol(app)
    make_user(email="admin@example.com", password=PASSWORD, phone="03000000001", role="admin")
    user_id = make_user(email="cust@example.com", password=PASSWORD)
    with app.app_context():
        db = get_db()
        driver_id = _make_driver(db, "Driver", status="Busy")
        order_id = _make_order(
            db,
            user_id,
            service_id,
            "k1",
            status="Assigned",
            scheduled_at="2026-12-01 10:00:00",
        )
        _assign(db, order_id, driver_id)
        db.commit()

    _login_as_admin(client, app)
    token = _stale_token(client, order_id)
    response = client.post(
        f"/admin/orders/{order_id}/status",
        data={"new_status": "Pending", "stale_token": token},
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        db = get_db()
        order = order_queries.find_by_id(db, order_id)
        assert order["status"] == "Pending"
        assert order["driver_id"] is None
        assert assignment_queries.find_by_order_id(db, order_id) is None
        assert driver_queries.find_by_id(db, driver_id)["status"] == "Available"


def test_illegal_move_pending_to_delivered_is_refused(app, client, make_user):
    service_id = _seed_petrol(app)
    make_user(email="admin@example.com", password=PASSWORD, phone="03000000001", role="admin")
    user_id = make_user(email="cust@example.com", password=PASSWORD)
    with app.app_context():
        db = get_db()
        order_id = _make_order(db, user_id, service_id, "k1")
        db.commit()

    _login_as_admin(client, app)
    token = _stale_token(client, order_id)
    response = client.post(
        f"/admin/orders/{order_id}/status",
        data={"new_status": "Delivered", "stale_token": token},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "not allowed" in response.data.decode()
    with app.app_context():
        db = get_db()
        assert order_queries.find_by_id(db, order_id)["status"] == "Pending"


def test_illegal_move_on_a_finished_order_is_refused(app, client, make_user):
    service_id = _seed_petrol(app)
    make_user(email="admin@example.com", password=PASSWORD, phone="03000000001", role="admin")
    user_id = make_user(email="cust@example.com", password=PASSWORD)
    with app.app_context():
        db = get_db()
        order_id = _make_order(db, user_id, service_id, "k1", status="Delivered")
        db.commit()
        # Delivered has no moves, so no form on the page carries a stale
        # token - read it straight from the DB, as a hand-crafted POST would.
        token = tracking_queries.latest_id_for_order(db, order_id)

    _login_as_admin(client, app)
    response = client.post(
        f"/admin/orders/{order_id}/status",
        data={"new_status": "On the Way", "stale_token": token},
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        db = get_db()
        assert order_queries.find_by_id(db, order_id)["status"] == "Delivered"


def test_cancel_requires_a_reason(app, client, make_user):
    service_id = _seed_petrol(app)
    make_user(email="admin@example.com", password=PASSWORD, phone="03000000001", role="admin")
    user_id = make_user(email="cust@example.com", password=PASSWORD)
    with app.app_context():
        db = get_db()
        order_id = _make_order(db, user_id, service_id, "k1")
        db.commit()

    _login_as_admin(client, app)
    token = _stale_token(client, order_id)
    response = client.post(
        f"/admin/orders/{order_id}/status",
        data={"new_status": "Cancelled", "stale_token": token},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "Choose a reason" in response.data.decode()
    with app.app_context():
        db = get_db()
        assert order_queries.find_by_id(db, order_id)["status"] == "Pending"


def test_cancel_other_reason_requires_typed_text(app, client, make_user):
    service_id = _seed_petrol(app)
    make_user(email="admin@example.com", password=PASSWORD, phone="03000000001", role="admin")
    user_id = make_user(email="cust@example.com", password=PASSWORD)
    with app.app_context():
        db = get_db()
        order_id = _make_order(db, user_id, service_id, "k1")
        db.commit()

    _login_as_admin(client, app)
    token = _stale_token(client, order_id)
    response = client.post(
        f"/admin/orders/{order_id}/status",
        data={"new_status": "Cancelled", "cancel_reason": "Other", "stale_token": token},
        follow_redirects=True,
    )
    assert "Type the reason" in response.data.decode()

    token = _stale_token(client, order_id)
    response = client.post(
        f"/admin/orders/{order_id}/status",
        data={
            "new_status": "Cancelled",
            "cancel_reason": "Other",
            "cancel_reason_other": "Shop closed early",
            "stale_token": token,
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        db = get_db()
        order = order_queries.find_by_id(db, order_id)
        assert order["status"] == "Cancelled"
        assert order["cancel_reason"] == "Shop closed early"


def test_cancel_frees_the_driver(app, client, make_user):
    service_id = _seed_petrol(app)
    make_user(email="admin@example.com", password=PASSWORD, phone="03000000001", role="admin")
    user_id = make_user(email="cust@example.com", password=PASSWORD)
    with app.app_context():
        db = get_db()
        driver_id = _make_driver(db, "Driver", status="Busy")
        order_id = _make_order(db, user_id, service_id, "k1", status="Assigned")
        _assign(db, order_id, driver_id)
        db.commit()

    _login_as_admin(client, app)
    token = _stale_token(client, order_id)
    response = client.post(
        f"/admin/orders/{order_id}/status",
        data={"new_status": "Cancelled", "cancel_reason": "Customer asked", "stale_token": token},
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        db = get_db()
        order = order_queries.find_by_id(db, order_id)
        assert order["status"] == "Cancelled"
        assert order["cancel_reason"] == "Customer asked"
        assert driver_queries.find_by_id(db, driver_id)["status"] == "Available"


def test_stale_update_is_refused(app, client, make_user):
    service_id = _seed_petrol(app)
    make_user(email="admin@example.com", password=PASSWORD, phone="03000000001", role="admin")
    user_id = make_user(email="cust@example.com", password=PASSWORD)
    with app.app_context():
        db = get_db()
        driver_id = _make_driver(db, "Driver", status="Busy")
        order_id = _make_order(db, user_id, service_id, "k1", status="Assigned")
        _assign(db, order_id, driver_id)
        db.commit()

    _login_as_admin(client, app)
    response = client.post(
        f"/admin/orders/{order_id}/status",
        data={"new_status": "On the Way", "stale_token": "999999"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "updated by someone else" in response.data.decode()
    with app.app_context():
        db = get_db()
        assert order_queries.find_by_id(db, order_id)["status"] == "Assigned"


def test_call_done_dispatches_an_asap_order(app, client, make_user):
    service_id = _seed_petrol(app)
    make_user(email="admin@example.com", password=PASSWORD, phone="03000000001", role="admin")
    user_id = make_user(email="cust@example.com", password=PASSWORD)
    with app.app_context():
        db = get_db()
        driver_id = _make_driver(db, "Driver")
        order_id = _make_order(
            db, user_id, service_id, "k1", quantity=250, call_confirmed=0, note="Generator"
        )
        db.commit()

    _login_as_admin(client, app)
    token = _stale_token(client, order_id)
    response = client.post(
        f"/admin/orders/{order_id}/call-done",
        data={"stale_token": token},
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        db = get_db()
        order = order_queries.find_by_id(db, order_id)
        assert order["call_confirmed"] == 1
        assert order["status"] == "Assigned"
        assert order["driver_id"] == driver_id
        assert driver_queries.find_by_id(db, driver_id)["status"] == "Busy"


def test_call_done_refused_when_already_confirmed(app, client, make_user):
    service_id = _seed_petrol(app)
    make_user(email="admin@example.com", password=PASSWORD, phone="03000000001", role="admin")
    user_id = make_user(email="cust@example.com", password=PASSWORD)
    with app.app_context():
        db = get_db()
        order_id = _make_order(db, user_id, service_id, "k1")
        db.commit()

    _login_as_admin(client, app)
    token = _stale_token(client, order_id)
    response = client.post(
        f"/admin/orders/{order_id}/call-done",
        data={"stale_token": token},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "already marked done" in response.data.decode()
