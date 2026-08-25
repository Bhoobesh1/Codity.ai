"""
Minimal structured-ish logging setup. Every log line includes a
timestamp, level, and logger name (module), which is enough to trace
what happened without pulling in a heavier structured-logging library
for a learning project. Called once from app/main.py at startup.
"""

import logging
import sys

from app.core.config import settings


def configure_logging() -> None:
    logging.basicConfig(
        level=settings.LOG_LEVEL,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        stream=sys.stdout,
    )
    # Quiet down noisy third-party loggers unless we're debugging.
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.LOG_LEVEL == "DEBUG" else logging.WARNING
    )
