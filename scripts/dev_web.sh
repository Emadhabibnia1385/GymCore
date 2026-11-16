#!/usr/bin/env bash
# Run the whole web panel locally: a demo database, the API on :8815 and the panel on :5173.
#   ./scripts/dev_web.sh        → open http://localhost:5173 and press «ورود آزمایشی»
# Nothing here touches a real database or a server; the test login exists only in this process.
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-python3}"
DEMO_DIR="${DEMO_DIR:-.demo}"
mkdir -p "$DEMO_DIR"
DB="$DEMO_DIR/demo.db"
[ -f "$DB" ] || "$PY" scripts/seed_demo.py "$DB"

export DATABASE_URL="sqlite:///$DB" TELEGRAM_OWNER_IDS=111 TELEGRAM_BOT_TOKEN= \
       WEB_COOKIE_SECURE=false WEB_DEV_LOGIN=true
"$PY" -m uvicorn app.api.main:app --port 8815 &
API=$!
trap 'kill $API 2>/dev/null' EXIT
(cd web && bun install --silent && exec bunx vite --port 5173)
