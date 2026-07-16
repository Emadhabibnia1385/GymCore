# 🏋️ GymCore

**GymCore** is a fitness coach management platform: students, classes, courses,
training & nutrition plans, attendance, payments — managed through a Persian
web admin panel, a client dashboard, and **Telegram + Bale bots** that share
one backend.

## Architecture

```
Telegram Bot ─┐
Bale Bot ─────┼──▶  Service layer (business rules)  ──▶  PostgreSQL
Web Admin ────┤            ▲
Client Panel ─┘            │
REST API (/api/v1) ────────┘   (future mobile app uses the same API)
```

| Layer | Path | Notes |
|---|---|---|
| Models | `app/models/` | SQLAlchemy 2.0 entities |
| Services | `app/services/` | **All** business logic lives here |
| REST API | `app/api/v1/` | JWT auth (cookie or Bearer) |
| Web UI | `app/web/` | Persian RTL, server-rendered |
| Bots | `app/bots/` | One platform-agnostic core for Telegram & Bale |

### Business rules baked into the code

- **Remaining sessions are never stored** — always computed from attendance
  history. Only `PRESENT` and `ABSENT_UNAUTHORIZED` consume a session.
- **Attendance history is append-only** — no update/delete anywhere.
- **Payments are immutable** — corrections are new rows with negative amounts.
- Courses auto-finish when the last paid session is consumed.
- Clients registering via bot are matched to existing students by phone number.

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
```

Run tests:

```bash
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

## Deployment variants

- **Docker (recommended):** `docker-compose.yml` — db, api, telegram-bot,
  bale-bot, nginx.
- **Bare metal:** systemd units in [deploy/systemd/](deploy/systemd/) +
  [deploy/nginx.conf](deploy/nginx.conf); app lives in `/opt/gymcore` with a
  virtualenv.

## Notes & roadmap

- Schema is created automatically on startup (`create_all`); Alembic
  migrations will be introduced with the first schema change.
- Dates are stored Gregorian, displayed Jalali (شمسی).
- Roadmap (SaaS direction): online payments, automated reminders,
  subscriptions, multi-coach support, analytics, mobile app.
