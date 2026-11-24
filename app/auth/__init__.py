"""Auth blueprint: login, register, logout (docs/SPEC.md screens 2 and 3)."""

import math
from datetime import timedelta

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from app import timeutil
from app.auth import validation
from app.db import get_db
from app.queries import users as user_queries
from app.security import is_safe_next, limiter, security_logger

bp = Blueprint("auth", __name__)

LOCK_AFTER_ATTEMPTS = 5
LOCK_MINUTES = 10
WRONG_CREDENTIALS_MESSAGE = "Email or password is not correct."
BLOCKED_MESSAGE = "This account is blocked. Please contact AJORA support."

# Verified on every login with no matching user, so a wrong email and a
# wrong password take the same time (no account-existence timing oracle).
_DUMMY_PASSWORD_HASH = generate_password_hash(
    "not-a-real-password-used-only-for-timing", method="scrypt"
)


def _dashboard_for(role):
    return url_for("admin.dashboard") if role == "admin" else url_for("customer.home")


def _redirect_after_login(role):
    next_path = request.form.get("next")
    if is_safe_next(next_path):
        return redirect(next_path)
    return redirect(_dashboard_for(role))


def _start_session(user):
    session.clear()
    session["user_id"] = user["user_id"]
    session["role"] = user["role"]
    session["session_version"] = user["session_version"]
    now = timeutil.to_sql(timeutil.utcnow())
    session["login_at"] = now
    session["last_seen"] = now
    session.permanent = True


def _is_locked(user):
    locked_until = user["locked_until"]
    return bool(locked_until) and timeutil.from_sql(locked_until) > timeutil.utcnow()


def _minutes_remaining(locked_until):
    remaining = timeutil.from_sql(locked_until) - timeutil.utcnow()
    return max(1, math.ceil(remaining.total_seconds() / 60))


def _clear_lock_if_expired(db, user):
    if user["locked_until"] and not _is_locked(user):
        user_queries.reset_login_state(db, user["user_id"])
        db.commit()
        return user_queries.find_by_id(db, user["user_id"])
    return user


def _record_failed_attempt(db, user):
    attempts = user["failed_attempts"] + 1
    locked_until = None
    if attempts >= LOCK_AFTER_ATTEMPTS:
        locked_until = timeutil.to_sql(timeutil.utcnow() + timedelta(minutes=LOCK_MINUTES))
    user_queries.record_failed_login(db, user["user_id"], attempts, locked_until)
    db.commit()
    return user_queries.find_by_id(db, user["user_id"])


def _verify_password(user, password):
    if len(password) > validation.MAX_PASSWORD_LENGTH:
        return False
    if user is None:
        check_password_hash(_DUMMY_PASSWORD_HASH, password)
        return False
    return check_password_hash(user["password_hash"], password)


def _login_form(next_path, errors=None, status=200):
    return (
        render_template(
            "auth/login.html",
            next=next_path if is_safe_next(next_path) else None,
            errors=errors,
        ),
        status,
    )


@bp.get("/login")
def login():
    if session.get("user_id"):
        return redirect(_dashboard_for(session.get("role")))
    return _login_form(request.args.get("next"))


@bp.post("/login")
@limiter.limit("10/minute;50/hour")
def login_submit():
    email = validation.normalize_email(request.form.get("email"))
    password = request.form.get("password") or ""
    next_path = request.form.get("next")

    errors = {}
    if not email:
        errors["email"] = "Enter your email"
    if not password:
        errors["password"] = "Enter your password"  # noqa: S105 (UI text, not a secret)
    if errors:
        return _login_form(next_path, errors, 400)

    db = get_db()
    user = user_queries.find_by_email(db, email)
    if user is not None:
        user = _clear_lock_if_expired(db, user)

    if user is not None and _is_locked(user):
        minutes = _minutes_remaining(user["locked_until"])
        security_logger().info("lockout email=%s", email)
        message = f"Too many tries. Try again in {minutes} minutes."
        return _login_form(next_path, {"form": message, "form_kind": "lockout"}, 429)

    password_ok = _verify_password(user, password)

    if not password_ok:
        if user is not None:
            user = _record_failed_attempt(db, user)
            if _is_locked(user):
                minutes = _minutes_remaining(user["locked_until"])
                security_logger().info("lockout email=%s", email)
                message = f"Too many tries. Try again in {minutes} minutes."
                return _login_form(next_path, {"form": message, "form_kind": "lockout"}, 429)
        security_logger().info("login failed email=%s", email)
        return _login_form(
            next_path, {"form": WRONG_CREDENTIALS_MESSAGE, "form_kind": "wrong"}, 400
        )

    if not user["is_active"]:
        security_logger().info("login blocked user_id=%s", user["user_id"])
        return _login_form(next_path, {"form": BLOCKED_MESSAGE, "form_kind": "blocked"}, 403)

    user_queries.reset_login_state(db, user["user_id"])
    db.commit()
    _start_session(user)
    security_logger().info("login ok user_id=%s", user["user_id"])
    flash(f"Welcome back, {user['name'].split()[0]}", "success")
    return _redirect_after_login(user["role"])


def _register_form(errors=None, status=200):
    return render_template("auth/register.html", errors=errors), status


@bp.get("/register")
def register():
    if session.get("user_id"):
        return redirect(_dashboard_for(session.get("role")))
    return _register_form()


@bp.post("/register")
@limiter.limit("5/hour")
def register_submit():
    full_name = (request.form.get("full_name") or "").strip()
    email = validation.normalize_email(request.form.get("email"))
    phone = validation.normalize_phone(request.form.get("phone"))
    password = request.form.get("password") or ""
    confirm_password = request.form.get("confirm_password") or ""

    errors = _register_errors(full_name, email, phone, password, confirm_password)

    db = get_db()
    if "email" not in errors and user_queries.find_by_email(db, email):
        errors["email"] = "This email is already registered."
        errors["email_taken"] = True
    if "phone" not in errors and user_queries.find_by_phone(db, phone):
        errors["phone"] = "This phone number is already registered."

    if errors:
        return _register_form(errors, 400)

    password_hash = generate_password_hash(password, method="scrypt")
    user_id = user_queries.create_user(db, full_name, email, phone, password_hash, "customer")
    db.commit()
    user = user_queries.find_by_id(db, user_id)
    _start_session(user)
    security_logger().info("register ok user_id=%s", user_id)
    flash("Account created. Welcome to AJORA.", "success")
    return redirect(url_for("customer.home"))


def _register_errors(full_name, email, phone, password, confirm_password):
    errors = {}
    if not validation.is_valid_name(full_name):
        errors["full_name"] = "Enter your full name"
    if not validation.is_valid_email(email):
        errors["email"] = "Enter a valid email"
    if not validation.is_valid_phone(phone):
        errors["phone"] = "Enter a valid mobile number like 0300-1234567"
    if password != confirm_password:
        errors["confirm_password"] = "Passwords do not match"  # noqa: S105 (UI text)
    else:
        password_problems = validation.password_errors(password, email)
        if password_problems:
            errors["password"] = password_problems[0]
    return errors


@bp.post("/logout")
def logout():
    user_id = session.get("user_id")
    if user_id:
        db = get_db()
        user_queries.bump_session_version(db, user_id)
        db.commit()
        security_logger().info("logout user_id=%s", user_id)
    session.clear()
    return redirect(url_for("landing"))
