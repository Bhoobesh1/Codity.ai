from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.models.base import ExecutionStatus, JobStatus, JobType


class JobCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255, description="Job name / handler key")
    job_type: JobType
    payload: dict = Field(default_factory=dict)
    priority: int = Field(default=0, ge=0, le=100)
    max_retries: int = Field(default=3, ge=0, le=50)

    # Only relevant for job_type == DELAYED
    delay_seconds: int | None = Field(default=None, ge=0)
    # Only relevant for job_type == SCHEDULED
    scheduled_at: datetime | None = None
    # Only relevant for job_type == BATCH -- groups jobs created in one call
    batch_id: str | None = None

    @model_validator(mode="after")
    def validate_type_specific_fields(self) -> "JobCreate":
        if self.job_type == JobType.DELAYED and self.delay_seconds is None:
            raise ValueError("delay_seconds is required for delayed jobs.")
        if self.job_type == JobType.SCHEDULED and self.scheduled_at is None:
            raise ValueError("scheduled_at is required for scheduled jobs.")
        if self.job_type == JobType.RECURRING:
            # Recurring jobs are cron *templates*, created via the
            # scheduler's endpoints (a later phase), not this one.
            raise ValueError(
                "Recurring jobs are created as ScheduledJob templates, "
                "not supported on this endpoint yet."
            )
        return self


class JobOut(BaseModel):
    id: str
    queue_id: str
    name: str
    job_type: JobType
    payload: dict
    priority: int
    status: JobStatus
    scheduled_at: datetime
    retry_count: int
    max_retries: int
    batch_id: str | None
    claimed_by: str | None
    claimed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class JobExecutionOut(BaseModel):
    id: str
    job_id: str
    worker_id: str | None
    retry_attempt: int
    status: ExecutionStatus
    started_at: datetime
    ended_at: datetime | None
    duration_ms: int | None
    error_message: str | None

    model_config = {"from_attributes": True}
