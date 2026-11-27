"""Visual check tool (dev only, not part of the app).

Runs AJORA against a freshly seeded temporary database and uses Playwright to
save a screenshot of each given path at mobile (390x844), tablet (834x1194)
and laptop (1440x900) into tools/screenshots/ (git-ignored). Compare these by
eye against the matching Figma screenshot (node IDs in docs/FIGMA.md).

A path ending in "#confirm" opens Order fuel, fills in the required fields
and clicks "Review order" first, to capture the Confirm order pop-up. Paths
under /app log in as the seeded demo customer (Ali Raza) once per run.

Usage:
    python tools/screenshots.py                  # the default screen list
    python tools/screenshots.py /login /register  # just these paths
"""

import secrets
import sys
import tempfile
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright
from werkzeug.security import generate_password_hash
from werkzeug.serving import make_server

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import create_app  # noqa: E402
from app.db import get_db, init_db  # noqa: E402
from app.demo_data import seed_demo  # noqa: E402
from app.queries import users as user_queries  # noqa: E402

SIZES = [("mobile", 390, 844), ("tablet", 834, 1194), ("laptop", 1440, 900)]
OUTPUT_DIR = ROOT / "tools" / "screenshots"
DEMO_PASSWORD = "demo-pass-1234"  # noqa: S105 (throwaway local tool database, not a secret)
DEMO_EMAIL = "ali.raza@example.com"
ADMIN_EMAIL = "sana.ahmed@example.com"
JOHAR_TOWN = (31.4697, 74.2728)

DEFAULT_PATHS = [
    "/",
    "/login",
    "/register",
    "/app",
    "/app/order/fuel",
    "/app/order/fuel#confirm",
    "/app/order/emergency",
    "/app/order/emergency#confirm",
    "/app/order/generator",
    "/app/order/generator#confirm",
    "/app/order/assistance",
    "/app/order/assistance#confirm",
    "/app/orders/42/confirmed",
    "/app/orders/43/confirmed",
    "/admin",
    "/admin/orders",
    "/admin/orders?from=2020-01-01&to=2020-01-02&date=custom",
    "/admin/orders/36",  # Assigned, single stop
    "/admin/orders/36#assign",  # pop-up 2: change driver
    "/admin/orders/36#status-on-the-way",  # pop-up 3: simple status move
    "/admin/orders/36#cancel",  # pop-up 3: cancel with reason
    "/admin/orders/42",  # On the way, multi-stop route
    "/admin/orders/71",  # Pending, no driver
    "/admin/orders/71#assign",  # pop-up 2: assign a driver
    "/admin/orders/46",  # Pending + Emergency, no driver free
    "/admin/orders/46#assign",
    "/admin/orders/43",  # Pending + Call needed
    "/admin/orders/1",  # Delivered (read-only)
    "/admin/orders/7",  # Cancelled (read-only)
    "/admin/emergency",
    "/admin/customers",
    "/admin/customers/1",  # Ali Raza: pop-up 4 customer panel
    "/admin/services",
    "/admin/services#add-service",  # pop-up 5: add
    "/admin/services#edit-service-1",  # pop-up 5: edit (Petrol)
    "/admin/drivers",
    "/admin/drivers#add-driver",  # pop-up 6: add
    "/admin/drivers#edit-driver-1",  # pop-up 6: edit (Ahmed Raza)
    "/admin/drivers#remove-driver-1",  # pop-up 6: remove refused (Ahmed Raza is Busy)
    "/admin/reports",
    "/admin/reports?period=day&date=2020-01-01",  # empty period
    "/app#logout",  # pop-up 7: customer
    "/admin#logout",  # pop-up 7: admin
]


class _ServerThread(threading.Thread):
    def __init__(self, app):
        super().__init__(daemon=True)
        self.server = make_server("127.0.0.1", 0, app, threaded=True)
        self.port = self.server.server_address[1]

    def run(self):
        self.server.serve_forever()

    def stop(self):
        self.server.shutdown()


def _build_seeded_app(db_path):
    app = create_app(
        {
            "SECRET_KEY": "screenshot-tool-not-for-production",
            "DATABASE_PATH": str(db_path),
            "WTF_CSRF_ENABLED": False,
            "RATELIMIT_ENABLED": False,
        }
    )
    with app.app_context():
        init_db()
        db = get_db()
        seed_demo(db, DEMO_PASSWORD)
        admin_password = secrets.token_urlsafe(16)
        user_queries.create_user(
            db,
            "Sana Ahmed",
            ADMIN_EMAIL,
            "03004445555",
            generate_password_hash(admin_password, method="scrypt"),
            "admin",
        )
        db.commit()
    return app, admin_password


