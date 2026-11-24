"""CLI commands: init-db, seed, create-admin, backup."""

import shutil
from datetime import UTC, datetime
from pathlib import Path

import click
from flask import current_app
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash

from app.db import get_db, init_db
from app.demo_data import seed_demo
from app.queries import users as user_queries

BACKUPS_TO_KEEP = 7


@click.command("init-db")
@with_appcontext
def init_db_command():
    """Create tables (drops old data)."""
    init_db()
    click.echo("Database initialised.")


@click.command("seed")
@click.option("--demo", is_flag=True, help="Allow seeding in production.")
@with_appcontext
def seed_command(demo):
    """Load demo data from docs/FIGMA.md."""
    if current_app.config["ENV"] == "production" and not demo:
        raise click.ClickException("Refusing to seed in production without --demo.")
    demo_password = current_app.config["DEMO_PASSWORD"]
    if not demo_password:
        raise click.ClickException("Set DEMO_PASSWORD in .env before seeding.")
    db = get_db()
    seed_demo(db, demo_password)
    db.commit()
    click.echo("Demo data loaded.")


@click.command("create-admin")
@with_appcontext
def create_admin_command():
    """Create an admin account (terminal only)."""
    email = click.prompt("Email")
    password = click.prompt("Password", hide_input=True, confirmation_prompt=True)
    if len(password) < 8:
        raise click.ClickException("Password must be at least 8 characters.")
    db = get_db()
    if user_queries.find_by_email(db, email):
        raise click.ClickException("This email is already registered.")
    full_name = click.prompt("Full name")
    phone = click.prompt("Phone (03XXXXXXXXX)")
    password_hash = generate_password_hash(password, method="scrypt")
    user_queries.create_user(db, full_name, email, phone, password_hash, "admin")
    db.commit()
    click.echo(f"Admin account created for {email}.")


@click.command("backup")
@with_appcontext
def backup_command():
    """Dated copy of the database in instance/backups, keeps 7."""
    db_path = Path(current_app.config["DATABASE_PATH"])
    backups_dir = db_path.parent / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")
    backup_path = backups_dir / f"{db_path.stem}-{stamp}.db"
    shutil.copy(db_path, backup_path)
    _prune_old_backups(backups_dir, db_path.stem)
    click.echo(f"Backup saved to {backup_path}.")


def _prune_old_backups(backups_dir, stem):
    backups = sorted(backups_dir.glob(f"{stem}-*.db"), key=lambda p: p.name, reverse=True)
    for stale in backups[BACKUPS_TO_KEEP:]:
        stale.unlink()


def init_app(app):
    app.cli.add_command(init_db_command)
    app.cli.add_command(seed_command)
    app.cli.add_command(create_admin_command)
    app.cli.add_command(backup_command)
