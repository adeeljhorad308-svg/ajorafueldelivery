"""Pure validation helpers for auth forms. No SQL, no Flask request object."""

import re
from pathlib import Path

from email_validator import EmailNotValidError, validate_email

PHONE_RE = re.compile(r"^03\d{9}$")
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128

_COMMON_PASSWORDS_PATH = Path(__file__).resolve().parent.parent / "data" / "common-passwords.txt"


def _load_common_passwords():
    with _COMMON_PASSWORDS_PATH.open(encoding="utf-8") as handle:
        return {line.strip().lower() for line in handle if line.strip()}


_COMMON_PASSWORDS = _load_common_passwords()


def normalize_email(email):
    return (email or "").strip().lower()


def normalize_phone(phone):
    return re.sub(r"[^0-9]", "", phone or "")


def is_valid_email(email):
    try:
        validate_email(email, check_deliverability=False)
    except EmailNotValidError:
        return False
    return True


def is_valid_phone(phone):
    return bool(PHONE_RE.match(phone))


def is_valid_name(name):
    name = (name or "").strip()
    return 2 <= len(name) <= 60


def password_errors(password, email):
    """Rules from docs/SECURITY.md: 8+ chars, not common, not equal to the email."""
    errors = []
    if len(password) < MIN_PASSWORD_LENGTH:
        errors.append("Password must be at least 8 characters.")
    if len(password) > MAX_PASSWORD_LENGTH:
        errors.append("Password must be 128 characters or fewer.")
    if password.lower() in _COMMON_PASSWORDS:
        errors.append("Choose a less common password.")
    if email and password.lower() == email.lower():
        errors.append("Password cannot be the same as your email.")
    return errors
