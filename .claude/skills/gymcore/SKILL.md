# GymCore Project Skill

## Project Identity

Name:
GymCore

Description:
GymCore is a fitness coach management platform for managing students, classes, training plans, nutrition plans, attendance, payments, and communication through Telegram, Bale and Web dashboard.

Repository:
https://github.com/Emadhabibnia1385/GymCore


# Core Rule

You are working on an existing production project.

Never rewrite the project from zero.

Always:
1. Inspect existing code.
2. Understand architecture.
3. Make small controlled changes.
4. Test changes.
5. Commit.
6. Push to GitHub main branch.


# Development Workflow

Before coding:

Run:

git status
ls -la
find . -maxdepth 2 -type f


Understand:

- Backend
- Database
- Frontend
- Bots
- Deployment


After every feature:

Run tests.

Then:

git add .
git commit -m "describe change"
git push origin main


Never leave uncommitted changes.


# Architecture

Main architecture:

Telegram Bot
        |
Bale Bot
        |
Web Dashboard
        |
        |
     FastAPI Backend
        |
     PostgreSQL


All clients must use the same backend services.


# Backend

Framework:

FastAPI


Requirements:

- Clean architecture
- Modular services
- API separation
- Environment variables
- Logging
- Error handling


# Database Models


Person:

- id
- name
- phone
- role


Roles:

CLIENT
COACH
ADMIN


ChannelIdentity:

- platform
- platformUserId
- personId


Platforms:

TELEGRAM
BALE
WEB


# Business Logic


## Classes

ClassType:

- title
- description
- active
- order


## Courses

Course:

- client
- class
- sessions
- tuition
- gym fee
- start date
- status


Status:

ACTIVE
FINISHED
PAUSED


Remaining sessions are calculated.

Never store remaining sessions manually.


## Attendance

AttendanceEvent:

Statuses:

PRESENT
ABSENT_ALLOWED
ABSENT_UNAUTHORIZED
COACH_CANCELLED
HOLIDAY


Attendance history is append-only.


## Payments

Payment history must never be deleted.


## Plans

Support:

- Training plans
- Nutrition plans
- Custom plans


# Telegram Bot

Keyboard:

🏋️ ثبت‌نام کلاس
📋 سفارش برنامه
🗓 کلاس‌های من
📄 برنامه‌های من
📞 راه‌های ارتباطی ما


Bot responsibilities:

- Show courses
- Show attendance
- Show plans
- Send notifications


# Bale Bot

Same functionality as Telegram.

Both bots share backend.


# Admin Panel

Admin can:

- Manage students
- Create courses
- Manage classes
- Upload plans
- Record attendance
- Record payments
- Manage settings


# Environment

Never hardcode:

Tokens
Passwords
Secrets


Use:

.env


Required:

TELEGRAM_BOT_TOKEN=
TELEGRAM_OWNER_ID=

BALE_BOT_TOKEN=
BALE_OWNER_ID=

DATABASE_URL=

DOMAIN=


# Deployment

Maintain:

install.sh

docker-compose.yml

nginx configuration

systemd service


Deployment must be simple:

One command installation on Ubuntu server.


# Code Style

Write professional production code.

Avoid:

- duplicate logic
- hardcoded values
- temporary hacks

Prefer:

- reusable services
- clear naming
- documentation


# Product Vision

GymCore should become a SaaS platform for fitness coaches.

Future features:

- online payments
- automated reminders
- subscriptions
- mobile application
- analytics
- multiple coaches


# Language

User interface:
Persian

Code:
English


# Visual Identity

Brand: "Mehdi Sarmad" — phosphor green on black. The web surface is dark-theme only.

Design tokens (single source of truth: `app/web/static/style.css` `:root`):

```css
:root {
  /* Brand */
  --primary: #B2F828;   /* phosphor green — buttons, links, active nav, stat values */

  /* Base */
  --background: #000000;
  --foreground: #FFFFFF;

  /* UI */
  --card: #111111;
  --border: #2A2A2A;

  /* States */
  --success: #B2F828;
  --danger:  #FF4D4F;
  --warning: #FFC107;
}
```

Rules:

- All web colors come from these tokens — never hardcode a hex in a template or rule.
- Text on a green (`--primary`) fill must be near-black (`--on-primary`), never white:
  the green is light, so white-on-green fails contrast.
- Badges/alerts use translucent tints of the state color on the dark card, not solid fills.
- Bots (Telegram/Bale) have no colors of their own; there the identity is carried by
  tone, emoji and structure — not styling.


# Content & Tone

UI language is Persian; the voice is warm, encouraging and lightly literary —
GymCore speaks to the athlete as a companion on the road, using informal «تو».

- Prose (greetings, confirmations, reminders, empty states) carries the literary
  warmth. Keep it concise — a sentence or two, never a paragraph.
- Buttons and menu labels stay short and iconic; they are also router keys in
  `app/bots/handlers.py`, so do not turn them into sentences.
- Validation and error messages stay clear and precise first, warm second.
- The admin panel stays professional and plain; the literary voice is for
  client-facing surfaces (client dashboard, bots, notifications).
- Dates shown to people are Jalali (شمسی); money is integer Toman.


# Final Rule

You are not only writing code.

You are maintaining GymCore as a long-term product.