import os

import pytest
from werkzeug.security import generate_password_hash

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")

from app import create_app  # noqa: E402
from app.db import get_db, init_db  # noqa: E402
from app.queries import users as user_queries  # noqa: E402


def _build_app(tmp_path, overrides=None):
    db_path = tmp_path / "test.db"
    config = {
        "TESTING": True,
        "DATABASE_PATH": str(db_path),
        "RATELIMIT_ENABLED": False,
        "WTF_CSRF_ENABLED": False,
        "DEMO_PASSWORD": "demo-pass-1234",
    }
    if overrides:
        config.update(overrides)
    test_app = create_app(config)
    with test_app.app_context():
        init_db()
        get_db().commit()
    return test_app


@pytest.fixture
def app(tmp_path):
    yield _build_app(tmp_path)


@pytest.fixture
def csrf_app(tmp_path):
    """A second app with CSRF actually enforced, for the one test that needs it."""
    yield _build_app(tmp_path, {"WTF_CSRF_ENABLED": True})


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def make_user(app):
    def _make(
        email="user@example.com",
        password="StrongPass1",  # noqa: S107 (test fixture default, not a secret)
        phone="03001112222",
        role="customer",
        full_name="Test User",
        is_active=1,
    ):
        with app.app_context():
            db = get_db()
            password_hash = generate_password_hash(password, method="scrypt")
            user_id = user_queries.create_user(
                db, full_name, email, phone, password_hash, role, is_active
            )
            db.commit()
        return user_id

    return _make
