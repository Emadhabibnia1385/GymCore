---
name: gymcore-engineering
description: Engineering constitution for GymCore — a bot-first gym-management system for one coach, running entirely inside Telegram and Bale bots on a shared Python backend (FastAPI, SQLAlchemy 2.0, Alembic, Postgres). Read this skill before writing, reviewing, or refactoring ANY code in this repository — including a "quick" one-line change, a single handler, a copy tweak, a migration, or a config edit. Use it whenever the task touches the client bot flow, the in-bot admin panel, courses, the session grid, attendance, payments, programs, contact links, settings, notifications, identity linking, Jalali dates, Persian copy, models or migrations, install.sh or the systemd services. If you are unsure whether this skill applies, it applies.
license: MIT
metadata:
  author: Emad Habibnia
  version: "1.0.0"
---

# GymCore — engineering constitution

GymCore is a **bot-first management system** for the personal fitness coach
Mahdi Sarmad. The entire product — for clients *and* for the coach — is two
bots (**Telegram** and **Bale**) sharing one backend, one database and one
business-logic layer.

There is **no web dashboard, no client panel, no `/admin` site**. FastAPI exists
only as an internal service: a health probe, a brand status page, and an
optional webhook receiver. Long polling is the default and needs no public port.

Brand: primary green `#B2F828`, black `#000000`, white `#FFFFFF`.

---

## 1. Invariants — never break these

These are the load-bearing rules. A change that violates one is wrong even if
every test still passes.

1. **Remaining sessions are never stored.** They are always derived from the
   append-only attendance history — `courses.remaining_sessions(db, course)`.
   Only `PRESENT` and `ABSENT_UNAUTHORIZED` consume a paid session
   (`SESSION_CONSUMING_STATUSES` in `models/enums.py`). Never add a mutable
   `remaining_sessions` column.
2. **Attendance is append-only.** `services/attendance.py` deliberately has no
   update and no delete. A correction is a *new* event on the same
   `session_date`; the latest event wins (`courses.effective_status_map`).
   Never edit or delete an `AttendanceEvent`.
3. **Payments are immutable.** A correction is a new `Payment` row with a
   negative amount. Never update or delete a payment.
4. **Money is integer Toman.** `BigInteger` columns, `int` in Python. No floats,
   no decimals, no currency conversion anywhere.
5. **Admin access is a numeric owner-ID whitelist.** `core/admin_auth.is_owner`
   reads `TELEGRAM_OWNER_IDS` / `BALE_OWNER_IDS`. Usernames are **never**
   trusted. Authorization is enforced in `bots/common/router.py::_callback`
   *before* any admin handler runs, so callback tampering is rejected outright.
   Never authorize inside a section handler instead.
6. **Course terms are locked on the Course.** `tuition`, `gym_fee`,
   `allowed_absence` and `sessions_total` are per-person agreements copied onto
   the row. Changing a catalog default must never rewrite historical courses.
7. **Catalog rows referenced by history are deactivated, never deleted.**
   `ClassType` and `PlanType` deletion is refused when a course/assignment
   references them — set `active = False` instead.
8. **All user-facing Persian lives in `app/copy/`.** Fixed scaffolding (button
   labels, navigation, empty states) in `copy/texts.py` and
   `copy/admin_texts.py`. Content the coach may reword (intros, the
   registration and plan-order messages, contact links) lives in the
   **database** so it changes without a deploy. Never inline a Persian string
   in a handler.
9. **Business logic lives in `app/services/`.** Bot handlers and admin sections
   are thin: parse the callback, call a service, render a keyboard. Logic must
   never be duplicated between the Telegram and Bale paths — there is only one
   path, adapted by `BotContext`.
10. **No user-facing web surface.** Do not add HTML pages, dashboards, forms or
    public API endpoints. `docs_url=None` and `redoc_url=None` stay off.

---

## 2. Where code lives

```
app/
  core/          config · logging · exceptions · jalali · phone · admin_auth
  db/            base · session · init (SQLite create_all; Postgres = Alembic)
  models/        SQLAlchemy 2.0 models + enums
  repositories/  pagination helper
  services/      ALL business logic (see below)
  copy/          every Persian string
  bots/
    common/      BotClient · runner · router · context · keyboards ·
                 callbacks · state · formatting · grid · client_flow
    telegram/    entrypoint (python -m app.bots.telegram.main)
    bale/        entrypoint (python -m app.bots.bale.main)
  admin/         in-bot admin panel, one module per section
  notifications/ queued/idempotent notifications + worker
  api/           FastAPI: /health, /health/ready, optional webhook
migrations/      Alembic (head: 0012)
tests/           pytest with fakes — never touches the network
deploy/systemd/  gymcore-{api,telegram,bale,worker}.service
```

