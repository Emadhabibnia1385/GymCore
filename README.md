# 🏋️ GymCore

**GymCore** is a fitness coach management platform: students, classes, courses,
training & nutrition plans, attendance, payments — managed through a Persian
web admin panel, a client dashboard, and **Telegram + Bale bots** that share
one backend.

## Architecture

```
Telegram Bot ───┐
Bale Bot ───────┤
Web Admin ──────┼──▶  Service layer (business rules)  ──▶  PostgreSQL
Client Panel ───┤            ▲
REST API ───────┤            │
Reminder worker ┘────────────┘   (future mobile app uses the same API)
```

| Layer | Path | Notes |
|---|---|---|
| Models | `app/models/` | SQLAlchemy 2.0 entities |
| Services | `app/services/` | **All** business logic lives here |
| REST API | `app/api/v1/` | JWT auth (cookie or Bearer) |
| Web UI | `app/web/` | Persian RTL, server-rendered |
| Bots | `app/bots/` | One platform-agnostic core for Telegram & Bale |
| Jobs | `app/jobs/` | Background workers (reminders) as standalone processes |

### Business rules baked into the code

- **Remaining sessions are never stored** — always computed from attendance
  history. Only `PRESENT` and `ABSENT_UNAUTHORIZED` consume a session.
- **Attendance history is append-only** — no update/delete anywhere.
- **Payments are immutable** — corrections are new rows with negative amounts.
- Courses auto-finish when the last paid session is consumed.
- Clients registering via bot are matched to existing students by phone number.
- **Automated reminders** — a background worker nudges clients when a course is
  running low on sessions or has gone quiet, without ever spamming (sends are
  de-duplicated and logged, append-only, in `reminder_logs`).

## Quick start (Ubuntu server, Docker)

```bash
git clone https://github.com/Emadhabibnia1385/GymCore.git
cd GymCore
sudo bash install.sh
```

The installer sets up Docker, generates secrets, asks you to fill tokens in
`.env`, and starts PostgreSQL + API + both bots + nginx.

- Admin panel: `http://<server>/admin`
- Client dashboard: `http://<server>/`
- API docs (Swagger): `http://<server>/docs`

## Local development

```bash
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt   # Windows: .venv\Scripts\pip
cp .env.example .env                             # fill ADMIN_PHONE / ADMIN_PASSWORD
# SQLite works out of the box: DATABASE_URL=sqlite:///./gymcore.db
.venv/bin/uvicorn app.main:app --reload
.venv/bin/python -m app.bots.telegram_main       # in another terminal
.venv/bin/python -m app.bots.bale_main           # in another terminal
.venv/bin/python -m app.jobs.reminders           # reminder worker (optional)
```

On SQLite the schema is created automatically. Lint and test with:

```bash
.venv/bin/ruff check .
.venv/bin/pytest
```

## Configuration

Everything comes from `.env` — see [.env.example](.env.example).
No token, password or secret is ever hardcoded.

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | `postgresql+psycopg://user:pass@host:5432/gymcore` |
| `SECRET_KEY` | JWT signing key (generate: `openssl rand -hex 32`) |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_OWNER_ID` | Telegram bot + owner notifications |
| `BALE_BOT_TOKEN` / `BALE_OWNER_ID` | Bale bot + owner notifications |
| `ADMIN_PHONE` / `ADMIN_PASSWORD` | Bootstrap admin, created on first startup |
| `DOMAIN`, `COOKIE_SECURE` | Set `COOKIE_SECURE=true` once HTTPS is enabled |
| `CORS_ORIGINS` | Comma-separated origins for a cross-origin SPA (empty = same-origin) |
| `REMINDER_*` | Reminder worker cadence and thresholds (see `.env.example`) |

## Running beside other services on the same server

If port 80 is already taken (another site/panel on the server), set a free
port in `.env` and restart:

```bash
HTTP_PORT=8090
```

```bash
docker compose up -d
```

GymCore is then served at `http://your-domain:8090/…`. Alternatively, keep
GymCore off port 80 entirely and add a vhost to the **existing** host nginx
that proxies your (sub)domain to `127.0.0.1:8000` (the API container is bound
to loopback), then stop the bundled nginx: `docker compose stop nginx`.

## Deployment variants

- **Docker (recommended):** `docker-compose.yml` — db, migrate, api,
  telegram-bot, bale-bot, reminders, nginx. The one-shot `migrate` service runs
  `alembic upgrade head` before the app services start.
- **Bare metal:** systemd units in [deploy/systemd/](deploy/systemd/) +
  [deploy/nginx.conf](deploy/nginx.conf); app lives in `/opt/gymcore` with a
  virtualenv. The API unit runs `alembic upgrade head` on start.

## Database migrations

The schema is managed by **Alembic** on Postgres. SQLite (local dev/tests)
still auto-creates tables from the models, so no migration step is needed there.

```bash
alembic upgrade head        # apply all migrations (run on deploy)
alembic revision --autogenerate -m "describe change"   # after editing models
alembic downgrade -1        # roll back one migration
```

Under Docker this runs automatically (the `migrate` service). Adding a model or
column? Edit the model, autogenerate a revision, review it, and commit it under
`migrations/versions/`.

> **Upgrading a pre-Alembic deployment** whose tables were created by the old
> `create_all`: baseline it once so Alembic won't try to recreate existing
> tables, then upgrade:
>
> ```bash
> alembic stamp 0001        # mark the v1.0 baseline as already applied
> alembic upgrade head      # applies only the new migrations (reminder_logs, …)
> ```

## Notes & roadmap

- Dates are stored Gregorian, displayed Jalali (شمسی).
- Delivered: Alembic migrations, automated reminders, production hardening
  (CORS, security headers, readiness probe), ruff + CI.
- Roadmap (SaaS direction): online payments, subscriptions, multi-coach
  support, analytics, mobile app.

## License

Released under the [MIT License](LICENSE) — © 2026 Emad Habibnia.
