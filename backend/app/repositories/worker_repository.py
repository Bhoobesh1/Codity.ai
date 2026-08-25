from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.base import WorkerStatus
from app.models.worker import Worker, WorkerHeartbeat


def get_by_id(db: Session, worker_id: str) -> Worker | None:
    return db.get(Worker, worker_id)


def register(db: Session, *, name: str, hostname: str | None, max_concurrency: int) -> Worker:
    worker = Worker(
        name=name,
        hostname=hostname,
        max_concurrency=max_concurrency,
        status=WorkerStatus.IDLE,
        last_heartbeat_at=datetime.now(timezone.utc),
    )
    db.add(worker)
    db.commit()
    db.refresh(worker)
    return worker


def record_heartbeat(
    db: Session, *, worker_id: str, status: WorkerStatus, current_job_count: int
) -> None:
    """
    Updates the denormalized fields on Worker (fast path for "list
    workers with current status") and appends a row to WorkerHeartbeat
    (the append-only history used for observability/debugging).
    """
    now = datetime.now(timezone.utc)
    worker = db.get(Worker, worker_id)
    if worker is None:
        return
    worker.status = status
    worker.last_heartbeat_at = now
    worker.current_job_count = current_job_count

    db.add(
        WorkerHeartbeat(
            worker_id=worker_id,
            status=status,
            current_job_count=current_job_count,
            last_heartbeat_at=now,
        )
    )
    db.commit()


def mark_stopped(db: Session, *, worker_id: str) -> None:
    db.execute(
        update(Worker).where(Worker.id == worker_id).values(status=WorkerStatus.STOPPED)
    )
    db.commit()


def list_all(db: Session) -> list[Worker]:
    return list(db.execute(select(Worker).order_by(Worker.created_at.desc())).scalars())


def mark_unhealthy_workers(db: Session, *, timeout_seconds: int) -> list[str]:
    """
    Flags any worker (not already STOPPED) whose last heartbeat is older
    than `timeout_seconds` as UNHEALTHY. Returns the list of worker ids
    that were just marked unhealthy, so the caller can requeue their jobs.

    This is a single atomic UPDATE -- safe to call concurrently from
    multiple workers/reaper tasks without a race, since Postgres
    serializes the row updates within the statement itself.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=timeout_seconds)
    result = db.execute(
        update(Worker)
        .where(
            Worker.status != WorkerStatus.STOPPED,
            Worker.status != WorkerStatus.UNHEALTHY,
            Worker.last_heartbeat_at < cutoff,
        )
        .values(status=WorkerStatus.UNHEALTHY)
        .returning(Worker.id)
    )
    ids = [row[0] for row in result]
    db.commit()
    return ids
