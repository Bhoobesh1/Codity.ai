from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.base import ExecutionStatus
from app.models.job_execution import JobExecution
from app.models.job_log import JobLog


def start(db: Session, *, job_id: str, worker_id: str, retry_attempt: int) -> JobExecution:
    execution = JobExecution(
        job_id=job_id,
        worker_id=worker_id,
        retry_attempt=retry_attempt,
        status=ExecutionStatus.RUNNING,
        started_at=datetime.now(timezone.utc),
    )
    db.add(execution)
    db.flush()
    return execution


def finish_success(db: Session, execution: JobExecution) -> None:
    now = datetime.now(timezone.utc)
    execution.ended_at = now
    execution.duration_ms = int((now - execution.started_at).total_seconds() * 1000)
    execution.status = ExecutionStatus.SUCCEEDED


def finish_failure(db: Session, execution: JobExecution, *, error_message: str) -> None:
    now = datetime.now(timezone.utc)
    execution.ended_at = now
    execution.duration_ms = int((now - execution.started_at).total_seconds() * 1000)
    execution.status = ExecutionStatus.FAILED
    execution.error_message = error_message[:4000]  # guard against unbounded error text


def add_log(db: Session, *, execution_id: str, level: str, message: str) -> None:
    db.add(
        JobLog(
            job_execution_id=execution_id,
            timestamp=datetime.now(timezone.utc),
            level=level,
            message=message[:4000],
        )
    )


def list_for_job(db: Session, *, job_id: str) -> list[JobExecution]:
    return list(
        db.execute(
            select(JobExecution)
            .where(JobExecution.job_id == job_id)
            .order_by(JobExecution.started_at.desc())
        ).scalars()
    )
