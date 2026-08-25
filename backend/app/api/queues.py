import math

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.common import Page
from app.schemas.queue import QueueCreate, QueueOut, QueueStats, QueueUpdate
from app.services import queue_service

router = APIRouter(tags=["queues"])


@router.post(
    "/projects/{project_id}/queues", response_model=QueueOut, status_code=status.HTTP_201_CREATED
)
def create_queue(
    project_id: str,
    payload: QueueCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QueueOut:
    return queue_service.create_queue(
        db,
        user_id=current_user.id,
        project_id=project_id,
        name=payload.name,
        priority=payload.priority,
        concurrency_limit=payload.concurrency_limit,
        retry_policy_in=payload.retry_policy,
    )


@router.get("/projects/{project_id}/queues", response_model=Page[QueueOut])
def list_queues(
    project_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    is_paused: bool | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[QueueOut]:
    items, total = queue_service.list_queues_for_project(
        db,
        user_id=current_user.id,
        project_id=project_id,
        page=page,
        page_size=page_size,
        is_paused=is_paused,
    )
    return Page(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.get("/queues/{queue_id}", response_model=QueueOut)
def get_queue(
    queue_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QueueOut:
    return queue_service.get_queue_for_user(db, user_id=current_user.id, queue_id=queue_id)


@router.put("/queues/{queue_id}", response_model=QueueOut)
def update_queue(
    queue_id: str,
    payload: QueueUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QueueOut:
    return queue_service.update_queue(
        db,
        user_id=current_user.id,
        queue_id=queue_id,
        name=payload.name,
        priority=payload.priority,
        concurrency_limit=payload.concurrency_limit,
    )


@router.post("/queues/{queue_id}/pause", response_model=QueueOut)
def pause_queue(
    queue_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QueueOut:
    return queue_service.set_paused(db, user_id=current_user.id, queue_id=queue_id, paused=True)


@router.post("/queues/{queue_id}/resume", response_model=QueueOut)
def resume_queue(
    queue_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QueueOut:
    return queue_service.set_paused(db, user_id=current_user.id, queue_id=queue_id, paused=False)


@router.get("/queues/{queue_id}/stats", response_model=QueueStats)
def queue_stats(
    queue_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QueueStats:
    return queue_service.get_queue_stats(db, user_id=current_user.id, queue_id=queue_id)
