"""Phone numbers: stored as 03001234567, shown as 0300-1234567 (CLAUDE.md formats)."""


def format_phone(digits):
    return f"{digits[:4]}-{digits[4:]}"
