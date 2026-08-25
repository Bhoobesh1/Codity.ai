# Entity-Relationship Diagram

```mermaid
erDiagram
    USERS ||--o{ ORGANIZATION_MEMBERS : "belongs to orgs via"
    ORGANIZATIONS ||--o{ ORGANIZATION_MEMBERS : "has members"
    ORGANIZATIONS ||--o{ PROJECTS : "owns"
    PROJECTS ||--o{ QUEUES : "contains"
    RETRY_POLICIES ||--o{ QUEUES : "default policy for"
    RETRY_POLICIES ||--o{ JOBS : "optionally overrides for"
    QUEUES ||--o{ JOBS : "contains"
    QUEUES ||--o{ SCHEDULED_JOBS : "has cron templates"
    SCHEDULED_JOBS ||--o{ JOBS : "spawns instances"
    JOBS ||--o{ JOB_EXECUTIONS : "has attempts"
    JOB_EXECUTIONS ||--o{ JOB_LOGS : "has log lines"
    JOBS ||--o| DEAD_LETTER_QUEUE_ENTRIES : "may have"
    WORKERS ||--o{ JOB_EXECUTIONS : "runs"
    WORKERS ||--o{ WORKER_HEARTBEATS : "has history"
    WORKERS ||--o{ JOBS : "currently claims"

    USERS {
        string id PK
        string email UK
        string hashed_password
        string full_name
        bool is_active
    }
    ORGANIZATIONS {
        string id PK
        string name
        string slug UK
    }
    ORGANIZATION_MEMBERS {
        string id PK
        string user_id FK
        string organization_id FK
        enum role "owner, admin, member"
    }
    PROJECTS {
        string id PK
        string organization_id FK
        string name
        string description
    }
    RETRY_POLICIES {
        string id PK
        string name
        enum strategy "fixed, linear, exponential"
        int base_delay_seconds
        int max_delay_seconds
        int max_retries
    }
    QUEUES {
        string id PK
        string project_id FK
        string name
        int priority
        int concurrency_limit
        bool is_paused
        string retry_policy_id FK
    }
    SCHEDULED_JOBS {
        string id PK
        string queue_id FK
        string name
        string cron_expression
        jsonb payload
        bool is_active
        timestamp next_run_at
        timestamp last_run_at
    }
    JOBS {
        string id PK
        string queue_id FK
        string name
        enum job_type "immediate, delayed, scheduled, recurring, batch"
        jsonb payload
        int priority
        enum status "queued, scheduled, claimed, running, completed, failed, retrying, dead_letter"
        timestamp scheduled_at
        int retry_count
        int max_retries
        string retry_policy_id FK
        string batch_id
        string scheduled_job_id FK
        string claimed_by FK
        timestamp claimed_at
    }
    JOB_EXECUTIONS {
        string id PK
        string job_id FK
        string worker_id FK
        int retry_attempt
        enum status "running, succeeded, failed"
        timestamp started_at
        timestamp ended_at
        int duration_ms
        string error_message
    }
    JOB_LOGS {
        string id PK
        string job_execution_id FK
        timestamp timestamp
        string level
        string message
    }
    WORKERS {
        string id PK
        string name
        string hostname
        int max_concurrency
        enum status "idle, busy, unhealthy, stopped"
        timestamp last_heartbeat_at
        int current_job_count
    }
    WORKER_HEARTBEATS {
        string id PK
        string worker_id FK
        enum status
        int current_job_count
        timestamp last_heartbeat_at
    }
    DEAD_LETTER_QUEUE_ENTRIES {
        string id PK
        string job_id FK UK
        string queue_id FK
        string failure_reason
        jsonb retry_history
        timestamp moved_at
        bool resolved
        timestamp resolved_at
    }
```

## Notable design choices

- **UUID primary keys everywhere**, not auto-increment integers. In a
  system with multiple independent processes (API replicas, workers,
  scheduler) potentially inserting rows concurrently, UUIDs avoid any
  chance of ID collision without needing a shared sequence, and they
  don't leak volume information (`/jobs/4821` tells a client nothing
  about job #4821 the way an integer would hint at "the 4821st job ever
  created").
- **`JobExecution` is separate from `Job`.** `Job` holds *current*
  state; every attempt to run it is its own row in `JobExecution`. This
  is what makes execution history, retry counts, and average-duration
  metrics possible without mutating history in place.
- **`ScheduledJob` is separate from `Job`.** A cron template
  ("run every day at 2am") and an actual unit of work are different
  things with different lifecycles — conflating them would mean
  awkwardly resetting a "completed" job back to "queued" forever instead
  of spawning fresh rows.
- **`DeadLetterQueueEntry` stores a JSON snapshot of retry history**,
  redundant with the `JobExecution` rows, so a DLQ entry remains a
  complete, self-contained audit record even if execution history is
  later pruned or archived.

See `backend/app/models/*.py` for the full column-by-column definitions,
and each model file's docstrings/comments for the reasoning behind
individual indexes.
