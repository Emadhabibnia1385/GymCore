#!/usr/bin/env bash
# ============================================================================
# GymCore database backup.
#
#   sudo bash /opt/gymcore/deploy/backup.sh [--once] [label]
#
# Snapshots the database named by DATABASE_URL in /opt/gymcore/.env into
# /var/backups/gymcore — root-only and gzipped — keeping the newest BACKUP_KEEP
# (default 30). install.sh runs it before it changes anything, so every install
# and auto-update, and with them every migration, starts from a fresh copy.
#
# SQLite goes through SQLite's online backup API, which stays consistent while
# the bots write, and the copy is integrity-checked. PostgreSQL uses pg_dump,
# with credentials passed in the environment, never on the command line (other
# users on a shared server can read command lines).
#
# --once   skip if a backup with this label was made in the last 24 hours, so a
#          retried update keeps its first backup instead of rotating it out.
#
# Exits 0 when there is nothing to back up yet (no .env, or no database file),
# and non-zero when a backup was needed but could not be made.
# ============================================================================
set -euo pipefail

APP_DIR=${GYMCORE_APP_DIR:-/opt/gymcore}
BACKUP_DIR=${GYMCORE_BACKUP_DIR:-/var/backups/gymcore}
ENV_FILE="$APP_DIR/.env"

say() { printf 'backup: %s\n' "$1"; }
die() { printf 'backup: %s\n' "$1" >&2; exit 1; }

read_env() {
  grep -E "^$1=" "$ENV_FILE" 2>/dev/null | tail -n 1 | cut -d= -f2- \
    | sed -E "s/^\"(.*)\"\$/\\1/; s/^'(.*)'\$/\\1/" || true
}

ONCE=false
if [[ "${1:-}" == "--once" ]]; then
  ONCE=true
  shift
fi
LABEL=$(printf '%s' "${1:-manual}" | tr -c 'A-Za-z0-9._-' '_' | cut -c1-60)

[[ -f "$ENV_FILE" ]] || { say "no $ENV_FILE yet — nothing to back up"; exit 0; }

URL=$(read_env DATABASE_URL)
URL=${URL:-sqlite:///./gymcore.db}
KEEP=$(read_env BACKUP_KEEP)
[[ "$KEEP" =~ ^[1-9][0-9]*$ ]] || KEEP=30

if $ONCE; then
  recent=$(find "$BACKUP_DIR" -maxdepth 1 -name "gymcore-*-$LABEL.*.gz" -mmin -1440 \
    2>/dev/null | head -n 1 || true)
  if [[ -n "$recent" ]]; then
    say "already have a backup for $LABEL from the last 24h — keeping it: $recent"
    exit 0
  fi
fi

umask 077
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"
BASE="$BACKUP_DIR/gymcore-$(date -u +%Y%m%dT%H%M%SZ)-$LABEL"

case "$URL" in
  sqlite:///*)
    DB=${URL#sqlite:///}
    DB=${DB%%\?*}
    [[ "$DB" == /* ]] || DB="$APP_DIR/${DB#./}"
    [[ -f "$DB" ]] || { say "no database file at $DB yet — nothing to back up"; exit 0; }
    OUT="$BASE.db"
    python3 - "$DB" "$OUT" <<'PY' || { rm -f "$OUT"; die "SQLite backup of $DB failed"; }
import sqlite3
import sys
from pathlib import Path

source = sqlite3.connect(Path(sys.argv[1]).resolve().as_uri() + "?mode=ro", uri=True)
target = sqlite3.connect(sys.argv[2])
try:
    source.backup(target)
    result = target.execute("PRAGMA integrity_check").fetchone()[0]
finally:
    target.close()
    source.close()
if result != "ok":
    sys.exit(f"integrity check of the copy failed: {result}")
PY
    ;;
  sqlite:*)
    say "in-memory SQLite — nothing to back up"
    exit 0
    ;;
  postgresql*|postgres:*)
    command -v pg_dump >/dev/null 2>&1 \
      || die "pg_dump not found — install postgresql-client, or set BACKUP_BEFORE_UPDATE=false"
    OUT="$BASE.sql"
    python3 - "$URL" "$OUT" <<'PY' || { rm -f "$OUT"; die "pg_dump failed"; }
import os
import subprocess
import sys
from urllib.parse import parse_qs, unquote, urlsplit

url = urlsplit(sys.argv[1])
env = dict(os.environ)
for key, value in (
    ("PGHOST", url.hostname),
    ("PGPORT", url.port),
    ("PGUSER", url.username),
    ("PGPASSWORD", url.password),
    ("PGDATABASE", url.path.lstrip("/")),
):
    if value:
        env[key] = unquote(str(value))
sslmode = parse_qs(url.query).get("sslmode")
if sslmode:
    env["PGSSLMODE"] = sslmode[0]
with open(sys.argv[2], "wb") as out:
    subprocess.run(["pg_dump", "--no-owner"], stdout=out, env=env, check=True)
PY
    ;;
  *)
    die "unsupported DATABASE_URL scheme '${URL%%:*}'"
    ;;
esac

gzip -9 -f "$OUT"
chmod 600 "$OUT.gz"

# Keep only the newest $KEEP backups.
ls -1t "$BACKUP_DIR"/gymcore-*.gz 2>/dev/null | tail -n +"$((KEEP + 1))" \
  | while IFS= read -r old; do rm -f -- "$old"; done || true

say "saved $OUT.gz ($(du -h "$OUT.gz" | cut -f1))"
