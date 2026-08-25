from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import ExecutionStatus, TimestampMixin, generate_uuid, pg_enum


class JobExecution(Base, TimestampMixin):
    """
    One row per *attempt* to run a Job. retry_attempt=0 is the first try,
    1 is the first retry, etc. This is what execution history / metrics
    (avg duration, failure rate) query against.
    """

    __tablename__ = "job_executions"
    __table_args__ = (
        # Powers: "show me execution history for this job, most recent first".
        Index("ix_job_executions_job_started", "job_id", "started_at"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    job_id: Mapped[str] = mapped_column(
        String, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    worker_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("workers.id", ondelete="SET NULL"), nullable=True, index=True
    )

    retry_attempt: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[ExecutionStatus] = mapped_column(
        pg_enum(ExecutionStatus, "execution_status"),
        default=ExecutionStatus.RUNNING,
        nullable=False,
    )

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    job: Mapped["Job"] = relationship(back_populates="executions")  # noqa: F821
    logs: Mapped[list["JobLog"]] = relationship(  # noqa: F821
        back_populates="execution", cascade="all, delete-orphan"
    )
