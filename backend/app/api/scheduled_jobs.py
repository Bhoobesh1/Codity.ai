from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.scheduled_job import ScheduledJobCreate, ScheduledJobOut
from app.services import scheduled_job_service

router = APIRouter(tags=["scheduled-jobs"])


@router.post(
    "/queues/{queue_id}/scheduled-jobs",
    response_model=ScheduledJobOut,
    status_code=status.HTTP_201_CREATED,
)
def create_scheduled_job(
    queue_id: str,
    payload: ScheduledJobCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ScheduledJobOut:
    return scheduled_job_service.create_scheduled_job(
        db,
        user_id=current_user.id,
        queue_id=queue_id,
        name=payload.name,
        cron_expression=payload.cron_expression,
        payload=payload.payload,
    )


@router.get("/queues/{queue_id}/scheduled-jobs", response_model=list[ScheduledJobOut])
def list_scheduled_jobs(
    queue_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ScheduledJobOut]:
    return scheduled_job_service.list_scheduled_jobs_for_queue(
        db, user_id=current_user.id, queue_id=queue_id
    )


@router.post("/scheduled-jobs/{scheduled_job_id}/pause", response_model=ScheduledJobOut)
def pause_scheduled_job(
    scheduled_job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ScheduledJobOut:
    return scheduled_job_service.set_active(
        db, user_id=current_user.id, scheduled_job_id=scheduled_job_id, active=False
    )


@router.post("/scheduled-jobs/{scheduled_job_id}/resume", response_model=ScheduledJobOut)
def resume_scheduled_job(
    scheduled_job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ScheduledJobOut:
    return scheduled_job_service.set_active(
        db, user_id=current_user.id, scheduled_job_id=scheduled_job_id, active=True
    )
