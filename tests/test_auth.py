from app.auth import _DUMMY_PASSWORD_HASH, _verify_password
from app.db import get_db
from app.queries import users as user_queries

VALID_PASSWORD = "StrongPass1"


def test_verify_password_hashes_a_dummy_value_when_no_user_found(monkeypatch):
    """Wrong-email and wrong-password must cost the same time: no early return."""
    calls = []
    import app.auth as auth_module

    original = auth_module.check_password_hash

    def spy(password_hash, password):
        calls.append(password_hash)
        return original(password_hash, password)

    monkeypatch.setattr(auth_module, "check_password_hash", spy)

    assert _verify_password(None, "whatever") is False
    assert calls == [_DUMMY_PASSWORD_HASH]


def test_verify_password_rejects_overlong_password_without_hashing(monkeypatch):
    import app.auth as auth_module

    calls = []
    monkeypatch.setattr(auth_module, "check_password_hash", lambda *a: calls.append(a) or True)
    assert _verify_password(None, "x" * 129) is False
    assert calls == []


def _register_payload(**overrides):
    payload = {
        "full_name": "Ayesha Khan",
        "email": "ayesha@example.com",
        "phone": "0300-1234567",
        "password": VALID_PASSWORD,
        "confirm_password": VALID_PASSWORD,
    }
    payload.update(overrides)
    return payload


def test_register_role_is_always_customer_even_if_posted(client, app):
    response = client.post("/register", data=_register_payload(role="admin"))
    assert response.status_code == 302
    with app.app_context():
        user = user_queries.find_by_email(get_db(), "ayesha@example.com")
    assert user["role"] == "customer"


def test_register_logs_in_and_redirects_to_customer_home(client):
    response = client.post("/register", data=_register_payload(), follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"] == "/app"
    with client.session_transaction() as session:
        assert session["role"] == "customer"


def test_register_phone_is_normalized_before_saving(client, app):
    client.post("/register", data=_register_payload(phone="0300-7654321"))
    with app.app_context():
        user = user_queries.find_by_phone(get_db(), "03007654321")
    assert user is not None


def test_register_requires_full_name(client):
    response = client.post("/register", data=_register_payload(full_name=" "))
    assert response.status_code == 400
    assert b"Enter your full name" in response.data


def test_register_requires_valid_email(client):
    response = client.post("/register", data=_register_payload(email="not-an-email"))
    assert response.status_code == 400
    assert b"Enter a valid email" in response.data


def test_register_requires_valid_phone(client):
    response = client.post("/register", data=_register_payload(phone="12345"))
    assert response.status_code == 400
    assert b"Enter a valid mobile number like 0300-1234567" in response.data


def test_register_passwords_must_match(client):
    response = client.post("/register", data=_register_payload(confirm_password="Different1"))
    assert response.status_code == 400
    assert b"Passwords do not match" in response.data


def test_register_password_too_short(client):
    response = client.post(
        "/register", data=_register_payload(password="short", confirm_password="short")
    )
    assert response.status_code == 400
    assert b"at least 8 characters" in response.data


def test_register_password_too_long(client):
    huge = "A1" * 100  # 200 chars
    response = client.post(
        "/register", data=_register_payload(password=huge, confirm_password=huge)
    )
    assert response.status_code == 400
    assert b"128 characters or fewer" in response.data


def test_register_password_cannot_be_common(client):
    response = client.post(
        "/register", data=_register_payload(password="password", confirm_password="password")
    )
    assert response.status_code == 400
    assert b"less common password" in response.data


def test_register_password_cannot_equal_email(client):
    response = client.post(
        "/register",
        data=_register_payload(
            email="same@example.com",
            password="same@example.com",
            confirm_password="same@example.com",
        ),
    )
    assert response.status_code == 400
    assert b"cannot be the same as your email" in response.data


def test_register_duplicate_email_is_rejected(client, make_user):
    make_user(email="ayesha@example.com", phone="03009998888")
    response = client.post("/register", data=_register_payload())
    assert response.status_code == 400
    assert b"already registered" in response.data


def test_register_duplicate_phone_is_rejected(client, make_user):
    make_user(email="someone-else@example.com", phone="03001234567")
    response = client.post("/register", data=_register_payload(phone="0300-1234567"))
    assert response.status_code == 400
    assert b"This phone number is already registered." in response.data


def test_login_requires_email_and_password(client):
    response = client.post("/login", data={"email": "", "password": ""})
    assert response.status_code == 400
    assert b"Enter your email" in response.data
    assert b"Enter your password" in response.data


def test_login_success_redirects_customer_to_app(client, make_user):
    make_user(email="cust@example.com", password=VALID_PASSWORD, role="customer")
    response = client.post(
        "/login",
        data={"email": "cust@example.com", "password": VALID_PASSWORD},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["Location"] == "/app"


def test_login_success_redirects_admin_to_admin(client, make_user):
    make_user(email="admin@example.com", password=VALID_PASSWORD, role="admin")
    response = client.post(
        "/login",
        data={"email": "admin@example.com", "password": VALID_PASSWORD},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["Location"] == "/admin"


def test_login_already_authenticated_redirects_to_dashboard(client, make_user):
    make_user(email="cust@example.com", password=VALID_PASSWORD, role="customer")
    client.post("/login", data={"email": "cust@example.com", "password": VALID_PASSWORD})
    response = client.get("/login", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"] == "/app"


def test_login_blocked_account_shown_only_after_correct_password(client, make_user):
    make_user(email="blocked@example.com", password=VALID_PASSWORD, is_active=0)
    wrong = client.post("/login", data={"email": "blocked@example.com", "password": "WrongPass1"})
    assert wrong.status_code == 400
    assert b"Email or password is not correct." in wrong.data
    assert b"blocked" not in wrong.data

    correct = client.post(
        "/login", data={"email": "blocked@example.com", "password": VALID_PASSWORD}
    )
    assert correct.status_code == 403
    assert b"This account is blocked. Please contact AJORA support." in correct.data


def test_logout_confirm_dialog_posts_the_real_logout_form(client, make_user):
    """Pop-up 7 (docs/FIGMA.md P7): the dialog's Log out button targets
    #logout-form by id instead of JS submitting it, so the no-JS fallback
    (a plain POST from the page's own logout button) and the confirmed path
    both end up posting the exact same form."""
    make_user(email="cust@example.com", password=VALID_PASSWORD)
    client.post("/login", data={"email": "cust@example.com", "password": VALID_PASSWORD})
    body = client.get("/app").data.decode()

    assert 'id="logout-form"' in body
    assert 'data-action="open-logout"' in body
    assert "Log out of AJORA?" in body
    assert 'form="logout-form"' in body
    assert 'data-action="confirm-logout"' in body


def test_logout_confirm_dialog_present_for_admin_too(client, app, make_user):
    make_user(email="admin@example.com", password=VALID_PASSWORD, role="admin")
    client.post("/login", data={"email": "admin@example.com", "password": VALID_PASSWORD})
    body = client.get("/admin").data.decode()

    assert 'id="logout-form"' in body
    assert 'data-action="open-logout"' in body
    assert 'form="logout-form"' in body


def test_logout_bumps_session_version(client, app, make_user):
    user_id = make_user(email="cust@example.com", password=VALID_PASSWORD)
    client.post("/login", data={"email": "cust@example.com", "password": VALID_PASSWORD})
    with app.app_context():
        before = user_queries.find_by_id(get_db(), user_id)["session_version"]
    client.post("/logout")
    with app.app_context():
        after = user_queries.find_by_id(get_db(), user_id)["session_version"]
    assert after == before + 1
