"""SQL for the users table. Always parameterised with `?`."""


def find_by_email(db, email):
    return db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()


def find_by_id(db, user_id):
    return db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()


def find_by_phone(db, phone):
    return db.execute("SELECT * FROM users WHERE phone = ?", (phone,)).fetchone()


def create_user(db, name, email, phone, password_hash, role, is_active=1):
    cursor = db.execute(
        """
        INSERT INTO users (name, email, phone, password_hash, role, is_active)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (name, email, phone, password_hash, role, is_active),
    )
    return cursor.lastrowid


def count_admins(db):
    row = db.execute("SELECT COUNT(*) AS n FROM users WHERE role = 'admin'").fetchone()
    return row["n"]


def record_failed_login(db, user_id, failed_attempts, locked_until):
    db.execute(
        "UPDATE users SET failed_attempts = ?, locked_until = ? WHERE user_id = ?",
        (failed_attempts, locked_until, user_id),
    )


def reset_login_state(db, user_id):
    db.execute(
        "UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE user_id = ?",
        (user_id,),
    )


def bump_session_version(db, user_id):
    db.execute(
        "UPDATE users SET session_version = session_version + 1 WHERE user_id = ?",
        (user_id,),
    )


_CUSTOMER_LIST_SELECT = """
    SELECT users.*,
           (SELECT COUNT(*) FROM orders WHERE orders.user_id = users.user_id) AS orders_count,
           (SELECT MAX(created_at) FROM orders WHERE orders.user_id = users.user_id)
               AS last_order_at
    FROM users
"""


def count_customers(db, search=""):
    if not search:
        row = db.execute("SELECT COUNT(*) AS n FROM users WHERE role = 'customer'").fetchone()
        return row["n"]
    pattern = f"%{search}%"
    row = db.execute(
        "SELECT COUNT(*) AS n FROM users WHERE role = 'customer' "
        "AND (name LIKE ? OR email LIKE ? OR phone LIKE ?)",
        (pattern, pattern, pattern),
    ).fetchone()
    return row["n"]


def count_blocked_customers(db):
    row = db.execute(
        "SELECT COUNT(*) AS n FROM users WHERE role = 'customer' AND is_active = 0"
    ).fetchone()
    return row["n"]


def list_customers(db, search, limit, offset):
    """Admin Customers screen (docs/SPEC.md screen 16): search by name, email
    or phone, newest-name-first is not useful here, so alphabetical by name
    keeps the list stable across page loads while new orders come and go."""
    if not search:
        return db.execute(
            f"{_CUSTOMER_LIST_SELECT} WHERE role = 'customer' "  # noqa: S608
            "ORDER BY name COLLATE NOCASE LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    pattern = f"%{search}%"
    return db.execute(
        f"""
        {_CUSTOMER_LIST_SELECT}
        WHERE role = 'customer' AND (name LIKE ? OR email LIKE ? OR phone LIKE ?)
        ORDER BY name COLLATE NOCASE
        LIMIT ? OFFSET ?
        """,  # noqa: S608
        (pattern, pattern, pattern, limit, offset),
    ).fetchall()


def find_customer_by_id(db, user_id):
    """role = 'customer' here is also the access rule that keeps an admin
    out of this list and out of block/unblock (CLAUDE.md: an admin can never
    block an admin or themselves) - there is simply no customer row for them."""
    return db.execute(
        f"{_CUSTOMER_LIST_SELECT} WHERE users.user_id = ? AND role = 'customer'",  # noqa: S608
        (user_id,),
    ).fetchone()


def total_spent_delivered(db, user_id):
    row = db.execute(
        "SELECT ROUND(SUM(total_amount), 2) AS total FROM orders "
        "WHERE user_id = ? AND status = 'Delivered'",
        (user_id,),
    ).fetchone()
    return row["total"]


def list_last_orders(db, user_id, limit=5):
    return db.execute(
        """
        SELECT orders.*, services.name AS service_name, services.unit AS service_unit
        FROM orders JOIN services ON services.service_id = orders.service_id
        WHERE orders.user_id = ?
        ORDER BY orders.created_at DESC
        LIMIT ?
        """,
        (user_id, limit),
    ).fetchall()


def block(db, user_id):
    db.execute(
        "UPDATE users SET is_active = 0, session_version = session_version + 1 WHERE user_id = ?",
        (user_id,),
    )


def unblock(db, user_id):
    db.execute("UPDATE users SET is_active = 1 WHERE user_id = ?", (user_id,))


def list_locked(db, now):
    """Accounts still locked out right now, most recently locked first
    (admin dashboard Security card)."""
    return db.execute(
        "SELECT name, locked_until FROM users WHERE locked_until IS NOT NULL "
        "AND locked_until > ? ORDER BY locked_until DESC",
        (now,),
    ).fetchall()
