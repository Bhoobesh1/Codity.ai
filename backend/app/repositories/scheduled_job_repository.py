from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.scheduled_job import ScheduledJob


def get_by_id(db: Session, scheduled_job_id: str) -> ScheduledJob | None:
    return db.get(ScheduledJob, scheduled_job_id)


def create(
    db: Session,
    *,
    queue_id: str,
    name: str,
    cron_expression: str,
    payload: dict,
    next_run_at: datetime,
) -> ScheduledJob:
    obj = ScheduledJob(
        queue_id=queue_id,
        name=name,
        cron_expression=cron_expression,
        payload=payload,
        next_run_at=next_run_at,
    )
    db.add(obj)
    db.flush()
    return obj


def list_for_queue(db: Session, *, queue_id: str) -> list[ScheduledJob]:
    return list(
        db.execute(
            select(ScheduledJob)
            .where(ScheduledJob.queue_id == queue_id)
            .order_by(ScheduledJob.created_at.desc())
        ).scalars()
    )


def list_due(db: Session, *, now: datetime) -> list[ScheduledJob]:
    """
    Locks due, active templates with SKIP LOCKED for the same reason job
    claiming does: if more than one scheduler process is running, this
    guarantees each due template is picked up by exactly one of them per
    tick, instead of two processes both spawning a duplicate Job.
    """
    return list(
        db.execute(
            select(ScheduledJob)
            .where(ScheduledJob.is_active.is_(True), ScheduledJob.next_run_at <= now)
            .with_for_update(skip_locked=True)
        ).scalars()
    )
