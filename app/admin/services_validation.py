"""Pure validation for the Services admin form (docs/SPEC.md pop-up 5). No
SQL, no Flask request object."""

import re
from decimal import Decimal

NAME_MIN_LENGTH = 2
NAME_MAX_LENGTH = 50
CATEGORIES = ("Fuel", "Assistance")
UNITS = ("litre", "service")

_PRICE_RE = re.compile(r"^\d{1,8}(\.\d{1,2})?$")


def is_valid_name(name):
    name = (name or "").strip()
    return NAME_MIN_LENGTH <= len(name) <= NAME_MAX_LENGTH


def is_valid_category(value):
    return value in CATEGORIES


def is_valid_unit(value):
    return value in UNITS


def parse_price(raw):
    """A positive Decimal with at most 2 decimal places, or None if the raw
    text isn't one (CLAUDE.md money rule: Decimal only, never a float)."""
    raw = (raw or "").strip()
    if not _PRICE_RE.match(raw):
        return None
    value = Decimal(raw)
    return value if value > 0 else None
