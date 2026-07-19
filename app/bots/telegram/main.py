"""Telegram bot entrypoint: `python -m app.bots.telegram.main`."""

from app.bots.common.runner import run_bot
from app.models import Platform

if __name__ == "__main__":
    run_bot(Platform.TELEGRAM)
