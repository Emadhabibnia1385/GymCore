You are the lead software engineer responsible for redesigning and completing the existing GymCore repository.

Project name:
GymCore

Repository:
https://github.com/Emadhabibnia1385/GymCore

The repository is already cloned locally.
Work only inside the existing local repository.

IMPORTANT:
Do not create a separate project.
Do not preserve obsolete architecture merely for compatibility.
Inspect the current repository first, then carefully refactor it according to this specification.

==================================================
MANDATORY GIT WORKFLOW
==================================================

Before making changes, run:

pwd
git status
git branch --show-current
git remote -v
ls -la
find . -maxdepth 3 -type f

Then read:

README.md
.claude/skills/gymcore/SKILL.md
all environment examples
all database models
all Telegram and Bale bot code
all installation and deployment files

Work on the main branch unless there is a technical reason not to.

After each completed phase:

1. Run tests.
2. Run lint/type checks where available.
3. Review git diff.
4. Update README and configuration examples.
5. Commit with a clear message.
6. Push to origin/main.
7. Report:
   - files changed
   - tests run
   - commit hash
   - push result

Commands:

git status
git add .
git commit -m "clear meaningful message"
git push origin main

Never leave completed work only locally.

Do not commit:

.env
database files
tokens
passwords
logs
uploaded private files
virtual environments
__pycache__
IDE-specific secrets

==================================================
NEW PRODUCT DIRECTION
==================================================

GymCore is no longer a web dashboard product.

It is a bot-first management system for a personal fitness coach.

The entire client experience and the entire admin management experience must run inside:

1. Telegram bot
2. Bale bot

Both bots must use:

- One shared backend
- One shared database
- One shared business-logic layer
- One shared admin system
- Platform adapters only where Telegram and Bale APIs differ

There must be no separate web admin panel.
There must be no client web dashboard.
There must be no student panel accessible by IP address.
There must be no `/admin` website.
There must be no `/dashboard` website.
There must be no `/me/...` client website.

FastAPI may remain as the internal backend/service layer, health endpoint, webhook receiver, or future API foundation, but it must not expose a user-facing dashboard.

==================================================
REMOVE OBSOLETE FEATURES
==================================================

Completely remove the old request-based registration and ordering workflow.

Remove all code, pages, handlers, schemas, services, templates, and migrations related to:

- ClassRequest
- PlanRequest
- pending class registration
- pending plan order
- request review queues
- NEW / CONTACTED / CONFIRMED / REJECTED request statuses
- in-bot multi-step registration forms
- asking users for a phone number for class registration
- requesting contact sharing for class registration
- selecting a contact network during registration
- admin approval of class-registration requests
- admin approval of plan-order requests
- web registration forms owned by GymCore
- client web dashboard
- web admin dashboard

Before deleting database models, inspect existing migrations and data compatibility.

If obsolete tables already exist:
- Create a safe Alembic migration.
- Do not silently destroy production data.
- Either archive/export obsolete data or document the migration clearly.
- Never reset the database as a shortcut.

The system is a management system, not an ordering pipeline.

==================================================
CLIENT BOT MAIN MENU
==================================================

Use an inline keyboard for the main menu.

The exact Persian layout must be:

Row 1:
🏋️ ثبت‌نام در کلاس‌ها
📋 سفارش برنامه

Row 2:
🗓 کلاس‌های من
📄 برنامه‌های من

Row 3:
📞 راه‌های ارتباطی ما

For coach/admin users, add one extra row at the bottom:

Row 4:
⚙️ ورود به پنل مدیریت

Do not show the admin button to normal clients.

All menu buttons must be inline buttons, often described as “glass buttons”.

Important platform limitation:
Telegram and Bale do not provide arbitrary custom button colors.
Do not attempt unsupported button-color APIs.
Use green visual cues such as 🟢, ✅, or brand-styled message content where appropriate.

Keep all Persian labels centralized in one copy/text module.
Do not scatter user-facing Persian text throughout handlers.

