"""App factory: wires config, database, security, caching and blueprints."""

from flask import Flask, jsonify, render_template
from flask_compress import Compress
from werkzeug.middleware.proxy_fix import ProxyFix

from app import cli, db, security
from app.admin import bp as admin_bp
from app.api import bp as api_bp
from app.auth import bp as auth_bp
from app.caching import init_caching
from app.config import build_config
from app.customer import bp as customer_bp
from app.errors import init_errors


def create_app(config_overrides=None):
    app = Flask(__name__)
    app.config.from_mapping(build_config())
    if config_overrides:
        app.config.from_mapping(config_overrides)

    if app.config["TRUSTED_PROXY_COUNT"] == 1:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

    db.init_app(app)
    security.init_security(app)
    init_caching(app)
    init_errors(app)
    cli.init_app(app)
    Compress(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    @app.get("/")
    def landing():
        return render_template("landing.html")

    @app.get("/health")
    def health():
        try:
            db.get_db().execute("SELECT 1")
        except Exception:
            return jsonify(status="error"), 503
        return jsonify(status="ok")

    return app
