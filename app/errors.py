"""Error pages: plain words, never a code or stack trace (docs/SPEC.md screen 20)."""

from flask import render_template, request
from flask_wtf.csrf import CSRFError

from app.security import security_logger

ERROR_CONTENT = {
    400: {
        "icon": "rotate-right",
        "tint": "subtle",
        "title": "This form expired.",
        "message": "Reload the page and try again. Nothing was saved twice.",
        "actions": [{"label": "Reload page", "style": "brand", "data_action": "reload"}],
    },
    403: {
        "icon": "shield-halved",
        "tint": "warning",
        "title": "This page is for AJORA admins only.",
        "message": "You are logged in as a customer. Your own orders are on the home page.",
        "actions": [{"label": "Back to home", "style": "brand", "endpoint": "customer.home"}],
    },
    404: {
        "icon": "magnifying-glass",
        "tint": "subtle",
        "title": "We could not find this page.",
        "message": "The link may be old, or the address was typed wrong.",
        "actions": [
            {"label": "Back to home", "style": "brand", "endpoint": "landing"},
            {"label": "Go back", "style": "outline", "data_action": "back"},
        ],
    },
    429: {
        "icon": "clock",
        "tint": "info",
        "title": "Too many tries.",
        "message": "Wait a minute and try again. This keeps your account safe.",
        "actions": [{"label": "Back to log in", "style": "brand", "endpoint": "auth.login"}],
    },
    500: {
        "icon": "circle-exclamation",
        "tint": "error",
        "title": "Something went wrong on our side.",
        "message": "Your data is safe. Please try again in a moment.",
        "actions": [
            {"label": "Try again", "style": "brand", "data_action": "reload"},
            {"label": "Back to home", "style": "outline", "endpoint": "landing"},
        ],
    },
}


def _log(status, error):
    if status == 400 and isinstance(error, CSRFError):
        security_logger().info("csrf fail path=%s", request.path)
    elif status == 403:
        security_logger().info("403 path=%s", request.path)
    elif status == 429:
        security_logger().info("429 path=%s", request.path)


def _render(status, error):
    _log(status, error)
    return render_template("errors.html", content=ERROR_CONTENT[status]), status


def init_errors(app):
    for status in ERROR_CONTENT:
        app.register_error_handler(status, lambda e, status=status: _render(status, e))
