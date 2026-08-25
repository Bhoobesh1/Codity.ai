"""
Executes a single claimed job and decides what happens next:
COMPLETED, requeued with backoff (QUEUED + a future scheduled_at), or
moved to the Dead Letter Queue once retries are exhausted.

This is deliberately synchronous and takes a single `Job` already in
CLAIMED status -- the worker process (app/workers/worker.py) is
responsible for claiming jobs and calling this once per job, optionally
across a thread pool for concurrency.
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.base import JobStatus
from app.models.dead_letter_queue import DeadLetterQueueEntry
from app.models.job import Job
from app.repositories import job_execution_repository
from app.workers.handlers import get_handler
from app.workers.retry import compute_retry_delay_seconds

logger = logging.getLogger(__name__)


def execute_job(db: Session, *, job: Job, worker_id: str) -> None:
    """
    Runs job.name's handler against job.payload. Mutates `job` and
    commits every outcome. Idempotency note: handlers are expected to be
    idempotent where possible (see design decisions doc) since a job can
    in principle be executed more than once (e.g. it completes but the
    worker crashes before persisting the COMPLETED status) -- this
    project doesn't implement exactly-once delivery, only at-least-once,
    which is the honest, common trade-off for this class of system.
    """
    job.status = JobStatus.RUNNING
    db.commit()

    execution = job_execution_repository.start(
        db, job_id=job.id, worker_id=worker_id, retry_attempt=job.retry_count
    )
    db.commit()

    handler = get_handler(job.name)
    payload = dict(job.payload)
    payload["__retry_count__"] = job.retry_count

    try:
        handler(payload)
    except Exception as exc:  # noqa: BLE001 -- handler failures are expected, not bugs
        _handle_failure(db, job=job, execution=execution, error=exc)
        return

    job_execution_repository.finish_success(db, execution)
    job.status = JobStatus.COMPLETED
    db.commit()
    logger.info("Job %s completed successfully", job.id)


def _handle_failure(db: Session, *, job: Job, execution, error: Exception) -> None:
    job_execution_repository.finish_failure(db, execution, error_message=str(error))

    retry_policy = job.retry_policy
    max_retries = job.max_retries
    # A queue-level (or job-level) retry policy governs the *delay*
    # between attempts; max_retries always comes from the job itself so
    # each job can independently cap its own attempts regardless of
    # which policy it borrows timing from.

    if job.retry_count < max_retries:
        delay_seconds = (
            compute_retry_delay_seconds(retry_policy, retry_count=job.retry_count)
            if retry_policy is not None
            else 5 * (2**job.retry_count)
        )
        job.retry_count += 1
        job.status = JobStatus.QUEUED
        job.claimed_by = None
        job.claimed_at = None
        job.scheduled_at = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
        db.commit()
        logger.info(
            "Job %s failed (attempt %d/%d), retrying in %ds",
            job.id,
            job.retry_count,
            max_retries,
            delay_seconds,
        )
        return

    # Retries exhausted -> Dead Letter Queue.
    history = [
        {
            "retry_attempt": e.retry_attempt,
            "status": e.status.value,
            "error_message": e.error_message,
            "started_at": e.started_at.isoformat(),
            "ended_at": e.ended_at.isoformat() if e.ended_at else None,
        }
        for e in job_execution_repository.list_for_job(db, job_id=job.id)
    ]
    job.status = JobStatus.DEAD_LETTER
    job.claimed_by = None
    job.claimed_at = None
    db.add(
        DeadLetterQueueEntry(
            job_id=job.id,
            queue_id=job.queue_id,
            failure_reason=str(error)[:4000],
            retry_history=history,
            moved_at=datetime.now(timezone.utc),
        )
    )
    db.commit()
    logger.warning("Job %s exhausted retries, moved to Dead Letter Queue", job.id)
