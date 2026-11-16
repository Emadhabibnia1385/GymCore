#!/usr/bin/env bash
# Build the web panel (web/) into web/dist, which nginx serves.
#
# Best effort by design: the bots and the API matter more than the panel, so a failed
# build never fails an update — the previous web/dist (if any) keeps serving. The build
# goes to dist.new and is swapped in at the end, so visitors never see a half-built panel.
set -uo pipefail

APP_DIR="${GYMCORE_APP_DIR:-/opt/gymcore}"
APP_USER="${GYMCORE_APP_USER:-gymcore}"
WEB="$APP_DIR/web"

[ -f "$WEB/package.json" ] || exit 0
command -v bun >/dev/null 2>&1 || { echo "web: bun is not installed — skipping the panel build"; exit 0; }

as_app() {
  sudo -u "$APP_USER" env HOME="$APP_DIR" BUN_INSTALL_CACHE_DIR="$APP_DIR/.bun-cache" \
    bash -c "cd '$WEB' && $1"
}

if as_app 'bun install --frozen-lockfile --silent' \
   && as_app 'bunx vite build --outDir dist.new --emptyOutDir'; then
  rm -rf "$WEB/dist.old"
  [ -d "$WEB/dist" ] && mv "$WEB/dist" "$WEB/dist.old"
  mv "$WEB/dist.new" "$WEB/dist"
  rm -rf "$WEB/dist.old"
  echo "web: panel built"
else
  rm -rf "$WEB/dist.new"
  echo "web: the panel build failed — the previous panel (if any) keeps serving"
fi
exit 0
