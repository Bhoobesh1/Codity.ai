from datetime import datetime

from pydantic import BaseModel, Field

from app.models.base import RetryStrategy


class RetryPolicyIn(BaseModel):
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    base_delay_seconds: int = Field(default=5, ge=1)
    max_delay_seconds: int = Field(default=3600, ge=1)
    max_retries: int = Field(default=5, ge=0, le=50)


class RetryPolicyOut(BaseModel):
    id: str
    strategy: RetryStrategy
    base_delay_seconds: int
    max_delay_seconds: int
    max_retries: int

    model_config = {"from_attributes": True}


class QueueCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    priority: int = Field(default=0, ge=0, le=100)
    concurrency_limit: int = Field(default=5, ge=1, le=1000)
    retry_policy: RetryPolicyIn = Field(default_factory=RetryPolicyIn)


class QueueUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    priority: int | None = Field(default=None, ge=0, le=100)
    concurrency_limit: int | None = Field(default=None, ge=1, le=1000)


class QueueOut(BaseModel):
    id: str
    project_id: str
    name: str
    priority: int
    concurrency_limit: int
    is_paused: bool
    retry_policy: RetryPolicyOut | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class QueueStats(BaseModel):
    queue_id: str
    total_jobs: int
    queued: int
    running: int
    completed: int
    failed: int
    retrying: int
    dead_letter: int
