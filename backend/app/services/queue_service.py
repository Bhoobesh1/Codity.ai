from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.base import JobStatus
from app.models.queue import Queue
from app.models.retry_policy import RetryPolicy
from app.repositories import queue_repository
from app.schemas.queue import RetryPolicyIn
from app.services.project_service import get_project_for_user


def create_queue(
    db: Session,
    *,
    user_id: str,
    project_id: str,
    name: str,
    priority: int,
    concurrency_limit: int,
    retry_policy_in: RetryPolicyIn,
) -> Queue:
    # Raises NotFoundError if the user can't access this project --
    # reused so queue authorization always follows project authorization.
    get_project_for_user(db, user_id=user_id, project_id=project_id)

    retry_policy = RetryPolicy(
        name=f"{name}-default",
        strategy=retry_policy_in.strategy,
        base_delay_seconds=retry_policy_in.base_delay_seconds,
        max_delay_seconds=retry_policy_in.max_delay_seconds,
        max_retries=retry_policy_in.max_retries,
    )
    db.add(retry_policy)
    db.flush()

    queue = queue_repository.create(
        db,
        project_id=project_id,
        name=name,
        priority=priority,
        concurrency_limit=concurrency_limit,
        retry_policy_id=retry_policy.id,
    )
    db.commit()
    db.refresh(queue)
    return queue


def get_queue_for_user(db: Session, *, user_id: str, queue_id: str) -> Queue:
    queue = queue_repository.get_by_id(db, queue_id)
    if queue is None:
        raise NotFoundError("Queue not found.")
    # Reuses project-level authorization -- a queue is only visible to
    # users who can see its parent project.
    get_project_for_user(db, user_id=user_id, project_id=queue.project_id)
    return queue


def list_queues_for_project(
    db: Session,
    *,
    user_id: str,
    project_id: str,
    page: int,
    page_size: int,
    is_paused: bool | None,
) -> tuple[list[Queue], int]:
    get_project_for_user(db, user_id=user_id, project_id=project_id)
    return queue_repository.list_for_project(
        db, project_id=project_id, page=page, page_size=page_size, is_paused=is_paused
    )


def update_queue(
    db: Session,
    *,
    user_id: str,
    queue_id: str,
    name: str | None,
    priority: int | None,
    concurrency_limit: int | None,
) -> Queue:
    queue = get_queue_for_user(db, user_id=user_id, queue_id=queue_id)
    if name is not None:
        queue.name = name
    if priority is not None:
        queue.priority = priority
    if concurrency_limit is not None:
        queue.concurrency_limit = concurrency_limit
    db.commit()
    db.refresh(queue)
    return queue


def set_paused(db: Session, *, user_id: str, queue_id: str, paused: bool) -> Queue:
    queue = get_queue_for_user(db, user_id=user_id, queue_id=queue_id)
    queue.is_paused = paused
    db.commit()
    db.refresh(queue)
    return queue


def get_queue_stats(db: Session, *, user_id: str, queue_id: str) -> dict:
    queue = get_queue_for_user(db, user_id=user_id, queue_id=queue_id)
    counts = queue_repository.job_status_counts(db, queue_id=queue.id)

    def c(status: JobStatus) -> int:
        return counts.get(status.value, 0)

    return {
        "queue_id": queue.id,
        "total_jobs": sum(counts.values()),
        "queued": c(JobStatus.QUEUED) + c(JobStatus.SCHEDULED) + c(JobStatus.CLAIMED),
        "running": c(JobStatus.RUNNING),
        "completed": c(JobStatus.COMPLETED),
        "failed": c(JobStatus.FAILED),
        "retrying": c(JobStatus.RETRYING),
        "dead_letter": c(JobStatus.DEAD_LETTER),
    }
