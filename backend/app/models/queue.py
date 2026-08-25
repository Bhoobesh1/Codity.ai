from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid


class Queue(Base, TimestampMixin):
    __tablename__ = "queues"
    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_queue_project_name"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    concurrency_limit: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    is_paused: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    retry_policy_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("retry_policies.id", ondelete="SET NULL"), nullable=True
    )

    project: Mapped["Project"] = relationship(back_populates="queues")  # noqa: F821
    retry_policy: Mapped["RetryPolicy"] = relationship(back_populates="queues")  # noqa: F821
    # Cascade note: deleting a Queue deletes its Jobs. In a real production
    # system you'd likely soft-delete or archive instead -- flagged in the
    # design decisions doc later -- but for this project's scope hard
    # cascade keeps referential integrity simple.
    jobs: Mapped[list["Job"]] = relationship(  # noqa: F821
        back_populates="queue", cascade="all, delete-orphan"
    )
    scheduled_jobs: Mapped[list["ScheduledJob"]] = relationship(  # noqa: F821
        back_populates="queue", cascade="all, delete-orphan"
    )
