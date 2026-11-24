import pytest

from app.config import ConfigError, build_config


def test_refuses_production_without_secret_key(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.setenv("DEBUG", "0")
    with pytest.raises(ConfigError):
        build_config()


def test_refuses_production_with_debug_on(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "a-real-secret")
    monkeypatch.setenv("DEBUG", "1")
    with pytest.raises(ConfigError):
        build_config()


def test_allows_production_with_secret_key_and_debug_off(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "a-real-secret")
    monkeypatch.setenv("DEBUG", "0")
    config = build_config()
    assert config["SECRET_KEY"] == "a-real-secret"
    assert config["SESSION_COOKIE_NAME"] == "__Host-ajora"
    assert config["SESSION_COOKIE_SECURE"] is True


def test_development_without_secret_key_gets_an_ephemeral_one(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    config = build_config()
    assert config["SECRET_KEY"]
    assert config["SESSION_COOKIE_NAME"] == "session"
    assert config["SESSION_COOKIE_SECURE"] is False
