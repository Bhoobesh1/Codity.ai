from datetime import datetime

from croniter import CroniterBadCronError, croniter
from pydantic import BaseModel, Field, field_validator


class ScheduledJobCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    cron_expression: str = Field(min_length=9, max_length=120)
    payload: dict = Field(default_factory=dict)

    @field_validator("cron_expression")
    @classmethod
    def validate_cron(cls, v: str) -> str:
        try:
            croniter(v)
        except (CroniterBadCronError, ValueError) as exc:
            raise ValueError(f"Invalid cron expression: {exc}") from exc
        return v


class ScheduledJobOut(BaseModel):
    id: str
    queue_id: str
    name: str
    cron_expression: str
    payload: dict
    is_active: bool
    next_run_at: datetime | None
    last_run_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
