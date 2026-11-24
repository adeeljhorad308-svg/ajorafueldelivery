from app.db import get_db


def test_pragmas_are_set(app):
    with app.app_context():
        db = get_db()
        assert db.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert db.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
        assert db.execute("PRAGMA synchronous").fetchone()[0] == 1  # NORMAL
        assert db.execute("PRAGMA foreign_keys").fetchone()[0] == 1
