"""8 response headers, CSRF, rate limits, sessions and the security log (docs/SECURITY.md)."""

import logging
from datetime import timedelta
from functools import wraps
from logging.handlers import RotatingFileHandler
from pathlib import Path

from flask import abort, current_app, flash, g, redirect, request, session, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf import CSRFProtect

from app import timeutil
from app.db import get_db
from app.queries import users as user_queries

CSP_BASE = (
    "default-src 'self'; script-src 'self'; style-src 'self'; "
    "img-src 'self' data:; font-src 'self'; connect-src 'self'; "
    "object-src 'none'; base-uri 'self'; form-action 'self'; "
    "frame-ancestors 'none'"
)
IDLE_TIMEOUT_MESSAGE = "You were logged out after 30 minutes of no activity."

csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address, default_limits=["300 per minute"])


def init_security(app):
    csrf.init_app(app)
    limiter.init_app(app)
    _init_security_log(app)
    app.after_request(_set_security_headers)
    app.before_request(_enforce_session_rules)


def _set_security_headers(response):
    in_production = current_app.config["ENV"] == "production" and not current_app.config["DEBUG"]
    csp = CSP_BASE + ("; upgrade-insecure-requests" if in_production else "")
    response.headers["Content-Security-Policy"] = csp
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "geolocation=(self), camera=(), microphone=(), payment=()"
    )
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    if in_production:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


def _init_security_log(app):
    log_dir = Path(app.config["LOG_DIR"])
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(log_dir / "security.log", maxBytes=1_000_000, backupCount=5)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger = logging.getLogger("ajora.security")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    app.extensions["security_logger"] = logger


def security_logger():
    return current_app.extensions["security_logger"]


def is_safe_next(path):
    """Same-site path only: one leading '/', no '//' start, no backslash, no CR/LF."""
    if not path:
        return False
    if not path.startswith("/") or path.startswith("//"):
        return False
    return not ("\\" in path or "\r" in path or "\n" in path)


def _is_background_poll():
    # Polling (GET /api/*) never counts as activity, so it can never keep an
    # idle session alive on its own, but it must still see an idle session
    # as expired once the real idle window has passed.
    return request.path.startswith("/api/") and request.method == "GET"


def _idle_timed_out():
    last_seen = session.get("last_seen")
    if not last_seen:
        return False
    minutes = current_app.config["SESSION_IDLE_MINUTES"]
    return timeutil.utcnow() - timeutil.from_sql(last_seen) > timedelta(minutes=minutes)


def _absolute_timed_out():
    # Flask refreshes the permanent session cookie on every request, so the
    # absolute lifetime is not enforced by PERMANENT_SESSION_LIFETIME alone;
    # login_at is the fixed point we check against.
    login_at = session.get("login_at")
    if not login_at:
        return False
    hours = current_app.config["SESSION_ABSOLUTE_HOURS"]
    return timeutil.utcnow() - timeutil.from_sql(login_at) > timedelta(hours=hours)


def _enforce_session_rules():
    if not session.get("user_id"):
        return None

    if _idle_timed_out():
        session.clear()
        if _is_background_poll():
            return None
        flash(IDLE_TIMEOUT_MESSAGE, "info")
        next_path = request.path if is_safe_next(request.path) else None
        return redirect(url_for("auth.login", next=next_path))

    if _absolute_timed_out():
        session.clear()
        return None

    db = get_db()
    user = user_queries.find_by_id(db, session["user_id"])
    if (
        user is None
        or not user["is_active"]
        or user["session_version"] != session.get("session_version")
    ):
        session.clear()
        return None

    if not _is_background_poll():
        session["last_seen"] = timeutil.to_sql(timeutil.utcnow())
    g.current_user = user
    return None


def require_admin():
    """Shared guard for the admin blueprint's `before_request` and @admin_required."""
    user = g.get("current_user")
    if user is None:
        next_path = request.path if is_safe_next(request.path) else None
        return redirect(url_for("auth.login", next=next_path))
    if user["role"] != "admin":
        abort(403)
    return None


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.get("current_user") is None:
            next_path = request.path if is_safe_next(request.path) else None
            return redirect(url_for("auth.login", next=next_path))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        guard_response = require_admin()
        if guard_response is not None:
            return guard_response
        return view(*args, **kwargs)

    return wrapped
