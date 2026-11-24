from datetime import UTC, datetime, timedelta

import pytest

from app.db import get_db
from app.queries import users as user_queries
from app.security import is_safe_next

HEADERS_ALWAYS = [
    "Content-Security-Policy",
    "X-Content-Type-Options",
    "X-Frame-Options",
    "Referrer-Policy",
    "Permissions-Policy",
    "Cross-Origin-Opener-Policy",
    "Cross-Origin-Resource-Policy",
]


def _assert_always_on_headers(response):
    for header in HEADERS_ALWAYS:
        assert header in response.headers


def test_headers_on_landing_page_in_development(client):
    response = client.get("/")
    _assert_always_on_headers(response)
    assert "Strict-Transport-Security" not in response.headers
    assert "upgrade-insecure-requests" not in response.headers["Content-Security-Policy"]


def test_headers_on_health(client):
    response = client.get("/health")
    _assert_always_on_headers(response)


def test_headers_on_404(client):
    response = client.get("/this-does-not-exist")
    assert response.status_code == 404
    _assert_always_on_headers(response)


def test_all_8_headers_in_production(app):
    app.config["ENV"] = "production"
    app.config["DEBUG"] = False
    client = app.test_client()
    response = client.get("/")
    _assert_always_on_headers(response)
    assert response.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"
    assert "upgrade-insecure-requests" in response.headers["Content-Security-Policy"]


def test_admin_guard_redirects_when_logged_out(client):
    response = client.get("/admin", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].startswith("/login")
    assert "next=/admin" in response.headers["Location"]


def test_admin_guard_403_for_non_admin(client, make_user):
    user_id = make_user(email="customer@example.com", role="customer")
    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["role"] = "customer"
        session["session_version"] = 0
    response = client.get("/admin")
    assert response.status_code == 403


def test_admin_guard_allows_admin(client, make_user):
    admin_id = make_user(email="admin@example.com", role="admin")
    with client.session_transaction() as session:
        session["user_id"] = admin_id
        session["role"] = "admin"
        session["session_version"] = 0
    response = client.get("/admin")
    assert response.status_code == 200


def test_api_admin_live_is_guarded(client):
    response = client.get("/api/admin/live", follow_redirects=False)
    assert response.status_code == 302


# --- docs/SECURITY.md test checklist -----------------------------------------


def test_checklist_1_five_wrong_passwords_locks_account(client, make_user, app):
    make_user(email="locktest@example.com", password="StrongPass1")
    for _ in range(4):
        response = client.post("/login", data={"email": "locktest@example.com", "password": "bad"})
        assert response.status_code == 400
        assert b"Email or password is not correct." in response.data

    fifth = client.post("/login", data={"email": "locktest@example.com", "password": "bad"})
    assert fifth.status_code == 429
    assert b"Too many tries. Try again in 10 minutes." in fifth.data

    with app.app_context():
        locked_user = user_queries.find_by_email(get_db(), "locktest@example.com")
    assert locked_user["locked_until"] is not None
    assert locked_user["failed_attempts"] == 5


def test_wrong_email_and_wrong_password_share_one_message(client, make_user):
    make_user(email="realuser@example.com", password="StrongPass1")
    wrong_password = client.post(
        "/login", data={"email": "realuser@example.com", "password": "nope"}
    )
    wrong_email = client.post("/login", data={"email": "nobody@example.com", "password": "nope"})
    assert wrong_password.status_code == wrong_email.status_code == 400
    # Same wording either way (the CSRF token embedded in the page differs
    # per request, so compare the error message, not the raw page bytes).
    message = b"Email or password is not correct."
    assert message in wrong_password.data
    assert message in wrong_email.data


