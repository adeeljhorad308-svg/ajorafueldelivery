# AJORA – speed and many users

## Targets

| Measure | Target | How to check |
| --- | --- | --- |
| Page ready on a 4G phone | under 2 s | Lighthouse mobile, DevTools "Fast 4G" |
| Server response p95 | under 500 ms normal, under 1 s at 200 users | Locust |
| Smart dispatch | under 1 s with 50 drivers | pytest timing test |
| Load test | 200 users, 20 orders/min, 0 errors, no "database is locked" | Locust |
| Lighthouse | Performance 90+, Accessibility 95+, Best practices 95+ | Chrome DevTools |
| Page weight (compressed) | HTML+CSS+JS < 150 KB, fonts < 100 KB, icons < 15 KB, images < 200 KB | DevTools Network |

## How

- Server-rendered pages; one small JS module per page; Chart.js only on Reports.
- Flask-Compress on HTML, CSS, JS, JSON.
- Static files: versioned URL (`?v=<hash>`), `Cache-Control: public, max-age=31536000, immutable`. Logged-in pages and API: `no-store`.
- Fonts: Inter 400/500/600/700 and JetBrains Mono 500 only, woff2, Latin subset, `font-display: swap`, preload the main one.
- Images: SVG for logo and icons; photos WebP with `width`/`height` and `loading="lazy"` below the fold.
- SQL: indexes on filtered/sorted columns, `LIMIT` on lists (10 customer, 20 admin), no `SELECT *`, no query in a loop, one query per report card. Price list cached in memory 60 s, cleared on price change.
- Polling: customer 30 s, admin 15 s, paused when `document.hidden`, back-off to 60 s after 3 errors; JSON under 2 KB.

## Many users with SQLite

- `PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000; PRAGMA synchronous=NORMAL; PRAGMA foreign_keys=ON;` on every connection.
- One connection per request, closed in `teardown_appcontext`.
- Order + dispatch + tracking row in one short `BEGIN IMMEDIATE` transaction.
- Several workers: Gunicorn `-w 4` on Linux, Waitress `--threads=16` on Windows.
- Lockout counter in the database (exact across workers). Rate limits: `memory://` for one worker, Redis for several.

## Indexes (minimum)

```
orders(user_id, created_at)
orders(status)
orders(is_emergency, status)
orders(order_key) UNIQUE
assignments(order_id) UNIQUE
assignments(driver_id)
drivers(status)
tracking(order_id)
users(email) UNIQUE
users(phone) UNIQUE
```

## Load test

```
pip install -r requirements-dev.txt
flask --app wsgi seed
waitress-serve --threads=16 --call app:create_app
locust -f loadtest/locustfile.py --host http://127.0.0.1:8080 -u 200 -r 20 -t 10m --headless --csv loadtest/result
```

User mix: 70% browse and track, 20% place orders (about 20 per minute), 10% admin. Pass: Failures 0, 95% under 1000 ms. If slow: `EXPLAIN QUERY PLAN` on the slowest route and add the missing index.

## Growth path

1. Now: Flask + SQLite (WAL) + 1–4 workers, one-city pilot.
2. More traffic: Redis for rate limits and cache; Gunicorn workers = 2 × CPU + 1 behind Nginx.
3. Many cities: PostgreSQL (plain SQL in `app/queries` keeps the move small), driver app with live GPS, ML ETA model trained on saved predicted vs actual times (Release 3).
