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


# Final Rule

You are not only writing code.

You are maintaining GymCore as a long-term product.