"""Customers (C11, docs/SPEC.md screen 16, pop-up 4). GET lists/searches
customers; GET /admin/customers/<id> renders the same list with that one
customer's panel open (so it is a real, bookmarkable, no-JS-needed URL); the
one POST blocks or unblocks."""

import sqlite3

from flask import abort, flash, g, redirect, render_template, request, url_for

from app.admin import bp
from app.admin.customers_presentation import (
    PER_PAGE,
    customer_panel_context,
    customer_row,
    customers_pagination,
)
from app.applog import app_logger
from app.db import get_db
from app.queries import users as user_queries
from app.security import security_logger

MAX_SEARCH_LENGTH = 80


def _search_query():
    return (request.args.get("q") or "").strip()[:MAX_SEARCH_LENGTH]


def _list_context(db, search, selected_panel=None):
    page = request.args.get("page", 1, type=int) or 1
    total_count = user_queries.count_customers(db, search)
    page_info = customers_pagination(total_count, page)
    offset = (page_info["page"] - 1) * PER_PAGE
    rows = user_queries.list_customers(db, search, PER_PAGE, offset)
    return {
        "rows": [customer_row(row) for row in rows],
        "page_info": page_info,
        "search": search,
        "total_count": total_count,
        "blocked_count": user_queries.count_blocked_customers(db),
        "page_url": lambda n: url_for("admin.customers", q=search or None, page=n),
        "close_url": url_for("admin.customers", q=search or None, page=page_info["page"]),
        "selected_panel": selected_panel,
    }


@bp.get("/admin/customers")
def customers():
    db = get_db()
    return render_template("admin/customers.html", **_list_context(db, _search_query()))


@bp.get("/admin/customers/<int:user_id>")
def customer_detail(user_id):
    db = get_db()
    row = user_queries.find_customer_by_id(db, user_id)
    if row is None:
        abort(404)
    panel = customer_panel_context(
        row,
        user_queries.total_spent_delivered(db, user_id),
        user_queries.list_last_orders(db, user_id),
    )
    return render_template(
        "admin/customers.html", **_list_context(db, _search_query(), selected_panel=panel)
    )


@bp.post("/admin/customers/<int:user_id>/block")
def customer_block(user_id):
    db = get_db()
    row = None
    action = request.form.get("action")
    try:
        db.execute("BEGIN IMMEDIATE")
        row = user_queries.find_customer_by_id(db, user_id)
        if row is None:
            db.rollback()
            abort(404)
        if action == "block":
            user_queries.block(db, user_id)
        elif action == "unblock":
            user_queries.unblock(db, user_id)
        else:
            db.rollback()
            abort(400)
        db.commit()
    except sqlite3.IntegrityError:
        db.rollback()
        raise
    admin_id = g.current_user["user_id"]
    app_logger().info("customer %s %sed by admin %s", user_id, action, admin_id)
    if action == "block":
        security_logger().info("customer %s blocked by admin %s", user_id, admin_id)
    flash(f"{row['name']} is now {'blocked' if action == 'block' else 'active'}.", "success")
    return redirect(url_for("admin.customer_detail", user_id=user_id))
