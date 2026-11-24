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
