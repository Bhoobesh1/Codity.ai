from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, WorkerStatus, generate_uuid, pg_enum


class Worker(Base, TimestampMixin):
    """
    Represents one running worker process. `status` and `last_heartbeat_at`
    are denormalized copies of the latest heartbeat, kept directly on this
    row so "list workers with their current status" doesn't require a join
    or subquery. The full heartbeat history still lives in
    `worker_heartbeats` for observability/debugging.
    """

    __tablename__ = "workers"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    max_concurrency: Mapped[int] = mapped_column(Integer, default=5, nullable=False)

    status: Mapped[WorkerStatus] = mapped_column(
        pg_enum(WorkerStatus, "worker_status"), default=WorkerStatus.IDLE, nullable=False
    )
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    current_job_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    heartbeats: Mapped[list["WorkerHeartbeat"]] = relationship(
        back_populates="worker", cascade="all, delete-orphan"
    )


class WorkerHeartbeat(Base, TimestampMixin):
    """Append-only history of heartbeats, one row per heartbeat ping."""

    __tablename__ = "worker_heartbeats"
    __table_args__ = (
        # Powers: "is this worker's most recent heartbeat stale" checks.
        Index("ix_worker_heartbeats_worker_time", "worker_id", "last_heartbeat_at"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    worker_id: Mapped[str] = mapped_column(
        String, ForeignKey("workers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[WorkerStatus] = mapped_column(
        pg_enum(WorkerStatus, "worker_status"), nullable=False
    )
    current_job_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_heartbeat_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    worker: Mapped["Worker"] = relationship(back_populates="heartbeats")
