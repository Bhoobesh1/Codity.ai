from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class DeadLetterQueueEntry(Base, TimestampMixin):
    """
    Created when a Job exhausts its max_retries. `retry_history` is a
    JSONB snapshot (attempt number, error, timestamp) taken at the moment
    the job dies -- stored redundantly with JobExecution rows so the DLQ
    entry remains a complete, self-contained record even if execution
    history is later pruned/archived.
    """

    __tablename__ = "dead_letter_queue_entries"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    job_id: Mapped[str] = mapped_column(
        String, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    queue_id: Mapped[str] = mapped_column(
        String, ForeignKey("queues.id", ondelete="CASCADE"), nullable=False, index=True
    )

    failure_reason: Mapped[str] = mapped_column(Text, nullable=False)
    retry_history: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    moved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    job: Mapped["Job"] = relationship(back_populates="dead_letter_entry")  # noqa: F821
