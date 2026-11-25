import time
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from app import dispatch
from app.areas import AREAS, area_centre
from app.db import get_db
from app.queries import drivers as driver_queries
from app.queries import orders as order_queries
from app.queries import services as service_queries

KARACHI = ZoneInfo("Asia/Karachi")


def _karachi(hour):
    return datetime(2026, 6, 15, hour, 0, 0, tzinfo=KARACHI)


_driver_sequence = iter(range(100_000))


def _make_driver(db, name="Driver", status="Available", area="DHA", is_active=1, phone=None):
    lat, lng = AREAS[area]
    # A counter, not hash(name), for uniqueness: Python's string hash is
    # randomized per process, so a run of 50+ drivers could collide by chance.
    n = next(_driver_sequence)
    phone = phone or f"0300{n:07d}"
    vehicle_no = f"LEA-{n:04d}"
    return driver_queries.create_driver(
        db, name, phone, vehicle_no, area, status, lat, lng, Decimal("4.5"), is_active
    )


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


def _seed_petrol(app):
    with app.app_context():
        db = get_db()
        service_id = service_queries.create_service(
            db, "Petrol", "Fuel", "litre", Decimal("252.00")
        )
        db.commit()
        return service_id


def test_haversine_one_degree_latitude_is_about_111_km():
    distance = dispatch.haversine_km(0, 0, 1, 0)
    assert distance == pytest.approx(111.19, abs=0.05)


def test_haversine_known_lahore_points():
    dha_lat, dha_lon = AREAS["DHA"]
    gulberg_lat, gulberg_lon = AREAS["Gulberg"]
    distance = dispatch.haversine_km(dha_lat, dha_lon, gulberg_lat, gulberg_lon)
    assert 3 < distance < 12


def test_eta_example_6km_at_30kmh_is_17_minutes():
    assert dispatch.eta_minutes(6, _karachi(12)) == 17


def test_speed_bands_including_midnight_edges():
    expected = {
        6: 30,
        7: 20,
        9: 20,
        10: 30,
        16: 30,
        17: 20,
        19: 20,
        20: 30,
        21: 30,
        22: 40,
        23: 40,
        0: 40,
        5: 40,
    }
    for hour, speed in expected.items():
        assert dispatch.speed_kmh(_karachi(hour)) == speed, f"hour {hour}"


def test_emergency_beats_an_older_normal_order(app, make_user):
    service_id = _seed_petrol(app)
    user_id = make_user()
    with app.app_context():
        db = get_db()
        _make_driver(db, "Solo Driver")
        older_normal = _make_order(
            db, user_id, service_id, "key-normal", created_at="2026-06-15 06:00:00"
        )
        newer_emergency = _make_order(
            db,
            user_id,
            service_id,
            "key-emergency",
            is_emergency=1,
            created_at="2026-06-15 08:00:00",
        )
        db.commit()
        assigned = dispatch.dispatch_pending(db, now=_karachi(12))
        older = order_queries.find_by_id_for_user(db, older_normal, user_id)
        newer = order_queries.find_by_id_for_user(db, newer_emergency, user_id)
    assert assigned == [newer_emergency]
    assert newer["status"] == "Assigned"
    assert older["status"] == "Pending"


def test_busy_off_duty_and_removed_drivers_are_ignored(app, make_user):
    service_id = _seed_petrol(app)
    user_id = make_user()
    with app.app_context():
        db = get_db()
        _make_driver(db, "Busy Driver", status="Busy")
        _make_driver(db, "Off Duty Driver", status="Off Duty")
        _make_driver(db, "Removed Driver", status="Available", is_active=0)
        order_id = _make_order(db, user_id, service_id, "key-ignored")
        db.commit()
        order_row = dict(order_queries.find_by_id_for_user(db, order_id, user_id))
        result = dispatch.dispatch_order(db, order_row, now=_karachi(12))
    assert result is None


def test_area_fallback_when_customer_location_missing(app, make_user):
    service_id = _seed_petrol(app)
    user_id = make_user()
    with app.app_context():
        db = get_db()
        _make_driver(db, "Gulberg Driver", area="Gulberg")
        order_id = _make_order(
            db,
            user_id,
            service_id,
            "key-area-fallback",
            latitude=None,
            longitude=None,
            area="Johar Town",
        )
        db.commit()
        order_row = dict(order_queries.find_by_id_for_user(db, order_id, user_id))
        result = dispatch.dispatch_order(db, order_row, now=_karachi(12))
    johar_lat, johar_lon = area_centre("Johar Town")
    gulberg_lat, gulberg_lon = AREAS["Gulberg"]
    expected_distance = dispatch.haversine_km(johar_lat, johar_lon, gulberg_lat, gulberg_lon)
    assert result is not None
    assert float(result["distance_km"]) == pytest.approx(expected_distance, abs=0.01)


def test_no_free_driver_leaves_order_pending(app, make_user):
    service_id = _seed_petrol(app)
    user_id = make_user()
    with app.app_context():
        db = get_db()
        order_id = _make_order(db, user_id, service_id, "key-no-drivers")
        db.commit()
        order_row = dict(order_queries.find_by_id_for_user(db, order_id, user_id))
        result = dispatch.dispatch_order(db, order_row, now=_karachi(12))
        order = order_queries.find_by_id_for_user(db, order_id, user_id)
    assert result is None
    assert order["status"] == "Pending"


def test_scheduled_and_above_200_litre_orders_stay_pending(app, make_user):
    service_id = _seed_petrol(app)
    user_id = make_user()
    with app.app_context():
        db = get_db()
        _make_driver(db, "Available Driver")
        _make_order(
            db,
            user_id,
            service_id,
            "key-scheduled",
            scheduled_at="2026-06-20 10:00:00",
        )
        _make_order(db, user_id, service_id, "key-call-needed", call_confirmed=0)
        db.commit()
        waiting = order_queries.list_pending_asap(db)
    assert waiting == []


def test_dispatch_of_50_drivers_is_fast(app, make_user):
    service_id = _seed_petrol(app)
    user_id = make_user()
    with app.app_context():
        db = get_db()
        for i in range(50):
            _make_driver(db, f"Driver {i}", area=list(AREAS)[i % len(AREAS)])
        order_id = _make_order(db, user_id, service_id, "key-perf")
        db.commit()
        order_row = dict(order_queries.find_by_id_for_user(db, order_id, user_id))
        started = time.perf_counter()
        result = dispatch.dispatch_order(db, order_row, now=_karachi(12))
        elapsed = time.perf_counter() - started
    assert result is not None
    assert elapsed < 1.0


def pytest_approx(value, abs):
    import pytest

    return pytest.approx(value, abs=abs)