def test_checklist_2_rate_limit_eleven_logins_per_minute(tmp_path):
    # Flask-Limiter reads RATELIMIT_ENABLED once, at init_app time, so it must
    # be set before create_app() rather than toggled on the shared fixture app.
    from app import create_app
    from app.db import get_db, init_db

    rate_limited_app = create_app(
        {
            "TESTING": True,
            "DATABASE_PATH": str(tmp_path / "ratelimit.db"),
            "WTF_CSRF_ENABLED": False,
            # Explicit, because Flask-Limiter's `enabled` flag lives on our
            # shared global Limiter singleton: config.setdefault() means an
            # earlier test's False would otherwise leak forward as the
            # default for any app that doesn't set this key itself.
            "RATELIMIT_ENABLED": True,
        }
    )
    with rate_limited_app.app_context():
        init_db()
        get_db().commit()
    client = rate_limited_app.test_client()

    responses = [
        client.post("/login", data={"email": "nobody@example.com", "password": "wrong"})
        for _ in range(11)
    ]
    assert [r.status_code for r in responses[:10]] == [400] * 10
    assert responses[10].status_code == 429
    assert b"Too many tries." in responses[10].data
    assert b"Wait a minute and try again." in responses[10].data


def test_checklist_5_logged_out_visiting_app_redirects_then_returns(client, make_user):
    response = client.get("/app", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"] == "/login?next=/app"

    make_user(email="cust@example.com", password="StrongPass1", role="customer")
    login_response = client.post(
        "/login",
        data={"email": "cust@example.com", "password": "StrongPass1", "next": "/app"},
        follow_redirects=False,
    )
    assert login_response.status_code == 302
    assert login_response.headers["Location"] == "/app"


def test_checklist_6_next_to_evil_domain_is_ignored(client, make_user):
    make_user(email="cust@example.com", password="StrongPass1", role="customer")
    response = client.post(
        "/login",
        data={"email": "cust@example.com", "password": "StrongPass1", "next": "https://evil.com"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["Location"] == "/app"


def test_checklist_7_post_without_csrf_token_is_400(csrf_app):
    client = csrf_app.test_client()
    response = client.post("/login", data={"email": "x@example.com", "password": "x"})
    assert response.status_code == 400
    assert b"This form expired." in response.data
    assert b"Reload the page and try again." in response.data


def test_checklist_8_role_posted_on_register_is_ignored(client, app):
    client.post(
        "/register",
        data={
            "full_name": "Someone",
            "email": "someone@example.com",
            "phone": "0300-1112222",
            "password": "StrongPass1",
            "confirm_password": "StrongPass1",
            "role": "admin",
        },
    )
    with app.app_context():
        user = user_queries.find_by_email(get_db(), "someone@example.com")
    assert user["role"] == "customer"


def test_checklist_17_idle_31_minutes_logs_out_with_message(client, make_user):
    make_user(email="cust@example.com", password="StrongPass1", role="customer")
    client.post("/login", data={"email": "cust@example.com", "password": "StrongPass1"})

    stale = (datetime.now(UTC) - timedelta(minutes=31)).isoformat()
    with client.session_transaction() as session:
        session["last_seen"] = stale

    response = client.get("/app", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"] == "/login?next=/app"

    login_page = client.get(response.headers["Location"])
    assert b"You were logged out after 30 minutes of no activity." in login_page.data


def test_checklist_17_blocked_customer_logged_out_on_next_click(client, app, make_user):
    user_id = make_user(email="cust@example.com", password="StrongPass1", role="customer")
    client.post("/login", data={"email": "cust@example.com", "password": "StrongPass1"})

    with app.app_context():
        db = get_db()
        db.execute("UPDATE users SET is_active = 0 WHERE user_id = ?", (user_id,))
        db.commit()

    response = client.get("/app", follow_redirects=False)
    assert response.status_code == 302
    with client.session_transaction() as session:
        assert "user_id" not in session


# --- 6 changes from the C2 plan review ----------------------------------------


def test_change1_absolute_12h_logs_out_even_with_fresh_last_seen(client, make_user):
    make_user(email="cust@example.com", password="StrongPass1", role="customer")
    client.post("/login", data={"email": "cust@example.com", "password": "StrongPass1"})

    stale_login = (datetime.now(UTC) - timedelta(hours=12, minutes=1)).isoformat()
    with client.session_transaction() as session:
        session["login_at"] = stale_login
        session["last_seen"] = datetime.now(UTC).isoformat()  # looks fresh

    response = client.get("/app", follow_redirects=False)
    assert response.status_code == 302
    with client.session_transaction() as session:
        assert "user_id" not in session


def test_change2_polling_does_not_reset_idle_timer_but_still_expires(client, make_user):
    make_user(email="admin@example.com", password="StrongPass1", role="admin")
    client.post("/login", data={"email": "admin@example.com", "password": "StrongPass1"})

    almost_stale = (datetime.now(UTC) - timedelta(minutes=29)).isoformat()
    with client.session_transaction() as session:
        session["last_seen"] = almost_stale

    response = client.get("/api/admin/live")
    assert response.status_code == 200
    with client.session_transaction() as session:
        assert session["last_seen"] == almost_stale  # polling did not refresh it

    too_stale = (datetime.now(UTC) - timedelta(minutes=31)).isoformat()
    with client.session_transaction() as session:
        session["last_seen"] = too_stale

    response = client.get("/api/admin/live")
    assert response.status_code == 302  # idle-expired, even though this was only polling
    with client.session_transaction() as session:
        assert "user_id" not in session


def test_change3_trusted_proxy_count_defaults_to_zero(app):
    assert app.config["TRUSTED_PROXY_COUNT"] == 0


def test_change3_proxy_fix_only_applied_when_trusted_proxy_count_is_one(tmp_path):
    from werkzeug.middleware.proxy_fix import ProxyFix

    from app import create_app

    app_without = create_app(
        {
            "DATABASE_PATH": str(tmp_path / "a.db"),
            "RATELIMIT_ENABLED": False,
            "TRUSTED_PROXY_COUNT": 0,
        }
    )
    assert not isinstance(app_without.wsgi_app, ProxyFix)

    app_with = create_app(
        {
            "DATABASE_PATH": str(tmp_path / "b.db"),
            "RATELIMIT_ENABLED": False,
            "TRUSTED_PROXY_COUNT": 1,
        }
    )
    assert isinstance(app_with.wsgi_app, ProxyFix)


def test_change5_logout_invalidates_other_devices_with_copied_cookie(client, make_user):
    user_id = make_user(email="cust@example.com", password="StrongPass1", role="customer")
    client.post("/login", data={"email": "cust@example.com", "password": "StrongPass1"})
    with client.session_transaction() as session:
        old_version = session["session_version"]

    client.post("/logout")

    # A second device with a copied, pre-logout cookie (same stale session_version).
    now = datetime.now(UTC).isoformat()
    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["role"] = "customer"
        session["session_version"] = old_version
        session["login_at"] = now
        session["last_seen"] = now

    response = client.get("/app", follow_redirects=False)
    assert response.status_code == 302
    with client.session_transaction() as session:
        assert "user_id" not in session


@pytest.mark.parametrize(
    "value",
    ["https://evil.com", "//evil.com", "/\\evil.com", None, "", "evil.com"],
)
def test_change6_is_safe_next_rejects_unsafe_values(value):
    assert is_safe_next(value) is False


@pytest.mark.parametrize("value", ["/app", "/admin/orders", "/"])
def test_change6_is_safe_next_accepts_same_site_paths(value):
    assert is_safe_next(value) is True


@pytest.mark.parametrize("evil_next", ["https://evil.com", "//evil.com", "/\\evil.com"])
def test_change6_login_ignores_unsafe_next_and_uses_dashboard(client, make_user, evil_next):
    make_user(email="cust@example.com", password="StrongPass1", role="customer")
    response = client.post(
        "/login",
        data={"email": "cust@example.com", "password": "StrongPass1", "next": evil_next},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["Location"] == "/app"
