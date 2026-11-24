"""Deterministic demo data: fixed random seed, exact records from docs/FIGMA.md,
about 300 past orders over 30 days. Pure data generation; all SQL stays in
app/queries/*.py."""

import random
from datetime import UTC, datetime, timedelta

from werkzeug.security import generate_password_hash

from app.areas import AREAS, area_names
from app.queries import drivers as driver_queries
from app.queries import orders as order_queries
from app.queries import services as service_queries
from app.queries import tracking as tracking_queries
from app.queries import users as user_queries

RANDOM_SEED = 20261124
TOTAL_ORDERS = 300
ALI_FILLER_ORDERS = 21  # + the 2 exact orders below = 23 total for Ali Raza

SERVICES = [
    ("Petrol", "Fuel", "litre", 25200),
    ("Diesel", "Fuel", "litre", 25800),
    ("Generator fuel", "Fuel", "litre", 25800),
    ("Engine oil delivery", "Assistance", "service", 280000),
    ("Battery help", "Assistance", "service", 150000),
    ("Tyre help", "Assistance", "service", 60000),
    ("Car wash", "Assistance", "service", 100000),
]
FILLER_SERVICE_NAMES = [
    "Petrol",
    "Diesel",
    "Engine oil delivery",
    "Battery help",
    "Tyre help",
    "Car wash",
]

DRIVERS = [
    ("Ahmed Raza", "03001112201", "LEA-1234", "DHA", "Busy", 4.8),
    ("Bilal Ahmed", "03001112202", "LEA-5521", "Gulberg", "Available", 4.6),
    ("Usman Ali", "03001112203", "LEA-7712", "Johar Town", "Available", 4.7),
    ("Kashif Iqbal", "03001112204", "LEA-3390", "Model Town", "Available", 4.5),
    ("Faisal Mehmood", "03001112205", "LEA-8843", "Township", "Available", 4.9),
    ("Naveed Akhtar", "03001112206", "LEA-2201", "Iqbal Town", "Available", 4.6),
    ("Shahid Butt", "03001112207", "LEA-4456", "Wapda Town", "Available", 4.7),
    ("Tariq Javed", "03001112208", "LEA-6678", "Cantt", "Available", 4.8),
    ("Adnan Raza", "03001112209", "LEA-9012", "Shahdara", "Off duty", 4.5),
]

FIRST_NAMES = [
    "Ahmed",
    "Ayesha",
    "Bilal",
    "Fatima",
    "Hamza",
    "Hira",
    "Imran",
    "Javeria",
    "Kamran",
    "Lubna",
    "Mohsin",
    "Nadia",
    "Omar",
    "Rabia",
    "Saad",
    "Sana",
    "Tahir",
    "Umair",
    "Waleed",
    "Zainab",
]
LAST_NAMES = [
    "Ahmed",
    "Akhtar",
    "Butt",
    "Chaudhry",
    "Hussain",
    "Iqbal",
    "Khan",
    "Malik",
    "Mehmood",
    "Mirza",
    "Qureshi",
    "Raza",
    "Sheikh",
    "Siddiqui",
]
CANCEL_REASONS = [
    "Customer asked",
    "No driver available",
    "Wrong address",
    "Duplicate order",
]


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _seed_services(db):
    return {
        name: service_queries.create_service(db, name, category, unit, price)
        for name, category, unit, price in SERVICES
    }


def _seed_drivers(db):
    driver_ids = []
    for name, phone, vehicle, area, status, rating in DRIVERS:
        lat, lng = AREAS[area]
        driver_ids.append(
            driver_queries.create_driver(db, name, phone, vehicle, area, status, lat, lng, rating)
        )
    return driver_ids


