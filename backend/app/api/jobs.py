import math

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.base import JobStatus
from app.models.user import User
from app.schemas.common import Page
from app.schemas.job import JobCreate, JobExecutionOut, JobOut
from app.services import job_service

router = APIRouter(tags=["jobs"])


@router.post(
    "/queues/{queue_id}/jobs", response_model=JobOut, status_code=status.HTTP_201_CREATED
)
def create_job(
    queue_id: str,
    payload: JobCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobOut:
    return job_service.create_job(db, user_id=current_user.id, queue_id=queue_id, payload_in=payload)


@router.get("/queues/{queue_id}/jobs", response_model=Page[JobOut])
def list_jobs(
    queue_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: JobStatus | None = Query(default=None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[JobOut]:
    items, total = job_service.list_jobs_for_queue(
        db,
        user_id=current_user.id,
        queue_id=queue_id,
        page=page,
        page_size=page_size,
        status=status_filter,
    )
    return Page(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobOut:
    return job_service.get_job_for_user(db, user_id=current_user.id, job_id=job_id)


@router.post("/jobs/{job_id}/retry", response_model=JobOut)
def retry_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobOut:
    return job_service.retry_dead_letter_job(db, user_id=current_user.id, job_id=job_id)


@router.get("/jobs/{job_id}/executions", response_model=list[JobExecutionOut])
def list_job_executions(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[JobExecutionOut]:
    return job_service.list_executions_for_job(db, user_id=current_user.id, job_id=job_id)
