from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import RetryStrategy, TimestampMixin, generate_uuid, pg_enum


class RetryPolicy(Base, TimestampMixin):
    """
    A reusable retry configuration. A Queue has a default RetryPolicy;
    individual Jobs may reference a different one to override it.

    delay formulas (applied by the worker/scheduler in Phase 2+):
      FIXED:       delay = base_delay_seconds
      LINEAR:      delay = base_delay_seconds * retry_count
      EXPONENTIAL: delay = base_delay_seconds * (2 ** retry_count)
    `max_delay_seconds` caps the computed delay so exponential backoff
    doesn't grow unbounded.
    """

    __tablename__ = "retry_policies"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    strategy: Mapped[RetryStrategy] = mapped_column(
        pg_enum(RetryStrategy, "retry_strategy"),
        default=RetryStrategy.EXPONENTIAL,
        nullable=False,
    )
    base_delay_seconds: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    max_delay_seconds: Mapped[int] = mapped_column(Integer, default=3600, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=5, nullable=False)

    queues: Mapped[list["Queue"]] = relationship(back_populates="retry_policy")  # noqa: F821
