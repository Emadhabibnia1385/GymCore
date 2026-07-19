#!/usr/bin/env bash
# ============================================================================
# GymCore installer for Debian/Ubuntu.
#
#   git clone https://github.com/Emadhabibnia1385/GymCore.git
#   cd GymCore && sudo bash install.sh
#
# Safe by design: installs into a dedicated user + directory, binds the API to
# loopback on a configurable non-privileged port, and touches ONLY GymCore's own
# systemd services. It never edits nginx, firewall rules, ports 80/443, Docker,
# or any other application on this server.
# ============================================================================
set -euo pipefail

APP_USER=gymcore
APP_DIR=/opt/gymcore
DEFAULT_PORT=8815
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"

green() { printf '\033[0;32m%s\033[0m\n' "$1"; }
warn()  { printf '\033[0;33m%s\033[0m\n' "$1"; }
err()   { printf '\033[0;31m%s\033[0m\n' "$1" >&2; }

[[ $EUID -eq 0 ]] || { err "Run as root:  sudo bash install.sh"; exit 1; }
command -v apt-get >/dev/null 2>&1 || { err "This installer supports Debian/Ubuntu (apt)."; exit 1; }

green "==> GymCore installer"

# --- 1. system packages (only what we need) ---
green "==> Installing system packages (python3, venv, pip, rsync)..."
apt-get update -y
apt-get install -y --no-install-recommends python3 python3-venv python3-pip rsync

# --- 2. dedicated system user ---
if ! id "$APP_USER" >/dev/null 2>&1; then
  green "==> Creating system user '$APP_USER'..."
  useradd --system --home "$APP_DIR" --shell /usr/sbin/nologin "$APP_USER"
fi

# --- 3. install application files ---
green "==> Installing application to $APP_DIR..."
mkdir -p "$APP_DIR"
rsync -a --delete \
  --exclude '.git' --exclude '.venv' --exclude '.env' \
  --exclude '__pycache__' --exclude '*.db' --exclude 'uploads' \
  "$SRC_DIR"/ "$APP_DIR"/

# --- 4. virtualenv + pinned dependencies ---
green "==> Creating virtualenv and installing dependencies..."
python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --upgrade pip -q
"$APP_DIR/.venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"

# --- 5. environment file (secrets never printed) ---
if [[ ! -f "$APP_DIR/.env" ]]; then
  green "==> Creating .env from template..."
  cp "$APP_DIR/.env.example" "$APP_DIR/.env"
  SECRET=$(head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n')
  sed -i "s|^SECRET_KEY=.*|SECRET_KEY=${SECRET}|" "$APP_DIR/.env"
  warn ""
  warn "!! Now set these in $APP_DIR/.env (values are never shown by this script):"
  warn "     TELEGRAM_BOT_TOKEN, TELEGRAM_OWNER_IDS"
  warn "     BALE_BOT_TOKEN,     BALE_OWNER_IDS"
  warn "     DATABASE_URL   (keep the SQLite default for a simple setup)"
  warn "     APP_PORT       (default ${DEFAULT_PORT})"
  read -r -p "Press Enter to edit .env now..." _ || true
  "${EDITOR:-nano}" "$APP_DIR/.env" || true
fi
chmod 600 "$APP_DIR/.env"
chown -R "$APP_USER":"$APP_USER" "$APP_DIR"

# --- 6. port safety check (never kills the occupant) ---
read_env() { grep -E "^$1=" "$APP_DIR/.env" 2>/dev/null | cut -d= -f2- || true; }
APP_HOST=$(read_env APP_HOST); APP_HOST=${APP_HOST:-127.0.0.1}
APP_PORT=$(read_env APP_PORT); APP_PORT=${APP_PORT:-$DEFAULT_PORT}
if ss -tulpn 2>/dev/null | grep -q ":${APP_PORT} "; then
  err ""
  err "!! Port ${APP_PORT} is already in use by another service on this server."
  err "   Set a free APP_PORT in $APP_DIR/.env and run install.sh again."
  err "   Installation stopped — nothing else on this server was changed."
  exit 1
fi
green "==> Port ${APP_PORT} on ${APP_HOST} is free."

# --- 7. database migrations ---
green "==> Applying database migrations (alembic upgrade head)..."
sudo -u "$APP_USER" bash -c "cd '$APP_DIR' && '$APP_DIR/.venv/bin/alembic' upgrade head"

# --- 8. systemd services (GymCore-only, clearly named) ---
green "==> Installing systemd services..."
install -m 0644 "$APP_DIR/deploy/systemd/gymcore-api.service"    /etc/systemd/system/
install -m 0644 "$APP_DIR/deploy/systemd/gymcore-worker.service" /etc/systemd/system/

TELEGRAM_TOKEN=$(read_env TELEGRAM_BOT_TOKEN)
BALE_TOKEN=$(read_env BALE_BOT_TOKEN)
SERVICES=(gymcore-api gymcore-worker)
if [[ -n "$TELEGRAM_TOKEN" ]]; then
  install -m 0644 "$APP_DIR/deploy/systemd/gymcore-telegram.service" /etc/systemd/system/
  SERVICES+=(gymcore-telegram)
else
  warn "   (TELEGRAM_BOT_TOKEN empty — Telegram bot service not started)"
fi
if [[ -n "$BALE_TOKEN" ]]; then
  install -m 0644 "$APP_DIR/deploy/systemd/gymcore-bale.service" /etc/systemd/system/
  SERVICES+=(gymcore-bale)
else
  warn "   (BALE_BOT_TOKEN empty — Bale bot service not started)"
fi

systemctl daemon-reload
green "==> Starting GymCore services: ${SERVICES[*]}"
for svc in "${SERVICES[@]}"; do
  systemctl enable "$svc" >/dev/null 2>&1 || true
  systemctl restart "$svc"
done

# --- 9. summary ---
green ""
green "==> GymCore is installed and running."
for svc in "${SERVICES[@]}"; do
  systemctl --no-pager --lines=0 status "$svc" 2>/dev/null || true
done
green ""
green "Manage the services:"
green "  systemctl status gymcore-api"
green "  systemctl restart gymcore-telegram"
green "  journalctl -u gymcore-bale -f"
green "  journalctl -u gymcore-worker -f"
green ""
green "Health check:  curl http://${APP_HOST}:${APP_PORT}/health"
green "The bots use long polling — no public web endpoint or open port is required."
