import logging
from datetime import datetime, timezone

from croniter import croniter
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.base import JobType
from app.models.scheduled_job import ScheduledJob
from app.repositories import job_repository, scheduled_job_repository
from app.services.queue_service import get_queue_for_user

logger = logging.getLogger(__name__)


def _next_run(cron_expression: str, *, base: datetime) -> datetime:
    return croniter(cron_expression, base).get_next(datetime)


def create_scheduled_job(
    db: Session, *, user_id: str, queue_id: str, name: str, cron_expression: str, payload: dict
) -> ScheduledJob:
    queue = get_queue_for_user(db, user_id=user_id, queue_id=queue_id)
    now = datetime.now(timezone.utc)
    obj = scheduled_job_repository.create(
        db,
        queue_id=queue.id,
        name=name,
        cron_expression=cron_expression,
        payload=payload,
        next_run_at=_next_run(cron_expression, base=now),
    )
    db.commit()
    db.refresh(obj)
    return obj


def list_scheduled_jobs_for_queue(db: Session, *, user_id: str, queue_id: str) -> list[ScheduledJob]:
    get_queue_for_user(db, user_id=user_id, queue_id=queue_id)
    return scheduled_job_repository.list_for_queue(db, queue_id=queue_id)


def set_active(db: Session, *, user_id: str, scheduled_job_id: str, active: bool) -> ScheduledJob:
    obj = scheduled_job_repository.get_by_id(db, scheduled_job_id)
    if obj is None:
        raise NotFoundError("Scheduled job not found.")
    get_queue_for_user(db, user_id=user_id, queue_id=obj.queue_id)
    obj.is_active = active
    db.commit()
    db.refresh(obj)
    return obj


def run_scheduler_tick(db: Session) -> int:
    """
    Called periodically (see app/scheduler/loop.py). Finds every active
    cron template that's due, spawns a Job instance for it, and advances
    next_run_at to the following occurrence. Returns how many jobs were
    spawned.
    """
    now = datetime.now(timezone.utc)
    due = scheduled_job_repository.list_due(db, now=now)
    if not due:
        return 0

    for template in due:
        job = job_repository.create(
            db,
            queue_id=template.queue_id,
            name=template.name,
            job_type=JobType.RECURRING,
            payload=dict(template.payload),
            priority=0,
            max_retries=3,
            scheduled_at=now,
            batch_id=None,
        )
        job.retry_policy_id = template.queue.retry_policy_id
        template.last_run_at = now
        template.next_run_at = _next_run(template.cron_expression, base=now)
        logger.info(
            "Spawned job from scheduled template %s, next run at %s",
            template.id,
            template.next_run_at,
        )

    db.commit()
    return len(due)
