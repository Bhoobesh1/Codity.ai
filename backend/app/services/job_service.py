from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.base import JobStatus, JobType
from app.models.job import Job
from app.models.job_execution import JobExecution
from app.repositories import job_execution_repository, job_repository
from app.schemas.job import JobCreate
from app.services.queue_service import get_queue_for_user


def create_job(db: Session, *, user_id: str, queue_id: str, payload_in: JobCreate) -> Job:
    queue = get_queue_for_user(db, user_id=user_id, queue_id=queue_id)

    if payload_in.job_type == JobType.DELAYED:
        scheduled_at = datetime.now(timezone.utc) + timedelta(seconds=payload_in.delay_seconds)
    elif payload_in.job_type == JobType.SCHEDULED:
        scheduled_at = payload_in.scheduled_at
    else:  # IMMEDIATE, BATCH
        scheduled_at = datetime.now(timezone.utc)

    job = job_repository.create(
        db,
        queue_id=queue.id,
        name=payload_in.name,
        job_type=payload_in.job_type,
        payload=payload_in.payload,
        priority=payload_in.priority,
        max_retries=payload_in.max_retries,
        scheduled_at=scheduled_at,
        batch_id=payload_in.batch_id,
    )
    # Jobs inherit their queue's retry policy by default. (A future
    # enhancement could let JobCreate override this per-job.)
    job.retry_policy_id = queue.retry_policy_id
    db.commit()
    db.refresh(job)
    return job


def get_job_for_user(db: Session, *, user_id: str, job_id: str) -> Job:
    job = job_repository.get_by_id(db, job_id)
    if job is None:
        raise NotFoundError("Job not found.")
    # Reuses queue-level (-> project -> org) authorization.
    get_queue_for_user(db, user_id=user_id, queue_id=job.queue_id)
    return job


def list_jobs_for_queue(
    db: Session,
    *,
    user_id: str,
    queue_id: str,
    page: int,
    page_size: int,
    status: JobStatus | None,
) -> tuple[list[Job], int]:
    get_queue_for_user(db, user_id=user_id, queue_id=queue_id)
    return job_repository.list_for_queue(
        db, queue_id=queue_id, page=page, page_size=page_size, status=status
    )


def list_executions_for_job(db: Session, *, user_id: str, job_id: str) -> list[JobExecution]:
    get_job_for_user(db, user_id=user_id, job_id=job_id)
    return job_execution_repository.list_for_job(db, job_id=job_id)


def retry_dead_letter_job(db: Session, *, user_id: str, job_id: str) -> Job:
    """
    Manually retries a job sitting in the Dead Letter Queue. Resets its
    retry count to give it a full fresh set of attempts -- the
    alternative (keep the old count and let it immediately return to the
    DLQ after zero further attempts) would make "manual retry" a no-op,
    which isn't what a human clicking "retry" expects.
    """
    job = get_job_for_user(db, user_id=user_id, job_id=job_id)
    if job.status != JobStatus.DEAD_LETTER:
        raise ConflictError("Only jobs in the Dead Letter Queue can be manually retried.")

    job.status = JobStatus.QUEUED
    job.retry_count = 0
    job.claimed_by = None
    job.claimed_at = None
    job.scheduled_at = datetime.now(timezone.utc)

    if job.dead_letter_entry is not None:
        job.dead_letter_entry.resolved = True
        job.dead_letter_entry.resolved_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(job)
    return job
