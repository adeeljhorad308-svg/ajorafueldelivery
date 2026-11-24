"""Pure validation helpers for customer order forms. No SQL, no Flask request object."""

from app.areas import area_names

MIN_FUEL_LITRES = 5
MAX_FUEL_LITRES = 100
MAX_ADDRESS_LENGTH = 200
MAX_NOTE_LENGTH = 200


def parse_litres(raw):
    """Return an int litres value, or None if not a plain whole number."""
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return None
    return value


def is_valid_fuel_litres(litres):
    return litres is not None and MIN_FUEL_LITRES <= litres <= MAX_FUEL_LITRES


def is_valid_address(address):
    address = (address or "").strip()
    return 1 <= len(address) <= MAX_ADDRESS_LENGTH


def is_valid_note(note):
    return len(note or "") <= MAX_NOTE_LENGTH


def is_valid_area(area):
    return area in area_names()
