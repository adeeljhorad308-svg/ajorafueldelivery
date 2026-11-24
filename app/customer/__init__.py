"""Customer blueprint. Order screens land in later sessions."""

from flask import Blueprint, render_template

from app.security import login_required

bp = Blueprint("customer", __name__)


@bp.get("/app")
@login_required
def home():
    return render_template("customer/home.html")
