from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.base import ExecutionStatus, JobStatus, WorkerStatus
from app.models.job import Job
from app.models.job_execution import JobExecution
from app.models.worker import Worker


def job_counts_for_queues(db: Session, *, queue_ids: list[str]) -> dict[str, int]:
    if not queue_ids:
        return {}
    rows = db.execute(
        select(Job.status, func.count())
        .where(Job.queue_id.in_(queue_ids))
        .group_by(Job.status)
    ).all()
    return {status.value: count for status, count in rows}


def retried_job_count(db: Session, *, queue_ids: list[str]) -> int:
    if not queue_ids:
        return 0
    return db.execute(
        select(func.count())
        .select_from(Job)
        .where(Job.queue_id.in_(queue_ids), Job.retry_count > 0)
    ).scalar_one()


def average_execution_time_ms(db: Session, *, queue_ids: list[str]) -> float | None:
    if not queue_ids:
        return None
    result = db.execute(
        select(func.avg(JobExecution.duration_ms))
        .select_from(JobExecution)
        .join(Job, Job.id == JobExecution.job_id)
        .where(
            Job.queue_id.in_(queue_ids),
            JobExecution.status == ExecutionStatus.SUCCEEDED,
            JobExecution.duration_ms.is_not(None),
        )
    ).scalar_one()
    return float(result) if result is not None else None


def queue_throughput(db: Session, *, queue_ids: list[str], window_hours: int = 24) -> dict[str, int]:
    """Completed jobs per queue in the last `window_hours`."""
    if not queue_ids:
        return {}
    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    rows = db.execute(
        select(Job.queue_id, func.count())
        .where(
            Job.queue_id.in_(queue_ids),
            Job.status == JobStatus.COMPLETED,
            Job.updated_at >= cutoff,
        )
        .group_by(Job.queue_id)
    ).all()
    return {queue_id: count for queue_id, count in rows}


def worker_counts(db: Session) -> dict[str, int]:
    """
    Worker health is a system-wide/global concept (a worker isn't scoped
    to one user's projects -- it pulls from any queue) so this isn't
    filtered by queue_ids, unlike the job metrics above.
    """
    rows = db.execute(select(Worker.status, func.count()).group_by(Worker.status)).all()
    counts = {status.value: count for status, count in rows}
    active = counts.get(WorkerStatus.IDLE.value, 0) + counts.get(WorkerStatus.BUSY.value, 0)
    return {
        "active": active,
        "unhealthy": counts.get(WorkerStatus.UNHEALTHY.value, 0),
        "total": sum(counts.values()),
    }