==================================================
BRAND DESIGN SYSTEM
==================================================

Brand owner:
Mahdi Sarmad

Brand colors:

Primary green:
#B2F828

Black:
#000000

White:
#FFFFFF

Apply these colors to:

- README branding
- generated banners/assets
- any HTML health/status page, if one exists
- bot message artwork
- documentation examples

For bot UI, because custom keyboard colors are unavailable:
- use green emojis consistently
- use clean Persian copy
- use structured messages
- avoid excessive emoji clutter

==================================================
REGISTER FOR CLASSES
==================================================

When the client presses:

🏋️ ثبت‌نام در کلاس‌ها

Do not start a form.
Do not create a ClassRequest.
Do not ask for a phone number.
Do not ask for contact sharing.
Do not ask them to select a class.

Send this message or a polished equivalent:

«برای ثبت‌نام در کلاس‌ها و هماهنگی درباره نوع کلاس، زمان‌بندی، تعداد جلسات و هزینه، از طریق یکی از راه‌های ارتباطی زیر با من در تماس باشید تا بهترین گزینه را با هم هماهنگ کنیم. 👇»

Then show the current contact links as inline URL buttons.

Contact links must come from database/admin settings and must not be hardcoded in handlers.

Current default links:

📧 ایمیل
mailto:mahdisarmad59@gmail.com

📞 تلفن
tel:+989305560950

💬 واتساپ
https://wa.me/message/Y5RUNKX4CVP5H1

✈️ تلگرام
https://t.me/mahdisarmadcoach

📷 اینستاگرام
https://www.instagram.com/mahdisarmad

💼 لینکدین
https://www.linkedin.com/in/mahdisarmad

🌐 وب‌سایت
https://mahdisarmad.ir/

Where platform behavior allows:
- Telegram users should see Telegram contact prominently.
- Bale users should see the configured Bale contact prominently.
- All other contact methods should still be available.

Add a back button:

🔙 بازگشت به منوی اصلی

==================================================
ORDER A PROGRAM
==================================================

When the client presses:

📋 سفارش برنامه

Do not start an in-bot order flow.
Do not create a pending request.
Do not ask questions.
Do not collect phone numbers.

Open or provide this URL:

https://mahdisarmad.ir/signup/

Use an inline URL button:

🟢 سفارش برنامه از وب‌سایت

Also send a concise Persian explanation such as:

«برای سفارش برنامه تمرینی یا تغذیه، از طریق دکمه زیر وارد فرم ثبت سفارش شوید.»

Include:

🔙 بازگشت به منوی اصلی

==================================================
MY COURSES
==================================================

When the client presses:

🗓 کلاس‌های من

Find the Person using ChannelIdentity:

- Telegram platform user ID
- Bale platform user ID

The Person owns all shared data.

Show each course as an inline button.

Suggested button label:

🟢 {class title} | {remaining sessions} جلسه باقی‌مانده

Remaining sessions must always be calculated from attendance events.
Never store a mutable `remainingSessions` value as the source of truth.

Opening a course must display:

- class title
- course status
- start date in Jalali
- total sessions
- consumed sessions
- remaining sessions
- allowed absences
- attendance history
- financial summary when appropriate
- carried credit, if any

Attendance outcomes in Persian:

✅ حاضر
🟡 غیبت مجاز
🔴 غیبت غیرمجاز
🔵 لغو توسط مربی
⚪ تعطیلی

Show all session dates in Jalali format.

Attendance history must be append-only.

For Bale:
Do not rely on editing a message containing an inline keyboard.
Send a fresh message for detail views when editing is unreliable.

Provide navigation buttons:

🔙 بازگشت
🏠 منوی اصلی

If a renewal feature is retained, it must create a new Course and apply eligible credit.
Never reset or overwrite the previous course.

==================================================
MY PROGRAMS
==================================================

When the client presses:

📄 برنامه‌های من

