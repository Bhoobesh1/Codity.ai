from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import generate_uuid


class JobLog(Base):
    """
    Structured log lines emitted during a job execution. Kept as its own
    table (rather than a text blob on JobExecution) so logs can be
    streamed/appended incrementally while the job runs, and queried/paged
    independently of the execution record itself.
    """

    __tablename__ = "job_logs"
    __table_args__ = (
        Index("ix_job_logs_execution_timestamp", "job_execution_id", "timestamp"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    job_execution_id: Mapped[str] = mapped_column(
        String, ForeignKey("job_executions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    level: Mapped[str] = mapped_column(String(20), default="INFO", nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    execution: Mapped["JobExecution"] = relationship(back_populates="logs")  # noqa: F821
