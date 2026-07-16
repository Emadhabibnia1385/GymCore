"""Bale bot entrypoint: `python -m app.bots.bale_main`."""

from app.bots.runner import run_bot
from app.models import Platform

if __name__ == "__main__":
    run_bot(Platform.BALE)
