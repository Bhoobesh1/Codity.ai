"""
The scheduler process. Run with:  python -m app.scheduler.loop

Separate from the worker process on purpose: workers claim and execute
jobs; the scheduler's only job is to notice when a cron template is due
and spawn a Job instance for it. Running it as its own lightweight
process means it can run as a single replica (or several -- the
SKIP LOCKED query in scheduled_job_repository.list_due makes multiple
scheduler instances safe too) without competing with worker capacity.
"""

import logging
import time

from app.core.database import SessionLocal
from app.core.logging import configure_logging
from app.services.scheduled_job_service import run_scheduler_tick

logger = logging.getLogger(__name__)

TICK_INTERVAL_SECONDS = 5


def main() -> None:
    configure_logging()
    logger.info("Scheduler starting, tick every %ds", TICK_INTERVAL_SECONDS)
    while True:
        db = SessionLocal()
        try:
            spawned = run_scheduler_tick(db)
            if spawned:
                logger.info("Scheduler tick spawned %d job(s)", spawned)
        except Exception:  # noqa: BLE001
            logger.exception("Scheduler tick failed")
        finally:
            db.close()
        time.sleep(TICK_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
