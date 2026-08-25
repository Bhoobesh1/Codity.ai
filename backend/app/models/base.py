"""
Shared building blocks for all ORM models: a timestamp mixin and the
enum types used across multiple tables.

Why a mixin: `created_at` / `updated_at` are needed on almost every table.
Defining them once and inheriting avoids copy-pasting the same two columns
into a dozen model files.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column


def pg_enum(enum_cls: type[enum.Enum], name: str) -> SAEnum:
    """
    Build a SQLAlchemy Enum column type that stores each member's *value*
    ("owner") rather than its *name* ("OWNER").

    Why this matters: by default SQLAlchemy's Enum type persists
    `member.name`, not `member.value`. Since our enums are defined as
    `class OrgRole(str, enum.Enum): OWNER = "owner"`, that default would
    try to write "OWNER" into a Postgres enum type that only allows
    "owner" -- and fail. `values_callable` makes it write member.value
    instead, matching the lowercase values used in the Alembic migration.
    """
    return SAEnum(enum_cls, name=name, values_callable=lambda cls: [e.value for e in cls])


def generate_uuid() -> str:
    """We use string UUIDs (not integers) as primary keys.

    Why: in a distributed system, integer auto-increment IDs are a poor fit
    -- multiple services/workers could theoretically create records
    independently, and UUIDs avoid ID collisions and don't leak how many
    rows exist (e.g. "job #4" tells a client nothing).
    """
    return str(uuid.uuid4())


class TimestampMixin:
    """Adds created_at / updated_at columns, managed by the database itself."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class JobType(str, enum.Enum):
    IMMEDIATE = "immediate"
    DELAYED = "delayed"
    SCHEDULED = "scheduled"
    RECURRING = "recurring"
    BATCH = "batch"


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    SCHEDULED = "scheduled"
    CLAIMED = "claimed"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD_LETTER = "dead_letter"


class RetryStrategy(str, enum.Enum):
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"


class WorkerStatus(str, enum.Enum):
    IDLE = "idle"
    BUSY = "busy"
    UNHEALTHY = "unhealthy"
    STOPPED = "stopped"


class ExecutionStatus(str, enum.Enum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class OrgRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
