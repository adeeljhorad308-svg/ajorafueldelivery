# AJORA – rules for Claude Code

AJORA is a Final Year Project (University of Lahore, BS Software Engineering) by Muhammad Adeel and Arwa Israr, advisor Ms. Sana Munir: an AI-based smart fuel delivery and vehicle assistance web platform for Lahore, Pakistan. Customers order fuel and road help; an admin runs orders, drivers and services; smart dispatch picks the nearest free driver and predicts the arrival time.

Read this file, then `docs/SPEC.md`, `docs/SECURITY.md`, `docs/PERFORMANCE.md` and `docs/FIGMA.md` at the start of every session. If anything here conflicts with a prompt, stop and ask.

## Stack (do not change)

- Python 3.12, Flask 3 with blueprints `auth`, `customer`, `admin`, `api`; app factory `create_app()` in `app/__init__.py`.
- SQLite through the built-in `sqlite3` module. No ORM. SQL lives only in `app/queries/*.py`, always with `?` parameters.
- Jinja2 templates, HTML5, CSS3 (tokens in `static/css/tokens.css`), plain JavaScript ES modules. No React, Tailwind, Bootstrap, jQuery, or build step.
- Libraries allowed: exactly those in `requirements.txt` and `requirements-dev.txt`. Ask before adding anything.
- No CDN. Fonts (Inter, JetBrains Mono), icons (inline SVG sprite) and Chart.js are self-hosted in `app/static`.
- Production: Gunicorn on Linux (or PythonAnywhere's own server). Local Windows load test: Waitress.

## Design source

- Figma file key `M95uPMv61dMZF0YLEU2DJV` ("AJORA – Design"). Read frames read-only with the Figma MCP using node IDs from `docs/FIGMA.md`. Never edit the Figma file.
- Rebuild designs with our own HTML/CSS; never paste generated React/Tailwind code.
- Breakpoints: mobile up to 599 px (frame 390), tablet 600–1023 px (frame 834), laptop 1024 px and up (frame 1440, content max 1200 px). Mobile-first CSS.

## Design gate (never skip)
- Before building any screen, fetch its node IDs (listed in docs/FIGMA.md) from https://www.figma.com/design/M95uPMv61dMZF0YLEU2DJV/AJORA-%E2%80%93-Design with the Figma MCP, read-only.
- If the MCP is not connected or any node is missing: stop and report. Never guess a layout or use placeholder UI.
- Read design tokens with get_variable_defs on 16:827 (Component overview), not 15:827.
- After building, compare with the Figma screenshot at 390, 834 and 1440 px and report differences.
- Customer nav: bottom tabs on mobile/tablet, top bar from 1024 px; order forms on mobile use a fixed action bar. Admin nav: 240 px sidebar (laptop), 72 px icon rail (tablet), top bar + menu (mobile).
- Formats: money `PKR 5,040` in JetBrains Mono · dates `05 Oct 2026, 7:40 pm` · orders `ORD-0042` · phones `0300-1234567` (stored as `03001234567`).
- Every screen needs all its states from `docs/SPEC.md`: loading skeleton (after 300 ms), empty, error, success, and the special states in `docs/FIGMA.md`.
- Seed data must match the "Seed data" section of `docs/FIGMA.md`.

## Business rules

- Fuel order: 5–100 L. Emergency: max 10 L and only one open emergency per customer. Generator/machinery: 20–500 L; above 200 L sets `call_confirmed = 0` and waits until the admin marks the call done.
- Car wash at least 2 hours ahead. Any delivery time within the next 7 days; slots 8 am–8 pm.
- Status flow: Pending → Assigned → On the way → Delivered. Assigned may go back to Pending. Cancel only from Pending or Assigned, by the admin, with a reason. Every change adds a tracking row. Customers do not cancel in version 1.
- Price and total always come from the database, never from the request. If the price changed since the page loaded, show the "price updated" state instead of placing the order.
- One-time `order_key` (hidden field, UNIQUE in the database) so a double tap makes one order.
- Only active services are shown to customers.
- Driver becomes Busy on assign and Available after Delivered or Cancelled; on Delivered the driver's location becomes the customer's location. A driver with an open order cannot be removed.

## Smart dispatch (`app/dispatch.py`, no Flask imports)

- Priority queue with `heapq`: emergency priority 2, normal 1, then oldest first.
- Only Available drivers. Distance by Haversine, R = 6371 km.
- ETA minutes = distance / speed × 60 + 5. Speed 20 km/h at 07–10 and 17–20, 40 km/h at 22–06, otherwise 30 km/h. Test: 6 km at 30 km/h → 17 min.
- Missing customer location → centre of the chosen area.
- Nearest-neighbour order for a driver's open stops.
- "As soon as possible" orders are assigned automatically in the same transaction as the order. Scheduled orders and above-200 L orders wait for the admin. No free driver → order stays Pending and the admin sees an alert.
- Save distance, predicted ETA, assigned/delivered times so a machine-learning ETA model can be trained in Release 3.

## Security (never skip)

- Deny by default. Admin blueprint guarded in `before_request`. Customer queries always include `AND user_id = ?` with the session user id; another user's order → 404.
- Role is never read from a form. Admins are created only with `flask create-admin` in a terminal.
- Every POST has a CSRF token (fetch sends `X-CSRFToken`). GET never changes data. POST → redirect → GET.
- No inline `<script>`, no `on...=` attributes, no `style=""`, no `|safe`, no `innerHTML` with data. Strict CSP from `docs/SECURITY.md`.
- Passwords: Werkzeug scrypt hash. 5 wrong tries → locked 10 minutes (counter in the database). Same message for wrong email and wrong password.
- Session: cleared on login, cookie `__Host-ajora` in production, HttpOnly, Secure, SameSite=Lax; idle 30 min, absolute 12 h; `is_active` and `session_version` checked on every request.
- Rate limits (Flask-Limiter): login 10/min and 50/hour per IP, register 5/hour, orders 10 per 10 min per user.
- 8 security headers set once in `security.py`. Secrets only from `.env`. App refuses to start in production without `SECRET_KEY` or with DEBUG on.
- Multi-step writes in one transaction. Validate every input for type, length and range on the server.
- Log security events to `logs/security.log` (rotating). Never log passwords, tokens or full session cookies.

## Speed

- Per page (first visit, compressed): HTML + CSS + JS under 150 KB, fonts under 100 KB, icons under 15 KB, images under 200 KB.
- Targets: page ready under 2 s on 4G, p95 under 500 ms, dispatch under 1 s, Lighthouse 90+ / 95+ / 95+.
- SQLite: `journal_mode=WAL`, `busy_timeout=5000`, `foreign_keys=ON`, `synchronous=NORMAL`; one connection per request; short transactions; indexes on every filtered/sorted column; `LIMIT` on every list; no query inside a loop.
- Static files versioned and cached 1 year; logged-in pages and API answers `Cache-Control: no-store`. Flask-Compress on.
- Polling: customer every 30 s, admin every 15 s, paused when the tab is hidden, back-off after errors. Price list cached 60 s.
- Chart.js only on the Reports page.

## Clean code

- No unused files, functions, imports or CSS classes; no commented-out code, `print`, `console.log` or TODO.
- Names say the job: `place_order()`, `find_nearest_driver()`, `.order-card__eta` (BEM for CSS).
- Functions under about 30 lines, files under about 300. One helper per job.
- Comments explain why, not what. One short docstring per module.
- Real words from `docs/SPEC.md` only; no filler text.
- Ruff formats and checks Python; `.editorconfig` sets 2 spaces for HTML, CSS, JS and 4 for Python.
- Every session ends with: cleanup pass, `ruff check --fix`, `ruff format`, `pytest`, then a one-line conventional commit message.

## Commands

```
flask --app wsgi run --debug        # local only
flask --app wsgi init-db            # create tables (drops old data)
flask --app wsgi seed               # demo data from docs/FIGMA.md
flask --app wsgi create-admin       # asks email and password in the terminal
flask --app wsgi backup             # dated copy in instance/backups, keeps 7 days
pytest -q
ruff check . && ruff format .
pip-audit -r requirements.txt
```
