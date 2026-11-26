"""Pure validation for the Drivers admin form (docs/SPEC.md pop-up 6). No
SQL, no Flask request object."""

import re

from app.areas import area_names

VEHICLE_RE = re.compile(r"^[A-Z]{3}-\d{4}$")
STATUSES = ("Available", "Off Duty")


def normalize_vehicle_no(raw):
    return (raw or "").strip().upper()


def is_valid_vehicle_no(value):
    return bool(VEHICLE_RE.match(value))


def is_valid_area(value):
    return value in area_names()


def is_valid_status(value):
    return value in STATUSES
