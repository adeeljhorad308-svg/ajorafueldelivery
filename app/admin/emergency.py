"""Emergency requests (C11, docs/SPEC.md screen 15). Read-only list: Assign
driver opens Order details' pop-up 2, Open goes straight there too - this
screen adds no new POST routes of its own."""

from flask import render_template

from app import timeutil
from app.admin import bp
from app.admin.emergency_presentation import emergency_card, header_summary, sort_cards
from app.db import get_db
from app.queries import admin_orders as order_queries


@bp.get("/admin/emergency")
def emergency():
    db = get_db()
    now = timeutil.utcnow()
    cards = sort_cards(
        [emergency_card(row, now) for row in order_queries.list_open_emergencies(db)]
    )
    title, caption = header_summary(cards)
    max_id = max((card["order_id"] for card in cards), default=0)
    return render_template(
        "admin/emergency.html",
        cards=cards,
        header_title=title,
        header_caption=caption,
        max_emergency_id=max_id,
    )