List all PlanAssignment records belonging to the Person.

Each item should show:

- program type
- assignment date in Jalali
- optional coach note
- file, document, image, or secure reference

Support Telegram and Bale delivery differences through platform adapters.

Do not expose server filesystem paths.
Do not expose private storage URLs without access control.

If there are no programs, show a friendly Persian empty state.

==================================================
CONTACT US
==================================================

When the client presses:

📞 راه‌های ارتباطی ما

Show all active ContactLink rows as inline URL buttons.

The admin must be able to:

- create links
- edit links
- activate/deactivate links
- reorder links

Do not hardcode the final runtime list in bot handlers.

==================================================
IN-BOT ADMIN PANEL
==================================================

There is no web admin panel.

The coach/admin enters management through:

⚙️ ورود به پنل مدیریت

Authorization must be based on configured numeric owner/admin IDs.

Environment variables:

TELEGRAM_OWNER_IDS=
BALE_OWNER_IDS=

Prefer comma-separated lists so multiple admins can be supported later.

Also retain role-based authorization in the database.

Never trust usernames for admin access.
Use numeric platform user IDs.

Unauthorized users must never see or access admin handlers, even by callback manipulation.

The Telegram and Bale admin panels must provide the same capabilities and use the same business services.

Admin main menu:

👥 مدیریت شاگردان
🏋️ مدیریت کلاس‌ها
📚 مدیریت دوره‌ها
✅ ثبت حضور و غیاب
📄 مدیریت برنامه‌ها
💳 مدیریت پرداخت‌ها
🔔 اعلان‌ها
⚙️ تنظیمات
🏠 خروج از پنل مدیریت

Use inline keyboards.

==================================================
ADMIN: STUDENT MANAGEMENT
==================================================

Admin can:

- search clients by name
- search by canonical phone number
- search by Telegram numeric ID
- search by Bale numeric ID
- create a client
- edit a client
- link Telegram/Bale identities
- view client profile
- view courses
- view programs
- view attendance
- view payments
- pause or activate a client when needed

Use pagination.
Do not send hundreds of buttons in one message.

Person remains the shared human identity.

ChannelIdentity remains the platform login identity.

==================================================
ADMIN: CLASS TYPE MANAGEMENT
==================================================

Admin can:

- list class types
- create a class type
- edit title
- edit description
- enable/disable
- change display order

ClassType fields:

- key
- title
- description
- active
- order

Do not delete catalog rows that are referenced by historical courses.
Use inactive/archived status where appropriate.

==================================================
ADMIN: COURSE MANAGEMENT
==================================================

Admin can:

- create a Course for a client
- select ClassType
- set total sessions
- set tuition in toman
- set gym fee in toman
- set allowed absence
- set start date
- set travelDeclared
- set status
- pause/resume/finish a course
- view derived remaining sessions
- renew a course
- apply valid carried credit

Course statuses:

ACTIVE
FINISHED
PAUSED

Per-person financial and attendance terms must be locked on the Course.

Do not change previous historical terms when catalog defaults change.

==================================================
ADMIN: ATTENDANCE
==================================================

Admin must be able to:

- select a client/course
- select or enter session date
- choose outcome
- add an optional note
- confirm before saving

AttendanceEvent fields:

- course
- sessionDate in UTC
- outcome
- note
- createdAt
- createdBy

Attendance is append-only.

If a correction is required:
- create a correction/reversal mechanism
- preserve audit history
- do not silently overwrite history

Derive:

- consumed sessions
- remaining sessions
- allowed absences used
- financial credit

from attendance events and business rules.

==================================================
ADMIN: PROGRAM MANAGEMENT
==================================================

Admin can:

- create/edit PlanType
- assign a plan to a client
- upload/send a document, PDF, image, or file
- store a platform file ID when suitable
- store an internal safe reference
- add coach notes
- resend an existing assignment
- view assignment history

PlanType defaults:

