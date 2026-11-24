"""Error pages: plain words, never a code or stack trace (docs/SPEC.md screen 20)."""

from flask import render_template, request
from flask_wtf.csrf import CSRFError

from app.security import security_logger

MESSAGES = {
    400: "This form expired. Reload the page and try again.",
    403: "This page is for AJORA admins only.",
    404: "We could not find this page.",
    429: "Too many tries. Wait a minute and try again.",
    500: "Something went wrong on our side. Your data is safe. Please try again.",
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
    return render_template("errors.html", message=MESSAGES[status]), status


def init_errors(app):
    for status in MESSAGES:
        app.register_error_handler(status, lambda e, status=status: _render(status, e))
