"""App configuration, built from environment variables (see .env.example)."""

import os
import secrets
from datetime import timedelta


class ConfigError(RuntimeError):
    """Raised when production settings are missing or unsafe."""


def build_config():
    env = os.environ.get("FLASK_ENV", "development")
    debug = os.environ.get("DEBUG", "0") == "1"
    secret_key = os.environ.get("SECRET_KEY", "")
    is_production = env == "production"

    if is_production and (not secret_key or debug):
        raise ConfigError("Refusing to start in production without SECRET_KEY, or with DEBUG on.")
    if not secret_key:
        secret_key = secrets.token_hex(32)  # dev convenience only, changes on restart

    session_absolute_hours = int(os.environ.get("SESSION_ABSOLUTE_HOURS", "12"))

    return {
        "ENV": env,
        "DEBUG": debug,
        "SECRET_KEY": secret_key,
        "DATABASE_PATH": os.environ.get("DATABASE_PATH", "instance/ajora.db"),
        "RATELIMIT_STORAGE_URI": os.environ.get("RATELIMIT_STORAGE_URI", "memory://"),
        "LOG_DIR": os.environ.get("LOG_DIR", "logs"),
        "SESSION_IDLE_MINUTES": int(os.environ.get("SESSION_IDLE_MINUTES", "30")),
        "SESSION_ABSOLUTE_HOURS": session_absolute_hours,
        "DEMO_PASSWORD": os.environ.get("DEMO_PASSWORD", ""),
        "TRUSTED_PROXY_COUNT": int(os.environ.get("TRUSTED_PROXY_COUNT", "0")),
        "MAX_CONTENT_LENGTH": 1 * 1024 * 1024,
        "SESSION_COOKIE_NAME": "__Host-ajora" if is_production else "session",
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SECURE": is_production,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "PERMANENT_SESSION_LIFETIME": timedelta(hours=session_absolute_hours),
        "WTF_CSRF_TIME_LIMIT": 3600,
    }