🥗 برنامه تغذیه اصولی
🏋️ برنامه تمرینی اصولی
🎯 برنامه تمرینی تخصصی

PlanAssignment history must not be silently deleted.

==================================================
ADMIN: PAYMENTS
==================================================

Admin can:

- select a client/course
- record received amount
- set received date
- choose payment kind
- add a note
- view payment history
- see tuition total
- see total paid
- see outstanding balance

Payment history must never be deleted silently.

Corrections must use reversal/adjustment records or an audit-safe approach.

All monetary values are stored as integer Toman amounts.

==================================================
ADMIN: SETTINGS
==================================================

Everything variable must be editable in the in-bot admin panel:

- card number
- coach display name
- registration contact message
- plan order message
- main intro message
- contact links
- default allowed absence
- class types
- plan types
- Bale owner contact
- Telegram owner contact
- notification settings
- low-session threshold

Persist settings in the database.

Do not require a code change for normal content updates.

==================================================
NOTIFICATIONS
==================================================

Retain and improve the shared Notification system.

Support:

- low remaining sessions
- course ending
- payment reminder
- new plan delivered
- manual broadcast
- scheduled notification

Telegram and Bale delivery must use one shared notification service with platform adapters.

Avoid duplicate delivery.

Track:

- scheduledFor
- sentAt
- failedAt
- retryCount
- lastError
- idempotency key where appropriate

==================================================
BACKEND ARCHITECTURE
==================================================

Preferred structure:

app/
  core/
  db/
  models/
  schemas/
  repositories/
  services/
  bots/
    common/
    telegram/
    bale/
  admin/
  notifications/
  api/
  copy/
  utils/

Keep platform-specific handlers thin.

Business logic belongs in services, not duplicated inside Telegram and Bale handlers.

Use:

- FastAPI
- SQLAlchemy
- Alembic
- Pydantic settings
- PostgreSQL in production
- SQLite only for local development/tests if needed

All database schema changes require Alembic migrations.

Do not run `create_all()` as a replacement for migrations in production.

==================================================
INSTALLATION AND SERVER SAFETY
==================================================

The existing installation is incomplete and must be audited.

Create or repair a professional `install.sh`.

The server already hosts other applications.

Therefore:

- do not occupy random existing ports
- do not overwrite global Nginx configuration
- do not replace unrelated systemd services
- do not stop Docker containers that belong to other projects
- do not modify firewall rules globally without explicit confirmation
- do not assume ports 80 or 443 are free
- do not instruct the user to open a client panel through the raw IP address
- do not bind the application publicly to `0.0.0.0` by default

Default safe bind:

APP_HOST=127.0.0.1
APP_PORT=8815

Make the port configurable during installation.

Before selecting a port, check whether it is already in use:

ss -tulpn
or an equivalent safe check.

If the selected port is occupied:
- stop installation
- ask for another port
- do not kill the process using it

Because bots can run with polling:
- use long polling as the safe default where supported
- do not require a public web endpoint merely to operate the bots

If webhook mode is implemented:
- make it optional
- use a dedicated domain/subdomain
- use configurable reverse-proxy settings
- never overwrite an existing virtual host
- validate HTTPS requirements for each platform
- document supported ports

Required environment variables:

APP_HOST=127.0.0.1
APP_PORT=8815
APP_DOMAIN=
APP_BASE_URL=

DATABASE_URL=

TELEGRAM_BOT_TOKEN=
TELEGRAM_OWNER_IDS=
TELEGRAM_BOT_MODE=polling

BALE_BOT_TOKEN=
BALE_OWNER_IDS=
BALE_BOT_MODE=polling

SECRET_KEY=
LOG_LEVEL=INFO
TIMEZONE=Asia/Tehran

No secret may be committed.

Installation must:

- check operating system
- check root permissions
- install only required packages
- create a dedicated Linux user
- create an application directory
- create a Python virtual environment
- install pinned dependencies
- create `.env` securely
- run Alembic migrations
- create a non-conflicting systemd service
- start/restart only GymCore services
- show service status
- show log commands
- preserve existing server applications

