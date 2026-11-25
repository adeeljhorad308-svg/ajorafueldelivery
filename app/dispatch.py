"""Smart dispatch: priority queue, Haversine ETA and nearest-neighbour routing.

Pure Python - no Flask imports. Callers pass an already-open db connection so
`dispatch_order` can be called inside the same transaction as placing an
order (CLAUDE.md: multi-step writes in one transaction); it never commits.
`dispatch_pending` commits per order, since it runs standalone later (e.g.
from an admin action), not nested inside another transaction.
"""

import heapq
import math
from decimal import Decimal

from app import timeutil
from app.areas import area_centre
from app.queries import assignments as assignment_queries
from app.queries import drivers as driver_queries
from app.queries import orders as order_queries
from app.queries import tracking as tracking_queries

EARTH_RADIUS_KM = 6371
EXTRA_MINUTES = 5


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance between two points, in kilometres."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return EARTH_RADIUS_KM * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def speed_kmh(dt):
    """Dispatch speed band for the given UTC-aware time, by Asia/Karachi hour."""
    hour = timeutil.to_karachi(dt).hour
    if 7 <= hour < 10 or 17 <= hour < 20:
        return 20
    if hour >= 22 or hour < 6:
        return 40
    return 30


def eta_minutes(distance_km, dt):
    """Minutes to arrival, rounded up (6 km at 30 km/h -> 17 min)."""
    speed = speed_kmh(dt)
    return math.ceil(float(distance_km) / speed * 60 + EXTRA_MINUTES)


def _order_location(order_row):
    if order_row["latitude"] is not None and order_row["longitude"] is not None:
        return order_row["latitude"], order_row["longitude"]
    return area_centre(order_row["area"])


def _nearest_driver(drivers, lat, lon):
    best_driver = None
    best_distance = None
    for driver in drivers:
        distance = haversine_km(lat, lon, driver["latitude"], driver["longitude"])
        if best_distance is None or distance < best_distance:
            best_distance = distance
            best_driver = driver
    return best_driver, best_distance


def dispatch_order(db, order_row, now=None):
    """Try to assign the nearest Available driver to one ASAP order.

    Returns the assignment info on success, or None if no driver is free
    (the order is left Pending; the admin sees it, from C9 on). Does not
    commit, so it can join the caller's own transaction.
    """
    now = now or timeutil.utcnow()
    drivers = driver_queries.list_available(db)
    if not drivers:
        return None
    lat, lon = _order_location(order_row)
    driver, distance = _nearest_driver(drivers, lat, lon)
    distance_km = Decimal(str(distance)).quantize(Decimal("0.01"))
    eta = eta_minutes(distance_km, now)
    assigned_at = timeutil.to_sql(now)

    assignment_queries.create_assignment(
        db, order_row["order_id"], driver["driver_id"], eta, assigned_at, distance_km=distance_km
    )
    order_queries.update_status(db, order_row["order_id"], "Assigned")
    driver_queries.set_status(db, driver["driver_id"], "Busy")
    tracking_queries.add_tracking(db, order_row["order_id"], "Assigned", assigned_at, lat, lon)

    return {"driver_id": driver["driver_id"], "eta_minutes": eta, "distance_km": distance_km}


def _priority_queue(orders):
    queue = []
    for order in orders:
        priority = 2 if order["is_emergency"] else 1
        heapq.heappush(queue, (-priority, order["created_at"], order["order_id"], dict(order)))
    return queue


def dispatch_pending(db, now=None):
    """Assign every waiting ASAP order it can, emergency first then oldest
    first, stopping as soon as no Available driver is left. Commits as it
    goes, so it is safe to call standalone (e.g. once a driver frees up)."""
    now = now or timeutil.utcnow()
    queue = _priority_queue(order_queries.list_pending_asap(db))
    assigned = []
    while queue:
        _, _, order_id, order_row = heapq.heappop(queue)
        result = dispatch_order(db, order_row, now)
        if result is None:
            break
        db.commit()
        assigned.append(order_id)
    return assigned


def nearest_neighbour_route(start_lat, start_lon, stops):
    """Reorder a driver's open stops nearest-first from their current
    position (admin Order details shows "Stop 2 of 3" in this order)."""
    remaining = list(stops)
    route = []
    lat, lon = start_lat, start_lon
    while remaining:
        nearest = min(
            remaining, key=lambda s: haversine_km(lat, lon, s["latitude"], s["longitude"])
        )
        route.append(nearest)
        lat, lon = nearest["latitude"], nearest["longitude"]
        remaining.remove(nearest)
    return route
