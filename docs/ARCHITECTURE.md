# Architecture

## System overview

The system is four independently deployable processes sharing one
PostgreSQL database, which is also the coordination mechanism between
them — there's no separate message broker or lock service.

```mermaid
flowchart TB
    subgraph Clients
        FE[React Dashboard]
        API_CLIENT[API clients / curl]
    end

    subgraph Backend
        API[FastAPI app<br/>stateless, N replicas]
        W1[Worker process]
        W2[Worker process]
        W3[Worker process N]
        SCHED[Scheduler process]
    end

    DB[(PostgreSQL)]

    FE -->|HTTPS + JWT| API
    API_CLIENT -->|HTTPS + JWT| API
    API -->|SQLAlchemy| DB
    W1 -->|SELECT FOR UPDATE SKIP LOCKED| DB
    W2 -->|SELECT FOR UPDATE SKIP LOCKED| DB
    W3 -->|SELECT FOR UPDATE SKIP LOCKED| DB
    SCHED -->|spawn due Jobs| DB
```

## Why this shape

**The API never touches job execution.** `POST /queues/{id}/jobs` just
inserts a row with `status=QUEUED`. It has no idea when or by which
worker that job will run. This decoupling is what lets workers scale
independently of API traffic, and it's why the API can stay fully
stateless (any replica can serve any request).

**Workers are dumb pollers, on purpose.** Each worker's loop is: send a
heartbeat, try to claim jobs, run whatever it claimed, repeat. There's
no leader election, no worker-to-worker communication, no shared
in-memory state. All coordination between workers happens through
short, atomic Postgres transactions (see `job_repository.claim_jobs`).
This is simple to reason about and correct under crashes: a worker that
dies mid-poll just... stops running its loop. Nothing else needs to
know it existed until its heartbeat goes stale.

**The scheduler is separate from workers**, even though it's also a
polling loop, because it does a fundamentally different job: workers
*consume* the job queue, the scheduler *produces* new jobs onto it (by
turning cron templates into `Job` rows). Merging them would mean every
worker replica also re-evaluates every cron template on every poll —
wasteful, and it complicates reasoning about "did this cron job already
fire this minute" once you have N workers instead of 1.

## Request lifecycle: submitting and running a job

```mermaid
sequenceDiagram
    participant User
    participant API
    participant DB as PostgreSQL
    participant Worker

    User->>API: POST /queues/{id}/jobs
    API->>DB: INSERT jobs (status=QUEUED)
    API-->>User: 201 Created

    loop every 2s
        Worker->>DB: BEGIN
        Worker->>DB: SELECT ... FOR UPDATE SKIP LOCKED
        Worker->>DB: UPDATE status=CLAIMED, claimed_by=worker_id
        Worker->>DB: COMMIT
    end

    Worker->>DB: UPDATE status=RUNNING
    Worker->>Worker: run handler(payload)
    alt success
        Worker->>DB: INSERT job_executions (SUCCEEDED)
        Worker->>DB: UPDATE jobs status=COMPLETED
    else failure, retries remain
        Worker->>DB: INSERT job_executions (FAILED)
        Worker->>DB: UPDATE jobs status=QUEUED, scheduled_at=now()+backoff
    else failure, retries exhausted
        Worker->>DB: INSERT job_executions (FAILED)
        Worker->>DB: UPDATE jobs status=DEAD_LETTER
        Worker->>DB: INSERT dead_letter_queue_entries
    end
```

## Crash recovery

```mermaid
sequenceDiagram
    participant Worker as Worker A (crashes)
    participant DB as PostgreSQL
    participant OtherWorker as Worker B (reaper)

    Worker->>DB: heartbeat (t=0s)
    Note over Worker: process killed at t=5s
    Note over Worker: no more heartbeats

    loop every 15s
        OtherWorker->>DB: UPDATE workers SET status='unhealthy'<br/>WHERE last_heartbeat_at < now() - 30s
    end
    OtherWorker->>DB: SELECT jobs WHERE claimed_by IN (unhealthy workers)
    OtherWorker->>DB: UPDATE jobs SET status='queued', claimed_by=NULL
    Note over DB: job is now claimable by any worker again
```

Every worker runs this recovery check on its own timer (every 15s by
default), so it doesn't depend on any single "coordinator" process
being alive — if the whole fleet restarts, whichever worker comes up
first will run the check.

## Deployment topology (docker-compose)

- `db` — PostgreSQL 16
- `api` — FastAPI, stateless, horizontally scalable
- `worker` — scalable independently (`docker compose up --scale worker=N`)
- `scheduler` — normally 1 replica; safe to run more (its due-template
  query also uses `SKIP LOCKED`), just unnecessary at small scale
- `frontend` — Vite dev server (a real deployment would build static
  assets and serve them from a CDN/static host instead)