Provide commands:

systemctl status gymcore
systemctl restart gymcore
journalctl -u gymcore -f

If Telegram and Bale run as separate workers, use clearly named services:

gymcore-api
gymcore-telegram
gymcore-bale
gymcore-worker

Or use one well-supervised process only if architecture and reliability justify it.

==================================================
DOCKER
==================================================

Keep Docker support optional.

Do not assume Docker owns ports 80 or 443.

Use configurable ports and project-specific container names/networks/volumes.

Example:

COMPOSE_PROJECT_NAME=gymcore

Docker Compose must not conflict with other projects.

==================================================
SECURITY
==================================================

Implement:

- strict admin numeric-ID whitelist
- callback authorization checks
- callback data validation
- rate limiting where reasonable
- secret redaction in logs
- secure environment loading
- safe file validation
- file size limits
- MIME/type validation
- SQL injection protection through ORM
- CSRF is irrelevant for pure bots, but secure any internal API
- no public debug mode
- no default production passwords

Do not display bot tokens in logs or installation summaries.

==================================================
MIT LICENSE
==================================================

Create a root-level file named:

LICENSE

Use the standard MIT License text.

Copyright line:

Copyright (c) 2026 Emad Habibnia

Also update README.md to clearly state:

License: MIT

Do not invent a custom license.
Do not add restrictions that conflict with MIT.

==================================================
TESTING
==================================================

Add or repair tests for:

- identity linking
- admin authorization
- user menu generation
- admin menu visibility
- registration contact flow
- plan-order URL flow
- course remaining-session calculation
- attendance outcomes
- Jalali date presentation
- payment balance calculation
- Telegram handlers
- Bale handlers
- callback tampering
- settings loading
- notification deduplication

Use mocks/fakes for external Telegram and Bale APIs.

Tests must not send real messages.

==================================================
README
==================================================

Rewrite README so it accurately describes the new bot-only architecture.

Include:

- project overview
- Telegram and Bale features
- client menu
- in-bot admin panel
- architecture diagram
- local setup
- server installation
- environment variables
- safe port configuration
- service commands
- migrations
- tests
- backup recommendations
- MIT license
- security notes

Remove screenshots and instructions for deleted web panels.

==================================================
IMPLEMENTATION PHASES
==================================================

Phase 1:
Audit the current codebase and create a written implementation plan.

Phase 2:
Remove obsolete web admin/client dashboard and request workflows safely.

Phase 3:
Normalize models, migrations, settings, and shared services.

Phase 4:
Implement the complete shared client bot flow.

Phase 5:
Implement the Telegram in-bot admin panel.

Phase 6:
Implement the Bale in-bot admin panel using the same services.

Phase 7:
Complete attendance, courses, programs, payments, settings, and notifications.

Phase 8:
Repair install.sh, systemd, optional Docker, port safety, and documentation.

Phase 9:
Add MIT LICENSE, finish tests, and perform final cleanup.

After every phase:
- test
- commit
- push to origin/main

==================================================
DECISION-MAKING RULES
==================================================

Do not repeatedly ask broad questions.

Inspect the code and make reasonable production-quality decisions.

Ask only when:

- a destructive migration requires confirmation
- a secret or platform-specific credential is missing
- a Bale API capability is uncertain
- existing production data may be lost
- two requirements directly conflict

When Telegram functionality is not supported identically by Bale:
- preserve the same business behavior
- adapt the interaction to Bale capabilities
- document the difference
- do not pretend unsupported features exist

==================================================
FIRST RESPONSE
==================================================

Before editing anything, respond with:

1. Current repository assessment
2. Existing architecture
3. Obsolete components to remove
4. Database migration risks
5. Proposed final architecture
6. Implementation phases
7. Exact tests to run
8. Any genuinely blocking question

Then begin implementation unless a destructive-data question blocks progress.