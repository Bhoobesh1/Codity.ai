"""initial schema

Revision ID: 557cd0eb7eea
Revises:
Create Date: 2026-08-25

This migration was written by hand (rather than via `alembic revision
--autogenerate`) because this sandbox has no live Postgres instance to
reflect against. It exactly mirrors the SQLAlchemy models in app/models/,
which were validated by compiling their DDL against the Postgres dialect.
Once you run this against real Postgres (via docker-compose, see README),
you can confirm it matches the models with:
    alembic revision --autogenerate -m "check drift"
and verifying the generated file is empty.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "557cd0eb7eea"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- organizations ---
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"], unique=True)

    # --- retry_policies ---
    retry_strategy_enum = postgresql.ENUM(
        "fixed", "linear", "exponential", name="retry_strategy"
    )
    retry_strategy_enum.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "retry_policies",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("strategy", postgresql.ENUM("fixed", "linear", "exponential", name="retry_strategy", create_type=False), nullable=False),
        sa.Column("base_delay_seconds", sa.Integer(), nullable=False),
        sa.Column("max_delay_seconds", sa.Integer(), nullable=False),
        sa.Column("max_retries", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # --- workers ---
    worker_status_enum = postgresql.ENUM(
        "idle", "busy", "unhealthy", "stopped", name="worker_status"
    )
    worker_status_enum.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "workers",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("hostname", sa.String(length=255), nullable=True),
        sa.Column("max_concurrency", sa.Integer(), nullable=False),
        sa.Column("status", postgresql.ENUM("idle", "busy", "unhealthy", "stopped", name="worker_status", create_type=False), nullable=False),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_job_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- organization_members ---
    org_role_enum = postgresql.ENUM("owner", "admin", "member", name="org_role")
    org_role_enum.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "organization_members",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("role", postgresql.ENUM("owner", "admin", "member", name="org_role", create_type=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "organization_id", name="uq_user_organization"),
    )
    op.create_index("ix_organization_members_user_id", "organization_members", ["user_id"])
    op.create_index("ix_organization_members_organization_id", "organization_members", ["organization_id"])

    # --- projects ---
    op.create_table(
        "projects",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "name", name="uq_project_org_name"),
    )
    op.create_index("ix_projects_organization_id", "projects", ["organization_id"])

    # --- worker_heartbeats ---
    op.create_table(
        "worker_heartbeats",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("worker_id", sa.String(), nullable=False),
        sa.Column("status", postgresql.ENUM("idle", "busy", "unhealthy", "stopped", name="worker_status", create_type=False), nullable=False),
        sa.Column("current_job_count", sa.Integer(), nullable=False),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["worker_id"], ["workers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_worker_heartbeats_worker_id", "worker_heartbeats", ["worker_id"])
    op.create_index(
        "ix_worker_heartbeats_worker_time", "worker_heartbeats", ["worker_id", "last_heartbeat_at"]
    )

    # --- queues ---
    op.create_table(
        "queues",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("concurrency_limit", sa.Integer(), nullable=False),
        sa.Column("is_paused", sa.Boolean(), nullable=False),
        sa.Column("retry_policy_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["retry_policy_id"], ["retry_policies.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "name", name="uq_queue_project_name"),
    )
    op.create_index("ix_queues_project_id", "queues", ["project_id"])

    # --- scheduled_jobs ---
    op.create_table(
        "scheduled_jobs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("queue_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("cron_expression", sa.String(length=120), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["queue_id"], ["queues.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scheduled_jobs_queue_id", "scheduled_jobs", ["queue_id"])
    op.create_index(
        "ix_scheduled_jobs_active_next_run", "scheduled_jobs", ["is_active", "next_run_at"]
    )

    # --- jobs ---
    job_type_enum = postgresql.ENUM(
        "immediate", "delayed", "scheduled", "recurring", "batch", name="job_type"
    )
    job_type_enum.create(op.get_bind(), checkfirst=True)
    job_status_enum = postgresql.ENUM(
        "queued", "scheduled", "claimed", "running", "completed",
        "failed", "retrying", "dead_letter", name="job_status",
    )
    job_status_enum.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("queue_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("job_type", postgresql.ENUM("immediate", "delayed", "scheduled", "recurring", "batch", name="job_type", create_type=False), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("status", postgresql.ENUM("queued", "scheduled", "claimed", "running", "completed", "failed", "retrying", "dead_letter", name="job_status", create_type=False), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("max_retries", sa.Integer(), nullable=False),
        sa.Column("retry_policy_id", sa.String(), nullable=True),
        sa.Column("batch_id", sa.String(), nullable=True),
        sa.Column("scheduled_job_id", sa.String(), nullable=True),
        sa.Column("claimed_by", sa.String(), nullable=True),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["queue_id"], ["queues.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["retry_policy_id"], ["retry_policies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["scheduled_job_id"], ["scheduled_jobs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["claimed_by"], ["workers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_jobs_queue_id", "jobs", ["queue_id"])
    op.create_index("ix_jobs_batch_id", "jobs", ["batch_id"])
    op.create_index("ix_jobs_queue_status", "jobs", ["queue_id", "status"])
    op.create_index(
        "ix_jobs_status_priority_scheduled_at", "jobs", ["status", "priority", "scheduled_at"]
    )

    # --- dead_letter_queue_entries ---
    op.create_table(
        "dead_letter_queue_entries",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("queue_id", sa.String(), nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=False),
        sa.Column("retry_history", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("moved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved", sa.Boolean(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["queue_id"], ["queues.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dead_letter_queue_entries_job_id", "dead_letter_queue_entries", ["job_id"], unique=True)
    op.create_index("ix_dead_letter_queue_entries_queue_id", "dead_letter_queue_entries", ["queue_id"])

    # --- job_executions ---
    execution_status_enum = postgresql.ENUM(
        "running", "succeeded", "failed", name="execution_status"
    )
    execution_status_enum.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "job_executions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("worker_id", sa.String(), nullable=True),
        sa.Column("retry_attempt", sa.Integer(), nullable=False),
        sa.Column("status", postgresql.ENUM("running", "succeeded", "failed", name="execution_status", create_type=False), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["worker_id"], ["workers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_job_executions_job_id", "job_executions", ["job_id"])
    op.create_index("ix_job_executions_worker_id", "job_executions", ["worker_id"])
    op.create_index("ix_job_executions_job_started", "job_executions", ["job_id", "started_at"])

    # --- job_logs ---
    op.create_table(
        "job_logs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("job_execution_id", sa.String(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("level", sa.String(length=20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["job_execution_id"], ["job_executions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_job_logs_job_execution_id", "job_logs", ["job_execution_id"])
    op.create_index(
        "ix_job_logs_execution_timestamp", "job_logs", ["job_execution_id", "timestamp"]
    )


def downgrade() -> None:
    # Dropping a table also drops its indexes/constraints automatically.
    op.drop_table("job_logs")
    op.drop_table("job_executions")
    op.execute("DROP TYPE IF EXISTS execution_status")
    op.drop_table("dead_letter_queue_entries")
    op.drop_table("jobs")
    op.execute("DROP TYPE IF EXISTS job_status")
    op.execute("DROP TYPE IF EXISTS job_type")
    op.drop_table("scheduled_jobs")
    op.drop_table("queues")
    op.drop_table("worker_heartbeats")
    op.drop_table("projects")
    op.drop_table("organization_members")
    op.execute("DROP TYPE IF EXISTS org_role")
    op.drop_table("workers")
    op.execute("DROP TYPE IF EXISTS worker_status")
    op.drop_table("users")
    op.drop_table("retry_policies")
    op.execute("DROP TYPE IF EXISTS retry_strategy")
    op.drop_table("organizations")
