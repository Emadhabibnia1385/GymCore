#!/usr/bin/env bash
# ============================================================================
# GymCore auto-update: check GitHub, and if origin/main moved, pull + reinstall.
# Run by the gymcore-update.timer (every minute). Does nothing when up to date.
# ============================================================================
set -euo pipefail

REPO_URL="https://github.com/Emadhabibnia1385/GymCore.git"
SRC="/opt/gymcore-src"

command -v git >/dev/null 2>&1 || exit 0

if [ ! -d "$SRC/.git" ]; then
  git clone --depth 20 "$REPO_URL" "$SRC" || exit 0
fi

git -C "$SRC" fetch --quiet origin main || exit 0
LOCAL="$(git -C "$SRC" rev-parse HEAD 2>/dev/null || echo none)"
REMOTE="$(git -C "$SRC" rev-parse origin/main 2>/dev/null || echo none)"

if [ "$REMOTE" != "none" ] && [ "$LOCAL" != "$REMOTE" ]; then
  logger -t gymcore-update "update ${LOCAL:0:7} -> ${REMOTE:0:7}; applying" 2>/dev/null || true
  git -C "$SRC" reset --hard origin/main
  # install.sh reinstalls + restarts; it runs non-interactively here (no tty,
  # .env already exists) so it never prompts.
  bash "$SRC/install.sh"
  logger -t gymcore-update "update applied (${REMOTE:0:7})" 2>/dev/null || true
fi
