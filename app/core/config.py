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


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor — import this, never instantiate Settings directly."""
    return Settings()
