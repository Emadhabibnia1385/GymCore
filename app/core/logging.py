"""Central logging configuration with secret redaction.

Every entrypoint (API, telegram bot, bale bot, worker) calls `setup_logging()`
once. A redaction filter guarantees bot tokens / secrets never reach the logs,
even if an exception message or URL happens to contain one.
"""

from __future__ import annotations

import logging
import sys

from app.core.config import get_settings

_LEVELS = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
}

_REDACTION = "***REDACTED***"


class _RedactSecretsFilter(logging.Filter):
    """Replace known secret values in any log record with a placeholder."""

    def __init__(self, secrets: tuple[str, ...]):
        super().__init__()
        self._secrets = tuple(s for s in secrets if s)

    def filter(self, record: logging.LogRecord) -> bool:
        if not self._secrets:
            return True
        try:
            message = record.getMessage()
        except Exception:
            return True
        redacted = message
        for secret in self._secrets:
            if secret in redacted:
                redacted = redacted.replace(secret, _REDACTION)
        if redacted != message:
            record.msg = redacted
            record.args = ()
        return True


def setup_logging(level: int | None = None) -> None:
    settings = get_settings()
    resolved = level if level is not None else _LEVELS.get(settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=resolved,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True,
    )
    redactor = _RedactSecretsFilter(settings.secret_values)
    root = logging.getLogger()
    for handler in root.handlers:
        handler.addFilter(redactor)
    # Silence noisy third-party loggers.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
