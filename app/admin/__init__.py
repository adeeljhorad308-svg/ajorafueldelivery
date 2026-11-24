"""Admin blueprint, deny by default (docs/SECURITY.md A01). Screens land in later sessions."""

from flask import Blueprint, render_template

from app.security import require_admin

bp = Blueprint("admin", __name__)


@bp.before_request
def guard():
    return require_admin()


@bp.get("/admin")
def dashboard():
    return render_template("admin/dashboard.html")
