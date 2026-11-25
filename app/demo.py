"""Dev-only demo helper for the 30 Nov checkpoint: moves one order to its next
allowed status with a tracking row, same as an admin action would (admin side
is not built yet). Pure logic, no Flask imports - the CLI command wraps this.
"""

from app import dispatch, timeutil
from app.areas import area_centre
from app.queries import assignments as assignment_queries
from app.queries import drivers as driver_queries
from app.queries import orders as order_queries
from app.queries import tracking as tracking_queries

NEXT_STATUS = {
    "Pending": "Assigned",
    "Assigned": "On the Way",
    "On the Way": "Delivered",
}


class DemoAdvanceError(Exception):
    """An order has no next status, or no driver is free to assign."""


def _order_location(order_row):
    if order_row["latitude"] is not None and order_row["longitude"] is not None:
        return order_row["latitude"], order_row["longitude"]
    return area_centre(order_row["area"])


def advance_order(db, order_row, now=None):
    """Move order_row to its next allowed status. Returns the new status.

    Raises DemoAdvanceError if the order is already Delivered/Cancelled, or a
    Pending order has no Available driver to assign.
    """
    now = now or timeutil.utcnow()
    current = order_row["status"]
    next_status = NEXT_STATUS.get(current)
    if next_status is None:
        raise DemoAdvanceError(f"{current} orders cannot be moved any further.")

    if current == "Pending":
        if dispatch.dispatch_order(db, dict(order_row), now) is None:
            raise DemoAdvanceError("No Available driver to assign right now.")
        return next_status

    sql_now = timeutil.to_sql(now)
    lat, lon = _order_location(order_row)
    order_queries.update_status(db, order_row["order_id"], next_status)
    tracking_queries.add_tracking(db, order_row["order_id"], next_status, sql_now, lat, lon)

    if next_status == "Delivered":
        assignment = assignment_queries.find_by_order_id(db, order_row["order_id"])
        if assignment is not None:
            assignment_queries.mark_completed(db, assignment["assign_id"], sql_now)
            driver_queries.set_status(db, assignment["driver_id"], "Available")
            driver_queries.update_location(db, assignment["driver_id"], lat, lon)

    return next_status