def _login(page, base_url, email=DEMO_EMAIL, password=DEMO_PASSWORD):
    page.goto(f"{base_url}/login")
    page.fill("#field-email", email)
    page.fill("#field-password", password)
    page.click("button[type=submit]")
    page.wait_for_load_state("networkidle")


def _open_fuel_confirm(page):
    page.fill("#field-address", "House 12, Block C, Johar Town")
    page.select_option("#field-area", "Johar Town")
    page.click('.order-summary [data-action="open-confirm"]')
    page.wait_for_selector("#confirm-order-dialog:not([hidden])")


def _open_emergency_confirm(page):
    page.fill("#field-note", "White Corolla near exit 4")
    page.click('.emergency-inline-submit [data-action="open-confirm"]')
    page.wait_for_selector("#confirm-order-dialog:not([hidden])")


def _open_generator_confirm(page):
    page.fill("#field-address", "Farm 7, Mauza Kot, Raiwind Road")
    page.select_option("#field-area", "Township")
    page.click('.order-summary [data-action="open-confirm"]')
    page.wait_for_selector("#confirm-order-dialog:not([hidden])")


def _open_assistance_confirm(page):
    page.fill("#field-address", "55-B Model Town, near Link Road")
    page.select_option("#field-area", "Model Town")
    page.click('.order-summary [data-action="open-confirm"]')
    page.wait_for_selector("#confirm-order-dialog:not([hidden])")


CONFIRM_HANDLERS = {
    "/app/order/fuel": _open_fuel_confirm,
    "/app/order/emergency": _open_emergency_confirm,
    "/app/order/generator": _open_generator_confirm,
    "/app/order/assistance": _open_assistance_confirm,
}


def _open_admin_dialog(page, fragment):
    """Order details (C10) pop-ups 2/3: fragment names the dialog id suffix,
    e.g. "#assign" opens #dialog-assign, "#status-on-the-way" opens
    #dialog-status-on-the-way, "#cancel" opens #dialog-cancel."""
    dialog_id = f"dialog-{fragment}"
    page.click(f'[data-dialog-open="{dialog_id}"]')
    page.wait_for_selector(f"#{dialog_id}:not([hidden])")


def _slug(path):
    name = path.strip("/").replace("/", "_").replace("#", "__") or "landing"
    for char in "?=&":
        name = name.replace(char, "_")
    return name


def _open_logout_dialog(page):
    page.click('[data-action="open-logout"]')
    page.wait_for_selector("#logout-dialog:not([hidden])")


def _capture_path(page, base_url, path):
    real_path, _, fragment = path.partition("#")
    page.goto(f"{base_url}{real_path}")
    if real_path.startswith(("/app", "/admin")):
        page.wait_for_load_state("networkidle")
    if fragment == "confirm":
        CONFIRM_HANDLERS[real_path](page)
    elif fragment == "logout":
        _open_logout_dialog(page)
    elif fragment and real_path.startswith(("/admin/orders/", "/admin/services", "/admin/drivers")):
        _open_admin_dialog(page, fragment)
    name = _slug(path)
    for size_name, width, height in SIZES:
        page.set_viewport_size({"width": width, "height": height})
        page.screenshot(path=str(OUTPUT_DIR / f"{name}--{size_name}.png"), full_page=False)


def capture(paths):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        app, admin_password = _build_seeded_app(Path(tmp) / "screenshots.db")
        server = _ServerThread(app)
        server.start()
        base_url = f"http://127.0.0.1:{server.port}"
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                latitude, longitude = JOHAR_TOWN
                context = browser.new_context(
                    geolocation={"latitude": latitude, "longitude": longitude}
                )
                context.grant_permissions(["geolocation"])
                page = context.new_page()
                # A separate browser context (its own cookie jar) for /admin
                # paths - the admin and the demo customer are two sessions,
                # and /login redirects an already logged-in session away.
                admin_context = browser.new_context()
                admin_page = admin_context.new_page()
                logged_in = False
                admin_logged_in = False
                for path in paths:
                    if path.startswith("/admin"):
                        active_page = admin_page
                        if not admin_logged_in:
                            _login(admin_page, base_url, ADMIN_EMAIL, admin_password)
                            admin_logged_in = True
                    else:
                        active_page = page
                        if path.startswith("/app") and not logged_in:
                            _login(page, base_url)
                            logged_in = True
                    _capture_path(active_page, base_url, path)
                    print(f"saved {_slug(path)}")
                browser.close()
        finally:
            server.stop()


if __name__ == "__main__":
    capture(sys.argv[1:] or DEFAULT_PATHS)
