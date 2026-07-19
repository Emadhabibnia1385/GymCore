# 🏋️ GymCore

**GymCore** is a **bot-first management system** for a personal fitness coach.
The entire experience — for clients *and* for the coach — runs inside **Telegram**
and **Bale** bots that share one backend, one database, and one business-logic
layer. There is **no web dashboard, no client panel, and no `/admin` site.**

Brand — Mahdi Sarmad · primary green `#B2F828` · black `#000000` · white `#FFFFFF`.

---

## What it does

**Clients** (inline "glass" menu):

| | |
|---|---|
| 🏋️ ثبت‌نام در کلاس‌ها | Shows the coach's contact links to arrange a class (no form, no phone prompt) |
| 📋 سفارش برنامه | Opens the signup form (Telegram Mini App / Bale URL) |
| 🗓 کلاس‌های من | Courses with **remaining sessions derived from attendance**, Jalali history, financials |
| 📄 برنامه‌های من | Delivered training/nutrition programs (file or text) |
| 📞 راه‌های ارتباطی ما | All active contact links |

The **⚙️ ورود به پنل مدیریت** row appears **only** for configured owners.

**Coach / admin** (in-bot panel, same on both platforms): students · classes ·
courses · attendance · programs · payments · notifications · settings.

## Business rules baked in

- **Remaining sessions are never stored** — always derived from attendance
  history; only `PRESENT` and `ABSENT_UNAUTHORIZED` consume a session.
- **Attendance is append-only** — corrections are appended (latest event per
  session date wins); nothing is ever overwritten.
- **Payments are immutable** — corrections are new rows with negative amounts.
- **Money is integer Toman**; catalog changes never rewrite historical course terms.
- **Admin auth is a numeric owner-ID whitelist** — usernames are never trusted.

## Architecture

```
 Telegram bot ┐                       ┌ services/ (all business logic)
 Bale bot     ┤─ bots/common (router, ┤  courses · attendance · payments · plans
 (long poll)  │   inline keyboards,   │  persons · identities · classes · settings
              │   BotContext adapter) │  contact_links · auth (owner whitelist)
 admin/ (8 shared sections) ──────────┤
 notifications/ (queue + worker) ─────┤─ models/ (SQLAlchemy 2.0) ─ Alembic ─ PostgreSQL
 api/ (health + optional webhook) ────┘                                      (SQLite for dev)
```

Platform-specific code is thin: `BotContext` knows each platform's capabilities
(Telegram edits messages + Mini App; Bale sends fresh messages + URL buttons).
See [docs/PLATFORM_DIFFERENCES.md](docs/PLATFORM_DIFFERENCES.md).

| Layer | Path |
|---|---|
| Models | `app/models/` |
| Services (business logic) | `app/services/` |
| Client bot flow | `app/bots/common/` |
| Platform entrypoints | `app/bots/telegram/`, `app/bots/bale/` |
| In-bot admin panel | `app/admin/` |
| Notifications + worker | `app/notifications/` |
| Internal API (health/webhook) | `app/api/` |
| Persian copy (single source) | `app/copy/` |

## Local development

```bash
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt      # Windows: .venv\Scripts\pip
cp .env.example .env                               # SQLite works out of the box
.venv/bin/python -m app.bots.telegram.main         # Telegram bot (polling)
.venv/bin/python -m app.bots.bale.main             # Bale bot (polling)
.venv/bin/python -m app.notifications.worker       # reminders/notifications worker
.venv/bin/uvicorn app.api.main:app --reload        # optional health/webhook API
```

On SQLite the schema is auto-created from the models. Lint and test:

```bash
.venv/bin/ruff check .
.venv/bin/pytest -q
```

## Server installation (Debian/Ubuntu)

```bash
git clone https://github.com/Emadhabibnia1385/GymCore.git
cd GymCore && sudo bash install.sh
```

