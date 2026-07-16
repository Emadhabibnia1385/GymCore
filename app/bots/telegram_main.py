"""Telegram bot entrypoint: `python -m app.bots.telegram_main`."""

from app.bots.runner import run_bot
from app.models import Platform

if __name__ == "__main__":
    run_bot(Platform.TELEGRAM)
