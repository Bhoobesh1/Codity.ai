"""
Recovery from worker crashes.

If a worker dies mid-job (process killed, host crashes, network
partition), its claimed/running jobs would otherwise sit stuck forever
-- nothing else would ever pick them up, since they're not in QUEUED
status. This module detects that situation via missed heartbeats and
requeues the affected jobs.

Design decision: requeuing a stale job does NOT consume one of the
job's retry attempts. A missed heartbeat is an infrastructure failure,
not a failure of the job's own logic, so it wouldn't be fair to burn
down `max_retries` for something the job didn't cause. We still record
a JobExecution row marking the abandoned attempt as FAILED, purely for
observability (so "why did this take 3 attempts" stays answerable).
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.base import ExecutionStatus, JobStatus
from app.models.job import Job
from app.models.job_execution import JobExecution
from app.repositories import worker_repository

logger = logging.getLogger(__name__)


def recover_stale_jobs(db: Session, *, heartbeat_timeout_seconds: int = 30) -> int:
    """
    1. Mark any worker whose heartbeat is older than the timeout as
       UNHEALTHY (single atomic UPDATE, safe under concurrent callers).
    2. Requeue any CLAIMED/RUNNING job that belongs to a now-unhealthy
       worker, and close out its dangling JobExecution row as FAILED.

    Returns the number of jobs recovered. Safe to call repeatedly/on a
    timer from every worker process -- if two workers race to run this,
    the UPDATEs are still atomic per-row, so a job only gets requeued
    once.
    """
    unhealthy_worker_ids = worker_repository.mark_unhealthy_workers(
        db, timeout_seconds=heartbeat_timeout_seconds
    )
    if not unhealthy_worker_ids:
        return 0

    stale_jobs = list(
        db.execute(
            select(Job).where(
                Job.status.in_([JobStatus.CLAIMED, JobStatus.RUNNING]),
                Job.claimed_by.in_(unhealthy_worker_ids),
            )
        ).scalars()
    )

    now = datetime.now(timezone.utc)
    for job in stale_jobs:
        open_execution = db.execute(
            select(JobExecution)
            .where(JobExecution.job_id == job.id, JobExecution.status == ExecutionStatus.RUNNING)
            .order_by(JobExecution.started_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        if open_execution is not None:
            open_execution.status = ExecutionStatus.FAILED
            open_execution.ended_at = now
            open_execution.error_message = "Worker heartbeat lost; job requeued for recovery."

        job.status = JobStatus.QUEUED
        job.claimed_by = None
        job.claimed_at = None

        logger.warning("Recovered stale job %s from crashed worker", job.id)

    db.commit()
    return len(stale_jobs)
