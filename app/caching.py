"""Static file versioning and Cache-Control rules (docs/PERFORMANCE.md)."""

from pathlib import Path

from flask import current_app, request, url_for


def static_versioned(filename):
    """URL for a static file with a `?v=<mtime>` query string so it can be cached forever."""
    file_path = Path(current_app.static_folder) / filename
    version = int(file_path.stat().st_mtime) if file_path.exists() else 0
    return url_for("static", filename=filename) + f"?v={version}"


def _set_cache_headers(response):
    path = request.path
    if path.startswith(current_app.static_url_path + "/"):
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    elif path.startswith(("/app", "/admin", "/api")) or path == "/health":
        response.headers["Cache-Control"] = "no-store"
    return response


def init_caching(app):
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 31536000
    app.jinja_env.globals["static_versioned"] = static_versioned
    app.after_request(_set_cache_headers)
