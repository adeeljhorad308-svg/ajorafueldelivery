# AJORA

AI-Based Smart Fuel Delivery & Vehicle Assistance Platform for Pakistan.
Final Year Project, BS Software Engineering, University of Lahore (2026).
Team: Muhammad Adeel, Arwa Israr · Advisor: Ms. Sana Munir

Customers in Lahore order petrol, diesel, emergency fuel, generator or machinery fuel, and vehicle help (engine oil, battery, tyre, car wash). Smart dispatch picks the nearest free driver with a priority queue, Haversine distance and a time-of-day ETA. Admins manage orders, emergencies, customers, services, drivers and reports.

## Stack

Python 3.12 · Flask 3 · SQLite (WAL) · Jinja2 · HTML5 · CSS3 · plain JavaScript

## Run it on Windows

```
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
copy .env.example .env
```

Put a new key in `.env` (`python -c "import secrets; print(secrets.token_hex(32))"`) and
set `DEMO_PASSWORD` (the password for every seeded demo customer), then:

```
flask --app wsgi init-db
flask --app wsgi seed
flask --app wsgi create-admin
flask --app wsgi run --debug
```

Open http://127.0.0.1:5000

## 30% checkpoint demo

```
flask --app wsgi init-db
flask --app wsgi seed
flask --app wsgi run --debug
```

Demo logins (password is whatever you set as `DEMO_PASSWORD` in `.env`):

- `ali.raza@example.com` – has an order already On the way and one waiting on a call
- `sana.iqbal@example.com` / `bilal.khan@example.com` – each has an open emergency request

5-step demo:

1. Log in as `ali.raza@example.com`, place a normal Order fuel order.
2. Open a second browser/incognito window, log in as `sana.iqbal@example.com`, send an Emergency
   fuel request.
3. Place another normal order for Ali Raza right after - watch the emergency get a driver first
   even though it was placed later (smart dispatch's priority queue).
4. In a terminal: `flask --app wsgi demo-advance ORD-0042` (or whichever order number you placed)
   moves it one step forward (Pending -> Assigned -> On the way -> Delivered), with a driver
   assigned/freed and a tracking row added, same as an admin action would.
5. Switch back to the customer's Track order page (no admin side yet) and watch the status, ETA
   and progress steps update within 30 seconds, with no reload.

## Checks

```
pytest -q
ruff check .
pip-audit -r requirements.txt
```

## Project documents

- `CLAUDE.md` – coding rules
- `docs/SPEC.md` – every screen and how it reacts
- `docs/SECURITY.md` – security controls and the 19-item test list
- `docs/PERFORMANCE.md` – speed targets and load test
- `docs/FIGMA.md` – Figma node IDs for every screen
