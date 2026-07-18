# GymCore — Implementation Plan (v2, bot-first)

> Status: **Phase 1 complete** (this document). Source of truth for requirements:
> `.claude/skills/gymcore/SKILL.md`.

GymCore is a **bot-first management system** for coach **Mahdi Sarmad**. The entire
client experience and the entire admin experience run inside the **Telegram** and
**Bale** bots. There is **no web admin panel and no client dashboard**. FastAPI
remains only as an internal service layer (health probe, optional webhook receiver).

Brand: primary green `#B2F828`, black `#000000`, white `#FFFFFF`.

## Context: repository was reset

The latest commit `aa5d035` ("بریم شروع دوباره") wiped the working tree to just the
project skill. The full v1 application (109 files) is preserved in git history at
commit `2f0be30` and is used as the salvage/reference source. We **rebuild in-tree**,
reusing the correct v1 parts and restructuring per the new spec.

## What we keep from v1

- Data model & business rules: Person + ChannelIdentity, append-only attendance,
  immutable payments, **remaining sessions derived from attendance** (never stored),
  session-consuming rule (only `PRESENT` + `ABSENT_UNAUTHORIZED` burn a session),
  integer-Toman money.
- Shared `BotClient` (one httpx client for Telegram and Bale via `tapi.bale.ai`),
  long-polling runner, notification dispatch, Jalali + phone utilities.
- Alembic migration chain `0001 → 0002 → 0003`.

## What we remove

- The entire web layer (`app/web/**`, admin templates, static, `/` → `/admin`
  redirect), JWT/web auth, `Person.password_hash`, password-based bootstrap admin.
- The in-bot registration form (name/phone prompts, contact sharing).
- Reply keyboards (replaced by inline "glass" keyboards).
- Any residue of the request workflow (ClassRequest / PlanRequest / RequestStatus).
- Singular `*_OWNER_ID` env vars (replaced by plural `*_OWNER_IDS`).

## Target architecture

```
app/
  core/          config, logging, exceptions, jalali, phone, admin-auth, rate-limit
  db/            base, session
  models/        person, channel_identity, class_type, course, attendance,
                 payment, plan_type, plan_assignment, contact_link, setting,
                 notification, enums
  repositories/  thin data-access helpers (pagination, lookups)
  services/      persons, identities, classes, courses, attendance, payments,
                 plans, contact_links, settings, stats, auth (admin whitelist)
  copy/          ALL Persian strings + labels (single source)
  bots/
    common/      BotClient, polling runner, update/callback router, inline
                 keyboard builders, pagination, per-chat state, admin guard,
                 formatters, shared client flow
    telegram/    adapter (Mini App, message edit) + entrypoint
    bale/        adapter (URL fallback, fresh-message strategy) + entrypoint
  admin/         in-bot admin handlers (students, classes, courses, attendance,
                 plans, payments, notifications, settings) — platform-agnostic
  notifications/ shared notification domain + delivery worker (dedup, retry)
  api/           FastAPI: /health, /health/ready, optional webhook — NO dashboard
migrations/      0001-0003 preserved + 0004+ forward
deploy/          systemd units (gymcore-telegram, gymcore-bale, gymcore-api, gymcore-worker)
install.sh       safe: 127.0.0.1:8815 default, port-conflict check
```

## Client inline menu (exact)

```
Row 1:  🏋️ ثبت‌نام در کلاس‌ها        📋 سفارش برنامه
Row 2:  🗓 کلاس‌های من               📄 برنامه‌های من
Row 3:  📞 راه‌های ارتباطی ما
Row 4 (owners only):  ⚙️ ورود به پنل مدیریت
```

- **ثبت‌نام در کلاس‌ها** → contact message + contact links (no form, no request).
- **سفارش برنامه** → inline URL button to `https://mahdisarmad.ir/signup/` (no flow).
- **کلاس‌های من** → courses as inline buttons; detail shows derived remaining
  sessions, Jalali dates, attendance history, financial summary.
- **برنامه‌های من** → PlanAssignment list/delivery.
- **راه‌های ارتباطی ما** → active ContactLink rows as inline URL buttons.

## In-bot admin panel (owners only, both platforms)

Numeric-ID whitelist (`TELEGRAM_OWNER_IDS`, `BALE_OWNER_IDS`) + DB role. Menu:
students, classes, courses, attendance, programs, payments, notifications,
settings. Same shared services on Telegram and Bale; Bale adapts interactions
where inline-message editing is unreliable (send fresh messages).

## Database migration strategy

Preserve `0001-0003`; add non-destructive forward migrations `0004+`:

- `class_types`: add `key`.
- `courses`: add `allowed_absence`, `travel_declared`.
- `plans` → `plan_types` + `plan_assignments` (copy existing rows, then drop `plans`).
- new `contact_links` (seeded from spec defaults + prior `contact_text`).
- new `notifications` (scheduledFor, sentAt, failedAt, retryCount, lastError,
  idempotency_key); retain `reminder_logs` history.
- drop web-only `persons.password_hash`.
- seed new settings keys (card number, coach name, messages, thresholds, owner
  contacts).

Never reset the database. Enum changes are dialect-aware (Postgres vs SQLite).

## Phases

1. **Audit & plan** (this doc).
2. **Foundation** — skeleton, config, core utils, db, models, restored migration chain.
3. **Migrations, settings, shared services** — new tables/seeds normalized.
4. **Shared client bot flow** — inline menu + all five client actions.
5. **Telegram in-bot admin panel.**
6. **Bale in-bot admin panel** (same services).
7. **Complete domain features** — attendance, courses, programs, payments,
   settings, notifications end-to-end.
8. **install.sh / systemd / optional Docker / README** — safe & documented.
9. **MIT LICENSE, tests, final cleanup.**

After each phase: `ruff check .`, `pytest -q`, review diff, update docs, commit,
push `origin/main`, report files/tests/commit/push.

## Tests (fakes for Telegram/Bale — no real network)

identity linking · admin numeric-ID authorization + callback tamper rejection ·
client menu generation · admin-button visibility · register→contact (asserts no
form/request/phone) · order→signup URL · course remaining-session derivation ·
attendance outcomes + session consumption + append-only · Jalali presentation ·
payment balance · Telegram handlers · Bale handlers · settings loading ·
notification dedup/idempotency · contact-link rendering/order.

## Security

Numeric-ID admin whitelist · callback authorization + data validation · rate
limiting · secret redaction in logs (never log tokens) · safe file validation
(size + MIME) · ORM-only queries · no public debug mode · no default production
passwords.

## License

MIT — © 2026 Emad Habibnia (added in Phase 9, `LICENSE` at repo root).
