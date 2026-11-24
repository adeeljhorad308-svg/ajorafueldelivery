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

import sys
import tempfile
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import create_app  # noqa: E402
from app.db import get_db, init_db  # noqa: E402
from app.demo_data import seed_demo  # noqa: E402

SIZES = [("mobile", 390, 844), ("tablet", 834, 1194), ("laptop", 1440, 900)]
OUTPUT_DIR = ROOT / "tools" / "screenshots"
DEMO_PASSWORD = "demo-pass-1234"  # noqa: S105 (throwaway local tool database, not a secret)
DEMO_EMAIL = "ali.raza@example.com"
JOHAR_TOWN = (31.4697, 74.2728)

DEFAULT_PATHS = [
    "/",
    "/login",
    "/register",
    "/app",
    "/app/order/fuel",
    "/app/order/fuel#confirm",
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
        seed_demo(get_db(), DEMO_PASSWORD)
        get_db().commit()
    return app


def _login(page, base_url):
    page.goto(f"{base_url}/login")
    page.fill("#field-email", DEMO_EMAIL)
    page.fill("#field-password", DEMO_PASSWORD)
    page.click("button[type=submit]")
    page.wait_for_load_state("networkidle")


def _open_confirm_dialog(page):
    page.fill("#field-address", "House 12, Block C, Johar Town")
    page.select_option("#field-area", "Johar Town")
    page.click('.order-summary [data-action="open-confirm"]')
    page.wait_for_selector("#confirm-order-dialog:not([hidden])")


def _slug(path):
    return path.strip("/").replace("/", "_").replace("#", "__") or "landing"


def _capture_path(page, base_url, path):
    real_path, _, fragment = path.partition("#")
    page.goto(f"{base_url}{real_path}")
    if real_path.startswith("/app"):
        page.wait_for_load_state("networkidle")
    if fragment == "confirm":
        _open_confirm_dialog(page)
    name = _slug(path)
    for size_name, width, height in SIZES:
        page.set_viewport_size({"width": width, "height": height})
        page.screenshot(path=str(OUTPUT_DIR / f"{name}--{size_name}.png"), full_page=False)


def capture(paths):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        app = _build_seeded_app(Path(tmp) / "screenshots.db")
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
                logged_in = False
                for path in paths:
                    if path.startswith("/app") and not logged_in:
                        _login(page, base_url)
                        logged_in = True
                    _capture_path(page, base_url, path)
                    print(f"saved {_slug(path)}")
                browser.close()
        finally:
            server.stop()


if __name__ == "__main__":
    capture(sys.argv[1:] or DEFAULT_PATHS)
