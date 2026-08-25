from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.job import Job
from app.models.queue import Queue


def get_by_id(db: Session, queue_id: str) -> Queue | None:
    return db.execute(
        select(Queue).options(joinedload(Queue.retry_policy)).where(Queue.id == queue_id)
    ).scalar_one_or_none()


def create(db: Session, *, project_id: str, name: str, priority: int, concurrency_limit: int, retry_policy_id: str) -> Queue:
    queue = Queue(
        project_id=project_id,
        name=name,
        priority=priority,
        concurrency_limit=concurrency_limit,
        retry_policy_id=retry_policy_id,
    )
    db.add(queue)
    db.flush()
    return queue


def list_for_project(
    db: Session, *, project_id: str, page: int, page_size: int, is_paused: bool | None = None
) -> tuple[list[Queue], int]:
    base_query = select(Queue).where(Queue.project_id == project_id)
    if is_paused is not None:
        base_query = base_query.where(Queue.is_paused == is_paused)

    total = db.execute(select(func.count()).select_from(base_query.subquery())).scalar_one()

    items = list(
        db.execute(
            base_query.options(joinedload(Queue.retry_policy))
            .order_by(Queue.priority.desc(), Queue.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).scalars()
    )
    return items, total


def job_status_counts(db: Session, *, queue_id: str) -> dict[str, int]:
    rows = db.execute(
        select(Job.status, func.count()).where(Job.queue_id == queue_id).group_by(Job.status)
    ).all()
    return {status.value: count for status, count in rows}
