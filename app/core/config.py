"""Application configuration.

All secrets and environment-specific values are read from `.env`
(see `.env.example`). Nothing is hardcoded anywhere else in the code.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Application ---
    app_name: str = "GymCore"
    debug: bool = False
    domain: str = "localhost"
    # Secret used to sign auth tokens. MUST be overridden in production.
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days
    cookie_secure: bool = False  # set True once HTTPS is configured
    # Comma-separated browser origins allowed to call the API cross-origin
    # (a future SPA / web mobile client). Empty = same-origin only, which
    # is the safe default; native mobile apps are not subject to CORS.
    cors_origins: str = ""

    # --- Database ---
    # Production: postgresql+psycopg://user:pass@host:5432/gymcore
    # Development fallback: local SQLite file.
    database_url: str = "sqlite:///./gymcore.db"

    # --- File storage (plan attachments) ---
    upload_dir: Path = Path("uploads")

    # --- Telegram bot ---
    telegram_bot_token: str = ""
    telegram_owner_id: str = ""
    telegram_api_base: str = "https://api.telegram.org"

    # --- Bale bot (Telegram-compatible Bot API) ---
    bale_bot_token: str = ""
    bale_owner_id: str = ""
    bale_api_base: str = "https://tapi.bale.ai"

    # --- Bootstrap admin (created on first startup if missing) ---
    admin_name: str = "مدیر"
    admin_phone: str = ""
    admin_password: str = ""

    # --- Automated reminders (background worker) ---
    reminders_enabled: bool = True
    # How often the worker scans for due reminders.
    reminder_interval_seconds: int = 6 * 60 * 60  # every 6 hours
    # Warn the client when remaining sessions drop to/below this count.
    reminder_low_session_threshold: int = 2
    # Nudge the client when an active course has had no attendance for this
    # many days (measured from the last session, or the course start date).
    reminder_inactive_days: int = 10
    # Don't resend the same reminder kind for the same course within this
    # many days (spam guard).
    reminder_resend_days: int = 3

    @property
    def cors_origin_list(self) -> list[str]:
        """`cors_origins` parsed into a clean list (empty when unset)."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_sqlite(self) -> bool:
        """True for the local SQLite dev/test database.

        Schema is auto-created for SQLite; Postgres is managed by Alembic.
        """
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor — import this, never instantiate Settings directly."""
    return Settings()