**Services** (`app/services/`): `persons` · `identities` · `classes` ·
`courses` · `attendance` · `schedule` · `payments` · `plans` · `contact_links` ·
`settings` · `auth` · `notifications` · `stats` · `bootstrap`.

**Admin sections** (`app/admin/`), routed by `panel.py::SECTIONS`:
`students` · `classes` · `courses` · `attend` · `plans` · `pay` · `notify` ·
`settings` · `contacts` · `start`. Each exposes `handle_callback(req, args)` and
`handle_message(req, message, substep, state)`.

Reaching a student's courses, programs, attendance and payments goes **through
the student profile** (`students` → `view`), not a top-level courses section.

---

## 3. The session grid — the subtle core

`services/schedule.py` derives the coach's paper attendance table. Nothing about
it is stored. Get these rules right or the coach's counts silently break:

- The grid always ends up holding exactly `sessions_total` **consuming** slots.
- `ABSENT_ALLOWED` / `COACH_CANCELLED` / `HOLIDAY` do **not** consume, so each
  one pushes an extra row onto the end — the client gets that session back.
- Session numbers (`جلسه ۱، جلسه ۲…`) count **consuming slots only**, in date order.
- Dates walk `Course.weekdays` (Persian indexes, `شنبه = 0`) forward from
  `start_date`. A course with no pattern falls back to its start date's weekday.
- Skipped dates in the middle stay on the grid as «در انتظار» — the timeline is
  never allowed to lose a gap.
- `MOVED` vacates its original date and expects the session on `moved_to`; the
  original row leaves the grid but stays in the audit history.
- **`allowed_absence == 0` means NO LIMIT**, not zero allowed. Render the
  counter bare in that case; only append `/N` when `allowed_absence > 0`. This
  rule appears in both `grid.header` and `formatting.format_course_detail` —
  keep them in step.

The grid renders as three glass buttons per row (weekday · Jalali date ·
outcome). Every cell in a row carries the same callback, so tapping anywhere on
the row opens that session's outcome picker. The client sees the same layout
with inert cells (`cb.NOOP`).

---

## 4. Platform differences (Telegram vs Bale)

Bale exposes a Telegram-compatible Bot API at `https://tapi.bale.ai`, so one
`BotClient` and one set of handlers serve both. Differences are absorbed by
`BotContext` capabilities — **never** fork a handler per platform.

| Capability | Telegram | Bale |
|---|---|---|
| `supports_edit` (edit a message with an inline keyboard) | ✅ | ❌ send fresh |
| `supports_button_style` (coloured buttons) | ✅ | ❌ `style` stripped |
| `supports_copy_text` (tap-to-copy buttons) | ✅ | ❌ rendered as text |
| `supports_web_app` (Mini App) | ✅ | ❌ plain URL button |

Hard constraints on both:

- Inline button URLs accept **only** `http://`, `https://`, `tg://`.
  `mailto:` and `tel:` are rejected with `BUTTON_URL_INVALID` and fail the whole
  message — use `keyboards.is_button_url()` and fall back to copy buttons or text.
- `callback_data` is capped at **64 bytes**. Keep tokens short; admin callbacks
  are `a:<section>:<action>:<args>`.
- Every inbound callback argument is parsed tamper-safely — `cb.parse_int` and
  `grid.parse_date_token` return `None` on anything malformed. Never trust
  callback data.

Owner IDs are **per platform**: a Telegram owner is not automatically an admin
on Bale.

**Single-message UX:** `BotContext` tracks one "screen" message per chat.
`ctx.show()` edits it in place where reliable, otherwise deletes and re-sends.
The user's own messages are deleted after handling. Use `ctx.show()` for
navigation and `ctx.send()` only for things that should persist.

Document any new divergence in `docs/PLATFORM_DIFFERENCES.md`. Never pretend an
unsupported feature exists.

---

## 5. Identity

A `Person` is the shared human identity and owns everything. A
`ChannelIdentity` links one platform account (`TELEGRAM` or `BALE`) to that
person.

On a client's **first contact only**, the bot asks once for a mobile number —
the join key that makes the same human resolve to one `Person` across both
platforms (`identities.link_by_phone`). Owners bypass it. This is the *single*
question the bots ever ask a client and it is deliberately **not** part of class
registration, which stays form-free. Phones are normalized to `09xxxxxxxxx`
(`core/phone.py`) before any lookup.

---

## 6. Data and migrations

- Postgres in production, SQLite for local dev and tests.
- SQLite auto-creates from the models (`db/init.py::init_dev_schema`). Postgres
  is **Alembic only** — never run `create_all()` against it.
