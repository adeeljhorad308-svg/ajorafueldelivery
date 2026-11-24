# AJORA – security rules

Built against the OWASP Top 10 (2025). Every control below must exist in code and have a test in `tests/test_security.py` or the related test file.

## Controls by risk

| OWASP 2025 | Risk in AJORA | Control | Where |
| --- | --- | --- | --- |
| A01 Broken access control | Customer opens another's order or admin pages | Deny by default; admin `before_request` guard; every customer query has `AND user_id = ?`; other user's order → 404; role never read from a form | `security.py`, `queries/*` |
| A02 Security misconfiguration | Debug page, missing headers | Refuse to start with DEBUG on or no `SECRET_KEY` in production; 8 headers on every response; custom error pages | `config.py`, `security.py` |
| A03 Supply chain | Vulnerable library | Pinned versions, `pip-audit` before every deploy, Dependabot, no CDN | `requirements.txt` |
| A04 Cryptographic failures | Stolen passwords or cookies | Werkzeug scrypt hashes; HTTPS + HSTS; Secure cookies; secrets only in `.env` | `auth/`, `.env` |
| A05 Injection | SQL injection, XSS | `?` parameters only; Jinja auto-escape, no `\|safe`; JS uses `textContent`; strict CSP | `queries/*`, templates, JS |
| A06 Insecure design | Rules bypassed by editing the form | Server re-checks every limit; price from DB; allowed status moves only; one-time order key | routes, `queries/orders.py` |
| A07 Authentication failures | Guessing, stolen session | 5 tries → 10 min lock (in DB); per-IP limits; same error message; session cleared on login; idle 30 min / absolute 12 h; `session_version` | `auth/`, `security.py` |
| A08 Integrity failures | Forged posts | CSRF on every POST and `X-CSRFToken` for fetch; GET never changes data | Flask-WTF |
| A09 Logging and alerting failures | Attack unnoticed | `logs/security.log`: logins, lockouts, blocks, 403, CSRF fails, 429; never secrets; Security card on dashboard | `security.py` |
| A10 Mishandling exceptional conditions | Half-saved data, crashes | Transactions with rollback; validate type/length/range; 400/403/404/429/500 pages; `busy_timeout` | `db.py`, forms |

## Settings

```
SESSION_COOKIE_NAME = "__Host-ajora"      # production (needs HTTPS, Path=/, no Domain)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = True               # False only in local development
SESSION_COOKIE_SAMESITE = "Lax"
PERMANENT_SESSION_LIFETIME = 12 hours      # absolute; idle 30 min checked per request
WTF_CSRF_TIME_LIMIT = 3600
MAX_CONTENT_LENGTH = 1 MB
```

## The 8 headers (set once in `security.py`)

```
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; upgrade-insecure-requests
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(self), camera=(), microphone=(), payment=()
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Resource-Policy: same-origin
```

Send HSTS and `upgrade-insecure-requests` only when not in local development.

## Rate limits (per IP unless stated)

- Login 10/min and 50/hour · register 5/hour · place order 10 per 10 min per user · status API 120/min · default 300/min. Hit → 429 page.
- Storage from `RATELIMIT_STORAGE_URI` in `.env`: `memory://` for one worker, `redis://...` for several. Tests turn limits off.

## Passwords and accounts

- At least 8 characters, not in `app/data/common-passwords.txt` (top 10,000), not equal to the email. No forced symbols.
- Admins only through `flask create-admin` (terminal prompt, password not echoed).
- Blocking a customer sets `is_active = 0` and `session_version + 1`.
- `?next=` accepts only paths that start with a single `/` on our own site.

## Input rules

- Name 2–60 chars · email ≤ 254 and valid · phone `^03\d{9}$` after removing the dash · address ≤ 200 · note ≤ 200 · litres integer in the allowed range · latitude 23–37.5 and longitude 60–78 (Pakistan) · dates within 7 days · all text trimmed · unknown fields ignored.

## Test checklist (all 19 must pass before deploy)

1. Wrong password 5 times → locked 10 min, same message as wrong email.
2. 11 logins in a minute from one IP → 429.
3. Customer opens `/admin`, every `/admin/...` and `/api/admin/live` → 403.
4. Customer A opens customer B's `/app/orders/<id>` and `/api/orders/<id>/status` → 404.
5. Logged-out user opens `/app` → Log in, then back to `/app`.
6. `?next=https://evil.com` after login is ignored.
7. POST without CSRF token → 400 page.
8. `role=admin` in the register form → still a customer.
9. `price=1` or `total=1` in the order form → ignored, DB price used.
10. 101 L, 11 L emergency, a second open emergency, car wash in 1 h → refused by the server.
11. Same order key posted twice → one order.
12. Admin posts Pending → Delivered by hand → refused.
13. Name `<script>alert(1)</script>` shows as text everywhere.
14. Search `' OR 1=1 --` returns nothing special and no error.
15. All 8 headers on pages, API and error pages.
16. Cookie is HttpOnly, Secure, SameSite=Lax (production).
17. Idle 31 min → next click logs out with the message; blocked customer logged out on next click.
18. App will not start with DEBUG on or no `SECRET_KEY` in production; `.env` never in Git.
19. `pip-audit` shows 0 known vulnerabilities; OWASP ZAP baseline on our own site shows no High or Medium.