The installer is **safe for a shared server**: it creates a dedicated `gymcore`
user and `/opt/gymcore`, a virtualenv with pinned deps, a `600`-permission `.env`
(auto-generated `SECRET_KEY`), runs migrations, and installs **only** the
`gymcore-*` systemd services. It **never** touches nginx, firewall rules, ports
80/443, Docker, or any other app. It checks that `APP_PORT` is free and **stops
(without killing anything) if it is taken** so you can pick another port.

```bash
systemctl status gymcore-api
systemctl restart gymcore-telegram
journalctl -u gymcore-bale -f
journalctl -u gymcore-worker -f
```

Services: `gymcore-api`, `gymcore-telegram`, `gymcore-bale`, `gymcore-worker`.

## Configuration

Everything comes from `.env` — see [.env.example](.env.example). No token,
password or secret is ever hardcoded or logged.

| Variable | Purpose |
|---|---|
| `APP_HOST` / `APP_PORT` | API bind — default **`127.0.0.1:8815`** (loopback, non-privileged) |
| `APP_DOMAIN` / `APP_BASE_URL` | Only needed for optional webhook mode |
| `DATABASE_URL` | `postgresql+psycopg://…` (prod) or `sqlite:///./gymcore.db` (dev) |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_OWNER_IDS` | Telegram bot + **comma-separated** numeric admin IDs |
| `BALE_BOT_TOKEN` / `BALE_OWNER_IDS` | Bale bot + admin IDs |
| `TELEGRAM_BOT_MODE` / `BALE_BOT_MODE` | `polling` (default, safe) or `webhook` |
| `SIGNUP_URL` | Plan-order form opened by «سفارش برنامه» |
| `SECRET_KEY` | Internal signing / webhook secret (`openssl rand -hex 32`) |
| `LOG_LEVEL`, `TIMEZONE` | `INFO`, `Asia/Tehran` |
| `LOW_SESSION_THRESHOLD`, `REMINDER_*` | Reminder worker thresholds/cadence |

### Running beside other services

The default loopback bind means GymCore claims no public port. If you enable
webhook mode later, add a vhost to your **existing** reverse proxy pointing at
`127.0.0.1:${APP_PORT}` on a dedicated (sub)domain — GymCore never edits your
web server for you.

## Docker (optional)

```bash
cp .env.example .env      # set tokens; point DATABASE_URL at the db service
docker compose up -d --build
```

Project-scoped (`name: gymcore`, `gymcore_pgdata` volume). The API publishes to
`127.0.0.1:${APP_PORT}` only — never 80/443. Services: `db`, `migrate` (one-shot
`alembic upgrade head`), `api`, `telegram`, `bale`, `worker`.

## Database migrations

Schema is managed by **Alembic** on Postgres; SQLite (dev/tests) auto-creates
from the models.

```bash
alembic upgrade head                                   # apply (run on deploy)
alembic revision --autogenerate -m "describe change"   # after editing a model
alembic downgrade -1                                   # roll back one
```

Migrations are forward-only and data-preserving — the schema is never reset.

## Backups

Back up the database and the uploads directory regularly:

```bash
# PostgreSQL
pg_dump "$DATABASE_URL" > gymcore-$(date +%F).sql
# uploaded program files
tar czf gymcore-uploads-$(date +%F).tar.gz /opt/gymcore/uploads
```

## Security

Numeric owner-ID whitelist · callback authorization gated in the router (tamper
rejection) · callback-data validation · secret redaction in logs (tokens never
printed) · safe file validation (extension + size limits) · ORM-only queries ·
no public API docs · no debug in production · no default passwords.

## Tests

`pytest` with fakes for Telegram/Bale — tests never touch the network or send
real messages. Coverage includes identity linking, admin authorization + callback
tampering, menu generation, register/order flows, session derivation, attendance
outcomes, Jalali dates, payment balances, both platforms, settings, and
notification dedup/retry.

## License

Released under the [MIT License](LICENSE) — © 2026 Emad Habibnia.
