"""SQL for the users table. Always parameterised with `?`."""


def find_by_email(db, email):
    return db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()


def find_by_id(db, user_id):
    return db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def find_by_phone(db, phone):
    return db.execute("SELECT * FROM users WHERE phone = ?", (phone,)).fetchone()


def create_user(db, full_name, email, phone, password_hash, role, is_active=1):
    cursor = db.execute(
        """
        INSERT INTO users (full_name, email, phone, password_hash, role, is_active)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (full_name, email, phone, password_hash, role, is_active),
    )
    return cursor.lastrowid


def count_admins(db):
    row = db.execute("SELECT COUNT(*) AS n FROM users WHERE role = 'admin'").fetchone()
    return row["n"]


def record_failed_login(db, user_id, failed_attempts, locked_until):
    db.execute(
        "UPDATE users SET failed_attempts = ?, locked_until = ? WHERE id = ?",
        (failed_attempts, locked_until, user_id),
    )


def reset_login_state(db, user_id):
    db.execute(
        "UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE id = ?",
        (user_id,),
    )


def bump_session_version(db, user_id):
    db.execute(
        "UPDATE users SET session_version = session_version + 1 WHERE id = ?",
        (user_id,),
    )
