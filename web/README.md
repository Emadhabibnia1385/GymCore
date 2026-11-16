# GymCore web panel

A responsive panel (phone, tablet, desktop) for the coach and for students, on the same
services and database as the Telegram and Bale bots. Persian, right to left, light and dark,
installable as an app (PWA).

- **Coach:** dashboard (income, expenses, net, who owes, today's classes, follow-ups), the student
  roster with search and filters, a student's profile (courses, money, programs), any course's grid.
- **Student:** their subscription, courses with the session grid, programs and packages (the bot
  sends files and videos to their Telegram), and a request for a course. A student never sees money.

Stack: Vite · React 19 · TanStack Router/Query · Tailwind 4 · HeroUI 3 behind the vendored
**Nasim** component library (`vendor/nasim`, never edited). UI conventions: `.claude/skills/nasim`.

## Run it on your computer

```bash
./scripts/dev_web.sh        # demo database + API on :8815 + panel on :5173
```

Open <http://localhost:5173> and press **«ورود آزمایشی به‌عنوان مربی»** (or **شاگرد**). The test login
exists only while `WEB_DEV_LOGIN=true` (the script sets it); a server never has it. Telegram's login
button can't run on `localhost`, so it appears only on a real domain registered with BotFather
(`/setdomain`).

## Develop

```bash
cd web && bun install
bun run dev         # panel with the API proxied to :8815
bun run typecheck && bun run test && bun run build
```

Sign-in: Telegram's widget → `POST /api/auth/telegram` verifies the signature → an httpOnly cookie
keeps the browser signed in for 180 days of use. Admin rights are the bot's own owner whitelist.