def _seed_customers(db, rng, password_hash):
    ali_id = user_queries.create_user(
        db, "Ali Raza", "ali.raza@example.com", "03001234567", password_hash, "customer"
    )
    sana_id = user_queries.create_user(
        db, "Sana Iqbal", "sana.iqbal@example.com", "03002345678", password_hash, "customer"
    )
    bilal_id = user_queries.create_user(
        db, "Bilal Khan", "bilal.khan@example.com", "03003456789", password_hash, "customer"
    )
    other_ids = []
    for i in range(47):
        full_name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
        email = f"customer{i + 1}@example.com"
        phone = f"0300{2000000 + i:07d}"
        other_ids.append(
            user_queries.create_user(db, full_name, email, phone, password_hash, "customer")
        )
    return ali_id, sana_id, bilal_id, other_ids


def _insert_ali_petrol_order(db, ali_id, petrol_service_id, driver_id, now):
    created_at = now - timedelta(hours=2, minutes=10)
    assigned_at = now - timedelta(hours=2)
    on_way_at = now - timedelta(hours=1, minutes=50)
    lat, lng = AREAS["DHA"]
    order_id = order_queries.insert_seed_order(
        db,
        user_id=ali_id,
        service_id=petrol_service_id,
        driver_id=driver_id,
        order_key="seed-ord-0042",
        status="On the way",
        is_emergency=0,
        call_confirmed=1,
        quantity=20,
        unit_price_paisa=25200,
        total_paisa=504000,
        address="House 12, Street 4, Phase 3",
        area="DHA",
        lat=lat,
        lng=lng,
        delivery_time="asap",
        created_at=_iso(created_at),
        assigned_at=_iso(assigned_at),
    )
    tracking_queries.add_tracking(db, order_id, "Pending", _iso(created_at))
    tracking_queries.add_tracking(db, order_id, "Assigned", _iso(assigned_at))
    tracking_queries.add_tracking(db, order_id, "On the way", _iso(on_way_at))


def _insert_ali_generator_order(db, ali_id, generator_service_id, now):
    created_at = now - timedelta(minutes=30)
    lat, lng = AREAS["Township"]
    order_id = order_queries.insert_seed_order(
        db,
        user_id=ali_id,
        service_id=generator_service_id,
        driver_id=None,
        order_key="seed-ord-0043",
        status="Pending",
        is_emergency=0,
        call_confirmed=0,
        quantity=250,
        unit_price_paisa=25800,
        total_paisa=6450000,
        address="Shop 5, Industrial Estate",
        area="Township",
        lat=lat,
        lng=lng,
        delivery_time="asap",
        created_at=_iso(created_at),
    )
    tracking_queries.add_tracking(db, order_id, "Pending", _iso(created_at))


def _insert_emergency_order(db, customer_id, petrol_service_id, now, minutes_ago, quantity, note):
    created_at = now - timedelta(minutes=minutes_ago)
    area = "Gulberg"
    lat, lng = AREAS[area]
    order_id = order_queries.insert_seed_order(
        db,
        user_id=customer_id,
        service_id=petrol_service_id,
        driver_id=None,
        order_key=f"seed-emergency-{customer_id}",
        status="Pending",
        is_emergency=1,
        call_confirmed=1,
        quantity=quantity,
        unit_price_paisa=25200,
        total_paisa=quantity * 25200,
        address="Roadside",
        area=area,
        lat=lat,
        lng=lng,
        note=note,
        delivery_time="asap",
        created_at=_iso(created_at),
    )
    tracking_queries.add_tracking(db, order_id, "Pending", _iso(created_at))


