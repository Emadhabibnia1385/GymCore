"""Application configuration.

All secrets and environment-specific values are read from `.env`
(see `.env.example`). Nothing is hardcoded anywhere else in the code.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def parse_owner_ids(raw: str) -> tuple[int, ...]:
    """Parse a comma/semicolon/space separated list of numeric IDs.

    Invalid fragments are ignored (never crash startup over a typo), and the
    result is de-duplicated while preserving order.
    """
    seen: dict[int, None] = {}
    for part in raw.replace(";", ",").replace(" ", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            seen.setdefault(int(part), None)
        except ValueError:
            continue
    return tuple(seen)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Application ---
    app_name: str = "GymCore"
    # Safe default bind: loopback only (bots use long polling, no public port).
    app_host: str = "127.0.0.1"
    app_port: int = 8815
    app_domain: str = ""
    app_base_url: str = ""
    debug: bool = False
    log_level: str = "INFO"
    timezone: str = "Asia/Tehran"
    # Secret used for internal signing / idempotency salting.
    secret_key: str = "change-me-in-production"

    # --- Database ---
    # Production: postgresql+psycopg://user:pass@host:5432/gymcore
    # Development fallback: local SQLite file.
    database_url: str = "sqlite:///./gymcore.db"

    # --- File storage (plan attachments) ---
    upload_dir: Path = Path("uploads")
    max_upload_mb: int = 20

    # --- Telegram bot ---
    telegram_bot_token: str = ""
    telegram_owner_ids: str = ""
    telegram_bot_mode: str = "polling"
    telegram_api_base: str = "https://api.telegram.org"

    # --- Bale bot (Telegram-compatible Bot API) ---
    bale_bot_token: str = ""
    bale_owner_ids: str = ""
    bale_bot_mode: str = "polling"
    bale_api_base: str = "https://tapi.bale.ai"

    # --- Plan-order signup (opened when a client taps «سفارش برنامه») ---
    signup_url: str = "https://mahdisarmad.ir/signup/"

    # --- Automated reminders (background worker) ---
    reminders_enabled: bool = True
    reminder_interval_seconds: int = 6 * 60 * 60  # every 6 hours
    low_session_threshold: int = 2
    reminder_inactive_days: int = 10
    reminder_resend_days: int = 3

    @property
    def telegram_owner_id_list(self) -> tuple[int, ...]:
        return parse_owner_ids(self.telegram_owner_ids)

    @property
    def bale_owner_id_list(self) -> tuple[int, ...]:
        return parse_owner_ids(self.bale_owner_ids)

    @property
    def is_sqlite(self) -> bool:
        """True for the local SQLite dev/test database.

        Schema is auto-created for SQLite; Postgres is managed by Alembic.
        """
        return self.database_url.startswith("sqlite")

    @property
    def max_upload_bytes(self) -> int:
        return max(self.max_upload_mb, 1) * 1024 * 1024

    @property
    def secret_values(self) -> tuple[str, ...]:
        """Secrets that must never appear in logs (see core.logging)."""
        return tuple(
            v
            for v in (self.telegram_bot_token, self.bale_bot_token, self.secret_key)
            if v and v != "change-me-in-production"
        )


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor — import this, never instantiate Settings directly."""
    return Settings()
