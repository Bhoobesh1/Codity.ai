from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class ScheduledJob(Base, TimestampMixin):
    """
    A recurring-job *template* defined by a cron expression, e.g.
    "0 2 * * *" (every day at 2am). The scheduler service (Phase 4) polls
    for templates that are due and creates a new `Job` row from them --
    this table itself never transitions through the job lifecycle, only
    the Job instances it spawns do.
    """

    __tablename__ = "scheduled_jobs"
    __table_args__ = (
        # Powers: the scheduler's "what's due right now" scan.
        Index("ix_scheduled_jobs_active_next_run", "is_active", "next_run_at"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    queue_id: Mapped[str] = mapped_column(
        String, ForeignKey("queues.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    cron_expression: Mapped[str] = mapped_column(String(120), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    queue: Mapped["Queue"] = relationship(back_populates="scheduled_jobs")  # noqa: F821