def _insert_filler_order(db, rng, user_id, service_ids, driver_ids, now):
    service_name = rng.choice(FILLER_SERVICE_NAMES)
    name, _category, unit, price = next(s for s in SERVICES if s[0] == service_name)
    quantity = rng.choice([10, 20, 30, 50, 80, 100]) if unit == "litre" else 1
    total = quantity * price if unit == "litre" else price
    created_at = now - timedelta(
        days=rng.randint(0, 29), hours=rng.randint(0, 23), minutes=rng.randint(0, 59)
    )
    status = rng.choices(
        ["Delivered", "Cancelled", "On the way", "Assigned", "Pending"],
        weights=[80, 10, 4, 3, 3],
    )[0]
    area = rng.choice(area_names())
    lat, lng = AREAS[area]

    driver_id, assigned_at, delivered_at, cancel_reason, cancelled_at = (
        None,
        None,
        None,
        None,
        None,
    )
    if status in ("Assigned", "On the way", "Delivered"):
        driver_id = rng.choice(driver_ids)
        assigned_at = created_at + timedelta(minutes=rng.randint(2, 15))
    if status == "Delivered":
        delivered_at = assigned_at + timedelta(minutes=rng.randint(15, 60))
    if status == "Cancelled":
        cancel_reason = rng.choice(CANCEL_REASONS)
        cancelled_at = created_at + timedelta(minutes=rng.randint(5, 120))

    order_id = order_queries.insert_seed_order(
        db,
        user_id=user_id,
        service_id=service_ids[name],
        driver_id=driver_id,
        order_key=f"seed-filler-{rng.random():.17f}",
        status=status,
        is_emergency=0,
        call_confirmed=1,
        quantity=quantity,
        unit_price_paisa=price,
        total_paisa=total,
        address=f"House {rng.randint(1, 200)}, {area}",
        area=area,
        lat=lat,
        lng=lng,
        delivery_time="asap",
        cancel_reason=cancel_reason,
        created_at=_iso(created_at),
        assigned_at=_iso(assigned_at) if assigned_at else None,
        delivered_at=_iso(delivered_at) if delivered_at else None,
    )
    _add_filler_tracking(
        db, order_id, status, created_at, assigned_at, delivered_at, cancel_reason, cancelled_at
    )


def _add_filler_tracking(
    db, order_id, status, created_at, assigned_at, delivered_at, cancel_reason, cancelled_at
):
    tracking_queries.add_tracking(db, order_id, "Pending", _iso(created_at))
    if status == "Cancelled":
        tracking_queries.add_tracking(
            db, order_id, "Cancelled", _iso(cancelled_at), note=cancel_reason
        )
        return
    if assigned_at:
        tracking_queries.add_tracking(db, order_id, "Assigned", _iso(assigned_at))
    if status in ("On the way", "Delivered"):
        tracking_queries.add_tracking(
            db, order_id, "On the way", _iso(assigned_at + timedelta(minutes=5))
        )
    if status == "Delivered":
        tracking_queries.add_tracking(db, order_id, "Delivered", _iso(delivered_at))


def seed_demo(db, demo_password):
    rng = random.Random(RANDOM_SEED)  # noqa: S311 (demo data, not crypto)
    password_hash = generate_password_hash(demo_password, method="scrypt")

    service_ids = _seed_services(db)
    driver_ids = _seed_drivers(db)
    ali_id, sana_id, bilal_id, other_ids = _seed_customers(db, rng, password_hash)
    now = datetime.now(UTC)

    filler_total = TOTAL_ORDERS - 4
    ali_slots = set(rng.sample(range(filler_total), ALI_FILLER_ORDERS))
    filler_customers = iter(
        ali_id if i in ali_slots else rng.choice(other_ids) for i in range(filler_total)
    )

    for _ in range(41):
        _insert_filler_order(db, rng, next(filler_customers), service_ids, driver_ids, now)
    _insert_ali_petrol_order(db, ali_id, service_ids["Petrol"], driver_ids[0], now)
    _insert_ali_generator_order(db, ali_id, service_ids["Generator fuel"], now)
    for _ in range(2):
        _insert_filler_order(db, rng, next(filler_customers), service_ids, driver_ids, now)
    _insert_emergency_order(
        db,
        sana_id,
        service_ids["Petrol"],
        now,
        minutes_ago=6,
        quantity=10,
        note="White Corolla near exit 4",
    )
    _insert_emergency_order(
        db,
        bilal_id,
        service_ids["Petrol"],
        now,
        minutes_ago=4,
        quantity=5,
        note="Black Honda CD 70",
    )
    for customer_id in filler_customers:
        _insert_filler_order(db, rng, customer_id, service_ids, driver_ids, now)
