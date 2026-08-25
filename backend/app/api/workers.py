from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.models.user import User
from app.repositories import worker_repository
from app.schemas.worker import WorkerOut

router = APIRouter(prefix="/workers", tags=["workers"])

# Note: workers are a system-wide resource (they pull jobs from any
# queue, not a specific organization's), so these endpoints only require
# being logged in, not membership in a particular org.


@router.get("", response_model=list[WorkerOut])
def list_workers(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[WorkerOut]:
    return worker_repository.list_all(db)


@router.get("/{worker_id}", response_model=WorkerOut)
def get_worker(
    worker_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkerOut:
    worker = worker_repository.get_by_id(db, worker_id)
    if worker is None:
        raise NotFoundError("Worker not found.")
    return worker
