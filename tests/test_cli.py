from app.db import get_db


def test_seed_refuses_in_production_without_demo_flag(app):
    app.config["ENV"] = "production"
    runner = app.test_cli_runner()
    result = runner.invoke(args=["seed"])
    assert result.exit_code != 0
    assert "production" in result.output.lower()


def test_seed_refuses_without_demo_password(app):
    app.config["DEMO_PASSWORD"] = ""
    runner = app.test_cli_runner()
    result = runner.invoke(args=["seed"])
    assert result.exit_code != 0
    assert "demo_password" in result.output.lower()


def test_seed_runs_with_demo_flag_in_production(app):
    app.config["ENV"] = "production"
    runner = app.test_cli_runner()
    result = runner.invoke(args=["seed", "--demo"])
    assert result.exit_code == 0
    with app.app_context():
        total = get_db().execute("SELECT COUNT(*) AS n FROM orders").fetchone()["n"]
    assert total == 300


def test_create_admin_creates_a_row(app):
    runner = app.test_cli_runner()
    result = runner.invoke(
        args=["create-admin"],
        input="admin@ajora.test\nStrongPass1\nStrongPass1\nAdmin Person\n03001230000\n",
    )
    assert result.exit_code == 0
    with app.app_context():
        row = get_db().execute("SELECT * FROM users WHERE email = 'admin@ajora.test'").fetchone()
    assert row["role"] == "admin"


def test_backup_creates_file_and_prunes_to_seven(app):
    from pathlib import Path

    runner = app.test_cli_runner()
    for _ in range(9):
        result = runner.invoke(args=["backup"])
        assert result.exit_code == 0

    backups_dir = Path(app.config["DATABASE_PATH"]).parent / "backups"
    backups = list(backups_dir.glob("*.db"))
    assert len(backups) == 7
