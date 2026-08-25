from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import JobStatus, JobType, TimestampMixin, generate_uuid, pg_enum


class Job(Base, TimestampMixin):
    """
    A single unit of work. This table holds the job's *current* state.
    Every attempt to run it is recorded separately in `job_executions`
    (see job_execution.py) so we keep a full audit trail without mutating
    history in place.
    """

    __tablename__ = "jobs"
    __table_args__ = (
        # Powers: "find jobs in this queue with this status" (dashboard filters).
        Index("ix_jobs_queue_status", "queue_id", "status"),
        # Powers: the worker claiming query in Phase 2 --
        # "find queued/scheduled jobs whose time has come, best priority first".
        Index("ix_jobs_status_priority_scheduled_at", "status", "priority", "scheduled_at"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    queue_id: Mapped[str] = mapped_column(
        String, ForeignKey("queues.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    job_type: Mapped[JobType] = mapped_column(pg_enum(JobType, "job_type"), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        pg_enum(JobStatus, "job_status"), default=JobStatus.QUEUED, nullable=False
    )

    # When the job becomes eligible to run. For IMMEDIATE jobs this is
    # set to "now" at creation time; for DELAYED/SCHEDULED jobs it's in
    # the future. The claiming query filters on this column.
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    # Optional override of the queue's default retry policy.
    retry_policy_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("retry_policies.id", ondelete="SET NULL"), nullable=True
    )

    # Groups jobs created together as part of a single batch submission
    # (job type "batch"). Nullable because most jobs aren't part of a batch.
    batch_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)

    # Set when a ScheduledJob (cron template) spawns this job instance.
    scheduled_job_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("scheduled_jobs.id", ondelete="SET NULL"), nullable=True
    )

    # --- Claiming fields, used by the worker in Phase 2 ---
    # Which worker currently holds this job (NULL if unclaimed).
    claimed_by: Mapped[str | None] = mapped_column(
        String, ForeignKey("workers.id", ondelete="SET NULL"), nullable=True
    )
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    queue: Mapped["Queue"] = relationship(back_populates="jobs")  # noqa: F821
    retry_policy: Mapped["RetryPolicy | None"] = relationship()  # noqa: F821
    executions: Mapped[list["JobExecution"]] = relationship(  # noqa: F821
        back_populates="job", cascade="all, delete-orphan"
    )
    dead_letter_entry: Mapped["DeadLetterQueueEntry | None"] = relationship(  # noqa: F821
        back_populates="job", cascade="all, delete-orphan", uselist=False
    )
