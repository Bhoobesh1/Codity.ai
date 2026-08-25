from datetime import datetime

from pydantic import BaseModel

from app.models.base import WorkerStatus


class WorkerOut(BaseModel):
    id: str
    name: str
    hostname: str | None
    max_concurrency: int
    status: WorkerStatus
    last_heartbeat_at: datetime | None
    current_job_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class DeadLetterEntryOut(BaseModel):
    id: str
    job_id: str
    queue_id: str
    failure_reason: str
    retry_history: list
    moved_at: datetime
    resolved: bool
    resolved_at: datetime | None

    model_config = {"from_attributes": True}
