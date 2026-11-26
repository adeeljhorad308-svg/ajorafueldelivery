"""Services and prices (C12, docs/SPEC.md screen 17, pop-up 5). GET lists
every service; the two POSTs add or edit/turn on/off one - all wording lives
in services_presentation.py / services_validation.py."""

import sqlite3

from flask import abort, flash, g, redirect, render_template, request, url_for

from app.admin import bp
from app.admin.services_presentation import (
    price_reminder,
    service_row,
    services_summary,
    turnoff_dialog_context,
)
from app.admin.services_validation import (
    is_valid_category,
    is_valid_name,
    is_valid_unit,
    parse_price,
)
from app.applog import app_logger
from app.db import get_db
from app.queries import services as service_queries

NAME_TAKEN_MESSAGE = "A service with this name already exists."


def _parse_service_form(form):
    name = (form.get("name") or "").strip()
    category = form.get("category") or ""
    unit = form.get("unit") or ""
    price = parse_price(form.get("unit_price"))
    # The turn-off confirm dialog posts an explicit hidden "available=0" (not
    # just an absent key, the way an unchecked checkbox would) - a presence
    # check alone would wrongly read that literal "0" string as truthy.
    available = 1 if form.get("available") == "1" else 0

    errors = {}
    if not is_valid_name(name):
        errors["name"] = "Name must be 2-50 characters."
    if not is_valid_category(category):
        errors["category"] = "Choose a category."
    if not is_valid_unit(unit):
        errors["unit"] = "Choose a unit."
    if price is None:
        errors["unit_price"] = "Price must be above 0, with at most 2 decimals."
    fields = {
        "name": name,
        "category": category or "Fuel",
        "unit": unit or "litre",
        "unit_price": form.get("unit_price") or "",
        "available": available,
    }
    return fields, price, errors


def _render_with_error(open_dialog, fields, errors):
    db = get_db()
    rows = [service_row(row) for row in service_queries.list_all(db)]
    return render_template(
        "admin/services.html",
        rows=rows,
        summary=services_summary(rows),
        price_reminder=price_reminder(rows),
        turnoff_dialogs=[turnoff_dialog_context(row) for row in rows],
        open_dialog=open_dialog,
        form_values=fields,
        form_errors=errors,
    ), 400


@bp.get("/admin/services")
def services():
    db = get_db()
    rows = [service_row(row) for row in service_queries.list_all(db)]
    return render_template(
        "admin/services.html",
        rows=rows,
        summary=services_summary(rows),
        price_reminder=price_reminder(rows),
        turnoff_dialogs=[turnoff_dialog_context(row) for row in rows],
        open_dialog=None,
        form_values=None,
        form_errors={},
    )


@bp.post("/admin/services")
def service_create():
    db = get_db()
    fields, price, errors = _parse_service_form(request.form)
    if not errors and service_queries.find_by_name_ci(db, fields["name"]) is not None:
        errors["name"] = NAME_TAKEN_MESSAGE
    if errors:
        return _render_with_error("dialog-add-service", fields, errors)

    db.execute("BEGIN IMMEDIATE")
    try:
        service_queries.create_service(
            db, fields["name"], fields["category"], fields["unit"], price, fields["available"]
        )
        db.commit()
    except sqlite3.IntegrityError:
        db.rollback()
        return _render_with_error("dialog-add-service", fields, {"name": NAME_TAKEN_MESSAGE})
    app_logger().info("service '%s' added by admin %s", fields["name"], g.current_user["user_id"])
    flash(f"{fields['name']} added.", "success")
    return redirect(url_for("admin.services"))


@bp.post("/admin/services/<int:service_id>")
def service_update(service_id):
    db = get_db()
    existing_row = service_queries.find_by_id(db, service_id)
    if existing_row is None:
        abort(404)

    fields, price, errors = _parse_service_form(request.form)
    if not errors and service_queries.find_by_name_ci(db, fields["name"], service_id) is not None:
        errors["name"] = NAME_TAKEN_MESSAGE
    if errors:
        return _render_with_error(f"dialog-edit-service-{service_id}", fields, errors)

    db.execute("BEGIN IMMEDIATE")
    try:
        service_queries.update_service(
            db,
            service_id,
            fields["name"],
            fields["category"],
            fields["unit"],
            price,
            fields["available"],
        )
        db.commit()
    except sqlite3.IntegrityError:
        db.rollback()
        return _render_with_error(
            f"dialog-edit-service-{service_id}", fields, {"name": NAME_TAKEN_MESSAGE}
        )
    app_logger().info("service %s updated by admin %s", service_id, g.current_user["user_id"])
    return redirect(url_for("admin.services"))
