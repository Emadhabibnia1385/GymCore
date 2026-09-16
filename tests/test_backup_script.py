"""deploy/backup.sh — the database backup install.sh takes before every update.

Runs the real script against a throwaway app dir, so CI checks the shell as well
as the Python it embeds. Needs bash and gzip (Linux / macOS).
"""

import gzip
import os
import shutil
import sqlite3
import stat
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "deploy" / "backup.sh"
DEFAULT_URL = "sqlite:///./gymcore.db"

pytestmark = pytest.mark.skipif(
    shutil.which("bash") is None or shutil.which("gzip") is None,
    reason="needs bash and gzip",
)


def _app(tmp_path, database_url=DEFAULT_URL, extra_env=""):
    app = tmp_path / "app"
    app.mkdir()
    (app / ".env").write_text(f"DATABASE_URL={database_url}\n{extra_env}", encoding="utf-8")
    if database_url == DEFAULT_URL:
        db = sqlite3.connect(app / "gymcore.db")
        db.execute("CREATE TABLE persons (id INTEGER PRIMARY KEY, name TEXT)")
        db.executemany("INSERT INTO persons (name) VALUES (?)", [("a",), ("b",), ("c",)])
        db.commit()
        db.close()
    return app


def _run(app, backups, *args):
    env = {**os.environ, "GYMCORE_APP_DIR": str(app), "GYMCORE_BACKUP_DIR": str(backups)}
    return subprocess.run(
        ["bash", str(SCRIPT), *args], env=env, capture_output=True, text=True, timeout=60
    )


def test_backs_up_a_sqlite_database_privately(tmp_path):
    app, backups = _app(tmp_path), tmp_path / "backups"
    result = _run(app, backups, "5214604-to-7c1e9aa")
    assert result.returncode == 0, result.stderr

    [backup] = backups.glob("gymcore-*-5214604-to-7c1e9aa.db.gz")
    assert stat.S_IMODE(backups.stat().st_mode) == 0o700
    assert stat.S_IMODE(backup.stat().st_mode) == 0o600

    restored = tmp_path / "restored.db"
    restored.write_bytes(gzip.decompress(backup.read_bytes()))
    db = sqlite3.connect(restored)
    assert db.execute("SELECT count(*) FROM persons").fetchone()[0] == 3
    assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    db.close()


def test_keeps_only_the_newest_backups(tmp_path):
    app, backups = _app(tmp_path, extra_env="BACKUP_KEEP=2\n"), tmp_path / "backups"
    for label in ("one", "two", "three"):
        assert _run(app, backups, label).returncode == 0
    assert len(list(backups.glob("gymcore-*.gz"))) == 2


def test_a_retried_update_keeps_its_first_backup(tmp_path):
    app, backups = _app(tmp_path), tmp_path / "backups"
    assert _run(app, backups, "--once", "aaa-to-bbb").returncode == 0
    retry = _run(app, backups, "--once", "aaa-to-bbb")
    assert retry.returncode == 0
    assert "already" in retry.stdout
    assert len(list(backups.glob("gymcore-*-aaa-to-bbb.db.gz"))) == 1


def test_nothing_to_back_up_before_the_first_install(tmp_path):
    backups = tmp_path / "backups"
    assert _run(tmp_path / "not-installed", backups).returncode == 0
    assert not backups.exists()


def test_a_database_not_created_yet_is_not_an_error(tmp_path):
    app = _app(tmp_path, database_url="sqlite:///./not-created-yet.db")
    assert _run(app, tmp_path / "backups").returncode == 0


def test_an_unsupported_database_fails_without_echoing_credentials(tmp_path):
    app = _app(tmp_path, database_url="mysql://gym:hunter2@db/gymcore")
    result = _run(app, tmp_path / "backups")
    assert result.returncode != 0
    assert "hunter2" not in result.stdout + result.stderr


def test_a_failed_postgres_dump_stops_and_leaves_nothing_behind(tmp_path):
    # Port 1 refuses at once; with no pg_dump installed the script stops sooner.
    app = _app(tmp_path, database_url="postgresql+psycopg://gym:hunter2@127.0.0.1:1/gymcore")
    backups = tmp_path / "backups"
    result = _run(app, backups)
    assert result.returncode != 0
    assert "hunter2" not in result.stdout + result.stderr
    assert not list(backups.glob("*.sql*"))