- Every schema change needs a migration. Migrations are forward-only and
  data-preserving; the database is never reset.
- Retired tables that still hold history (currently `reminder_logs`) are listed
  in `RETIRED_TABLES` in `migrations/env.py` so autogenerate never proposes
  dropping them.
- Content refreshes for existing deployments (seed rows already inserted) need
  an explicit `UPDATE` migration — startup seeding only fills in *missing* keys.

---

## 7. Persian copy rules

- Informal, warm, second-person singular («بزن», «بفرست», «خوش آمدی»).
- Green cues (🟢 ✅) for success; keep emoji purposeful, not decorative clutter.
- Jalali dates everywhere a date is shown (`core/jalali.py`). Never show a
  Gregorian date to a user.
- Money formatted with thousands separators plus `تومان`.
- Attendance outcome labels are fixed:
  ✅ حاضر · 🟡 غیبت مجاز · 🔴 غیبت غیرمجاز · 🔵 لغو توسط مربی · ⚪ تعطیلی · 🔀 جایگزین شد

---

## 8. Testing

```bash
.venv/bin/ruff check .
.venv/bin/pytest -q
```

**Python 3.11+ is required to run the tests.** SQLAlchemy resolves
`Mapped[str | None]` at runtime, which needs 3.10+; on 3.9 the whole suite fails
at import with `MappedAnnotationError`. Ruff works on any version.

- `tests/conftest.py` sets a throwaway SQLite DB, a temp upload dir and fixed
  owner IDs (`111,222` Telegram / `333` Bale) **before** importing the app, and
  sets `notifications.enabled = False`.
- `tests/fakes.py` provides the fake bot client. **Tests never touch the network
  and never send a real message.** Any new bot code must be testable through the
  fake.
- Cover the invariant, not just the happy path: session derivation, append-only
  corrections, tamper-safe callbacks, and both platforms.

CI (`.github/workflows/ci.yml`) runs ruff + pytest on Python 3.12 for every push
to `main` and every PR.

---

## 9. Deployment and server safety

The server hosts **other applications**. The installer is deliberately narrow:

- Default bind is loopback: `APP_HOST=127.0.0.1`, `APP_PORT=8815`.
- `install.sh` checks the port with `ss -tulpn` and **stops** if it is taken —
  it never kills the occupant.
- It touches **only** `gymcore-*` systemd units. Never nginx, never firewall
  rules, never ports 80/443, never Docker, never another app.
- Secrets are never printed or logged (`core/logging.py` redacts
  `settings.secret_values`). Never echo a bot token.

Services: `gymcore-api`, `gymcore-telegram`, `gymcore-bale`, `gymcore-worker`.

```bash
sudo gymcore                      # management menu (install/update/logs/status)
systemctl status gymcore-telegram
journalctl -u gymcore-bale -f
```

An optional `gymcore-update.timer` pulls `origin/main` every minute and
reinstalls when it moves.

---

## 10. Common tasks

**Add an admin section** — create `app/admin/<name>.py` with `handle_callback`
and `handle_message`, register it in `panel.py::SECTIONS`, add a button in
`keyboards.admin_menu()`, and put every string in `copy/admin_texts.py`.

**Add an editable setting** — add the `KEY_*` constant in `models/setting.py`,
a default in `services/settings.py::_defaults()`, and a label in
`admin_texts.SETTINGS_LABELS` (that alone makes it editable in-bot). No
migration needed; seeding fills it in on next start.

**Add an attendance outcome** — extend `AttendanceStatus`, decide whether it
belongs in `SESSION_CONSUMING_STATUSES`, then update `grid.STATUS_CODES`,
`_CELL_LABELS`, `PICKER_LABELS`, `STATUS_STYLES`, the picker rows, and
`attendance._STATUS_LABELS`. Add a migration for the enum on Postgres.

**Add a contact link** — it is data, not code: the coach adds it from
«📞 راه‌های ارتباطی». Only `_DEFAULT_LINKS` in `services/contact_links.py`
changes, and existing deployments need an `UPDATE` migration.

**Change client-visible wording** — if the coach should be able to change it,
it belongs in DB settings, not in `copy/`.

---

## 11. Before you commit

1. `ruff check .` clean.
2. `pytest -q` green (needs Python 3.11+).
3. `git diff` reviewed in full.
4. README and `docs/` updated if behaviour, the menu, or the migration head moved.
5. Commit message: a short topic-prefixed subject, then prose explaining *why*
   — match the existing history (`git log`).
6. Never commit `.env`, database files, tokens, logs, uploads, `.venv`, or
   `__pycache__`.
