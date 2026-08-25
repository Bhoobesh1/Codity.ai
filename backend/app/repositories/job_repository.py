from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.base import JobStatus
from app.models.job import Job
from app.models.queue import Queue


def get_by_id(db: Session, job_id: str) -> Job | None:
    return db.get(Job, job_id)


def create(
    db: Session,
    *,
    queue_id: str,
    name: str,
    job_type,
    payload: dict,
    priority: int,
    max_retries: int,
    scheduled_at: datetime,
    batch_id: str | None,
) -> Job:
    job = Job(
        queue_id=queue_id,
        name=name,
        job_type=job_type,
        payload=payload,
        priority=priority,
        max_retries=max_retries,
        status=JobStatus.QUEUED,
        scheduled_at=scheduled_at,
        batch_id=batch_id,
    )
    db.add(job)
    db.flush()
    return job


def list_for_queue(
    db: Session, *, queue_id: str, page: int, page_size: int, status: JobStatus | None
) -> tuple[list[Job], int]:
    base_query = select(Job).where(Job.queue_id == queue_id)
    if status is not None:
        base_query = base_query.where(Job.status == status)

    total = db.execute(select(func.count()).select_from(base_query.subquery())).scalar_one()
    items = list(
        db.execute(
            base_query.order_by(Job.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).scalars()
    )
    return items, total


def _queue_headroom(db: Session) -> dict[str, int]:
    """
    Returns {queue_id: free_slots} for every non-paused queue that has at
    least one free slot, where free_slots = concurrency_limit minus the
    number of jobs currently CLAIMED or RUNNING in that queue.

    This is a plain read (no locking) -- it's a snapshot used to decide
    which queues are even worth considering. The actual safety against
    over-claiming comes from re-checking headroom in Python as we walk
    the locked candidate rows below.
    """
    running_counts = dict(
        db.execute(
            select(Job.queue_id, func.count())
            .where(Job.status.in_([JobStatus.CLAIMED, JobStatus.RUNNING]))
            .group_by(Job.queue_id)
        ).all()
    )
    queues = db.execute(
        select(Queue.id, Queue.concurrency_limit).where(Queue.is_paused.is_(False))
    ).all()

    headroom = {}
    for queue_id, limit in queues:
        free = limit - running_counts.get(queue_id, 0)
        if free > 0:
            headroom[queue_id] = free
    return headroom


def claim_jobs(db: Session, *, worker_id: str, max_jobs: int) -> list[Job]:
    """
    Atomically claim up to `max_jobs` due jobs, respecting each queue's
    concurrency_limit, and commits the claim.

    How this prevents double-claiming across workers:
    `SELECT ... FOR UPDATE SKIP LOCKED` locks each matching row as it's
    selected. If another worker's transaction is concurrently running the
    same query and has already locked a row, this query simply skips that
    row instead of blocking on it -- so two workers can run this query at
    the same moment and are guaranteed to walk away with *disjoint* sets
    of jobs, with neither one waiting on the other. Without SKIP LOCKED,
    the second worker would block until the first transaction commits,
    then re-read the (now already-claimed) row and correctly not claim
    it -- SKIP LOCKED just makes that non-blocking, which matters a lot
    when many workers are polling constantly.
    """
    headroom = _queue_headroom(db)
    if not headroom:
        return []

    now = datetime.now(timezone.utc)
    # Over-fetch a bit since some candidates may fall in an already-full
    # queue by the time we walk the list in Python.
    candidates = list(
        db.execute(
            select(Job)
            .where(
                Job.status.in_([JobStatus.QUEUED, JobStatus.RETRYING]),
                Job.scheduled_at <= now,
                Job.queue_id.in_(list(headroom.keys())),
            )
            .order_by(Job.priority.desc(), Job.scheduled_at.asc())
            .limit(max_jobs * 4)
            .with_for_update(skip_locked=True)
        ).scalars()
    )

    claimed: list[Job] = []
    for job in candidates:
        if len(claimed) >= max_jobs:
            break
        if headroom.get(job.queue_id, 0) <= 0:
            continue  # this queue's concurrency limit is already spoken for
        job.status = JobStatus.CLAIMED
        job.claimed_by = worker_id
        job.claimed_at = now
        headroom[job.queue_id] -= 1
        claimed.append(job)

    db.commit()
    for job in claimed:
        db.refresh(job)
    return claimed
