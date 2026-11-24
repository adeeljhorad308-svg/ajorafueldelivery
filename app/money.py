"""Money as exact decimal.Decimal, never float.

SQLite has no real DECIMAL type: a column declared DECIMAL(10,2) still gets
NUMERIC affinity, and SQLite silently stores a bound value as a float or int
(confirmed: `typeof()` reports "real"/"integer" for a value like "5040.01").
The declared type is kept to match the FYP document and for PRAGMA
table_info, but this module is the only place that is allowed to assume
anything about what comes back from a money column - every value is
re-quantized here before use, so the rest of the app never touches a float.

Reports pages may use ROUND(SUM(total_amount), 2) in SQL for a single
aggregate value (there is no per-row maths to get wrong), then pass that one
result through from_db() here. No other money arithmetic belongs in SQL.
"""

from decimal import ROUND_HALF_UP, Decimal

TWO_PLACES = Decimal("0.01")


def to_db(amount):
    """Quantize to paisa and return the exact text a money column should store."""
    return str(amount.quantize(TWO_PLACES, rounding=ROUND_HALF_UP))


def from_db(value):
    """Read a money column back as an exact Decimal, whatever storage class
    SQLite actually used for it."""
    return Decimal(str(value)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def parse_amount(raw):
    """Parse user/form input into a quantized Decimal.

    Raises decimal.InvalidOperation on bad input; callers turn that into a
    field error.
    """
    return Decimal(str(raw).strip()).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def format_pkr(amount):
    """'PKR 5,040' for whole rupees, 'PKR 263.45' when there are paisa."""
    amount = amount.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    if amount == amount.to_integral_value():
        return f"PKR {int(amount):,}"
    return f"PKR {amount:,.2f}"
