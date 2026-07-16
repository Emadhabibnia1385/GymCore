#!/usr/bin/env bash
# ============================================================
# GymCore one-command installer for Ubuntu (Docker-based).
#
#   git clone https://github.com/Emadhabibnia1385/GymCore.git
#   cd GymCore && sudo bash install.sh
# ============================================================
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Run as root: sudo bash install.sh"
  exit 1
fi

echo "==> GymCore installer"

# --- 1. Docker ---
if ! command -v docker >/dev/null 2>&1; then
  echo "==> Installing Docker..."
  curl -fsSL https://get.docker.com | sh
fi
if ! docker compose version >/dev/null 2>&1; then
  echo "==> Installing docker compose plugin..."
  apt-get update -y && apt-get install -y docker-compose-plugin
fi

# --- 2. Environment file ---
if [[ ! -f .env ]]; then
  cp .env.example .env
  # Generate a strong secret key automatically.
  SECRET=$(head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n')
  sed -i "s/^SECRET_KEY=.*/SECRET_KEY=${SECRET}/" .env
  PGPASS=$(head -c 16 /dev/urandom | od -An -tx1 | tr -d ' \n')
  sed -i "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=${PGPASS}/" .env
  sed -i "s|^DATABASE_URL=.*|DATABASE_URL=postgresql+psycopg://gymcore:${PGPASS}@db:5432/gymcore|" .env

  echo ""
  echo "!! .env created. Now fill in the remaining values:"
  echo "   TELEGRAM_BOT_TOKEN, TELEGRAM_OWNER_ID"
  echo "   BALE_BOT_TOKEN, BALE_OWNER_ID"
  echo "   ADMIN_PHONE, ADMIN_PASSWORD, DOMAIN"
  echo ""
  read -r -p "Press Enter to edit .env now..." _
  "${EDITOR:-nano}" .env
fi

# --- 3. Port conflict check ---
HTTP_PORT=$(grep -E '^HTTP_PORT=' .env | cut -d= -f2)
HTTP_PORT=${HTTP_PORT:-80}
if ss -tlnp 2>/dev/null | grep -q ":${HTTP_PORT} "; then
  echo ""
  echo "!! Port ${HTTP_PORT} is already in use by another service."
  echo "   Set a free port in .env, e.g.:  HTTP_PORT=8090"
  read -r -p "Press Enter to edit .env and change HTTP_PORT..." _
  "${EDITOR:-nano}" .env
  HTTP_PORT=$(grep -E '^HTTP_PORT=' .env | cut -d= -f2)
  HTTP_PORT=${HTTP_PORT:-80}
fi

# --- 4. Build & start ---
echo "==> Building and starting services..."
docker compose up -d --build

PORT_SUFFIX=""
[[ "${HTTP_PORT}" != "80" ]] && PORT_SUFFIX=":${HTTP_PORT}"
echo ""
echo "==> GymCore is running."
echo "    Admin panel:      http://<server-ip>${PORT_SUFFIX}/admin"
echo "    Client dashboard: http://<server-ip>${PORT_SUFFIX}/"
echo "    API docs:         http://<server-ip>${PORT_SUFFIX}/docs"
echo ""
echo "    Logs:    docker compose logs -f"
echo "    Update:  git pull && docker compose up -d --build"
