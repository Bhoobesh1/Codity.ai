# Design Decisions — Distributed Job Scheduler

> **Note on assumptions:** The README describes the platform's behavior but not its exact tech stack. This document assumes a fairly common implementation — Node.js/TypeScript API, PostgreSQL, a React dashboard, and Docker Compose for orchestration — consistent with the project's setup instructions. Swap in your actual stack names where they differ; the underlying trade-offs still apply.

## 1. Overall Architecture

**Decision:** A single backend API service + a separate worker process, both reading from one shared PostgreSQL database, rather than a microservices split or a message-broker-based pipeline (e.g., SQS/RabbitMQ/Kafka).

**Why:**
- The database itself acts as the durable queue. Postgres row storage plus row-level locking is enough to get "exactly-once claim" semantics without operating a second piece of infrastructure.
- Keeping API and worker as two deployable units (not one monolith) means workers can be scaled horizontally and independently from the request-serving tier.
- A single source of truth (Postgres) makes job state, retry history, and metrics trivially queryable for the dashboard — no need to reconcile state across a broker and a database.

**Trade-off accepted:** Postgres-as-queue does not scale to the same throughput as Kafka/SQS for very high job volumes (tens of thousands of jobs/sec), and polling introduces latency between "job ready" and "job picked up." This was accepted because the assignment prioritizes reliability and correctness over extreme throughput. A message broker is listed as a future improvement path if volume grows.

## 2. Atomic Job Claiming (avoiding duplicate execution)

**Decision:** Workers claim jobs using `SELECT ... FOR UPDATE SKIP LOCKED` inside a transaction, immediately flipping status from `queued` to `claimed` and stamping `claimed_by_worker_id` + `claimed_at` before releasing the row.

**Why:**
- `SKIP LOCKED` lets N workers poll the same table concurrently without blocking on each other — a worker that hits a row already locked by another worker simply skips it and grabs the next eligible row.
- This avoids the classic "two workers read the same row, both think they own it" race that plain `SELECT` + `UPDATE` is vulnerable to.

**Alternative considered:** Optimistic concurrency via a `lock_version` integer, where the claim is a conditional `UPDATE ... WHERE status = 'queued' AND lock_version = N`. This was kept as a secondary safety net (the `lock_version` column exists in the schema) in case the platform later needs to claim jobs from a read replica or a non-transactional context — the version check still prevents a stale claim from succeeding.

**Trade-off:** Row-level locking works well up to a moderate number of concurrent workers per queue; beyond that, contention on "hot" queues could become a bottleneck. Queue sharding (splitting one logical queue across multiple physical partitions) is called out as a future improvement for exactly this reason.

## 3. Job Lifecycle & Idempotency

**Decision:** The lifecycle is `Queued → Scheduled → Claimed → Running → Completed | Failed`, with `Failed` looping back to `Queued` (with a delay) until `max_attempts` is exhausted, at which point the job moves to `Dead Letter Queue`.

**Why a single `status` field instead of separate boolean flags:** A single enum-like status column is queried far more cheaply (one indexed column vs. combinations of booleans) and makes invalid state combinations (e.g., "completed" and "running" both true) structurally impossible.

**Idempotency:** The platform does not guarantee jobs run exactly once end-to-end (a worker can crash mid-execution after doing real work but before reporting completion) — it guarantees jobs are *claimed* exactly once at any given time. Handlers are documented as needing to be idempotent (e.g., using the `job_id` as an idempotency key against downstream side effects) because at-least-once execution is the practical guarantee a polling-based system can make without two-phase commit into arbitrary external systems.

## 4. Retry Strategy

**Decision:** Retry policy is a first-class, reusable entity (`retry_policies`) attached to a queue rather than hard-coded per job, supporting `fixed`, `linear`, and `exponential` backoff with a configurable `max_attempts`, `base_delay_ms`, and `max_delay_ms` cap.

**Why:** Different job types have very different failure characteristics — a flaky third-party API call benefits from exponential backoff with jitter, while an internal idempotent job might just need a fixed short retry. Making the policy a separate, reusable row (rather than duplicating retry config on every queue) keeps configuration DRY and lets an operator update a policy in one place.

**Trade-off:** Jitter was deliberately included in the delay calculation (not just raw exponential backoff) to avoid retry storms where many jobs that failed simultaneously (e.g., due to a downstream outage) all retry at the exact same instant.

## 5. Delayed, Scheduled, and Recurring Jobs

**Decision:** Delayed and one-off scheduled jobs are represented directly on the `jobs` table via a `run_after` timestamp — the same `queued` polling query simply filters `run_after <= now()`. Recurring (cron) jobs get a separate `scheduled_jobs` table that a lightweight scheduler process evaluates on an interval, inserting a new concrete `jobs` row each time the cron expression fires.

**Why:** This keeps the hot path (the worker's claim query) simple — it only ever reads from `jobs`, never from `scheduled_jobs` — and it means a recurring job's history is just a series of normal, independently retryable job rows rather than a special-cased "recurring job" execution model.

## 6. Worker Health & Heartbeats

**Decision:** Workers write a heartbeat row (`worker_heartbeats`) on a fixed interval (e.g., every 10s) containing load and resource metrics; a worker is classified as `unhealthy` if the dashboard/API observes no heartbeat within a configurable timeout (e.g., 3× the heartbeat interval), and `stopped` if it shut down gracefully.

**Why a separate heartbeat table instead of just updating a `last_seen_at` column on `workers`:** Keeping a heartbeat history (not just the latest value) gives the metrics/observability layer a time series to plot worker load over time, and lets the Dead Letter/incident review process answer "was this worker under memory pressure when the job failed?"

**Graceful shutdown:** On receiving a shutdown signal, a worker stops claiming new jobs but finishes in-flight executions (up to a bounded grace period) before deregistering itself, so a deploy/restart doesn't orphan a `running` job — an orphaned `running` job with a stale heartbeat is instead detected by a reaper process and reset to `queued` for retry.

## 7. Database Design Trade-offs

- **Normalization:** The schema is normalized to 3NF (separate `job_executions`, `job_logs`, `worker_heartbeats` tables rather than columns bolted onto `jobs`/`workers`) so history can grow unboundedly without bloating the row that the hot-path claim query touches.
- **Indexing:** The claim query's filter (`queue_id`, `status = 'queued'`, `run_after <= now()`) is backed by a composite partial index (`WHERE status = 'queued'`) so the index stays small even as completed/failed job history grows into the millions of rows.
- **Cascading behavior:** Deleting an `organization` cascades to `projects`, `queues`, and `jobs` (a full tenant offboarding should not leave orphans), but deleting a `job` does **not** cascade-delete its `job_executions`/`job_logs`/`dead_letter_entries` — those are kept for audit purposes and only pruned by a separate retention job.
- **Append-only history tables:** `job_executions` and `job_logs` are treated as append-only/immutable, which simplifies concurrency (no update contention) and makes them safe to write from multiple workers without locking concerns.

## 8. Frontend/Dashboard

**Decision:** Polling (short-interval REST refresh) rather than WebSockets for the initial implementation, with WebSocket live updates listed explicitly as a future improvement.

**Why:** Polling is simpler to build, test, and reason about for a first version, and is sufficient for a dashboard where "a few seconds of staleness" on job/worker status is acceptable. WebSockets add real value once users need sub-second visibility (e.g., watching a job execute live), which is why it's flagged as the natural next step rather than deferred indefinitely.

## 9. Summary of Explicitly Deferred Trade-offs

| Concern | Current approach | Deferred alternative | Why deferred |
|---|---|---|---|
| Queue transport | Postgres-as-queue | Kafka/SQS/RabbitMQ | Simplicity; sufficient throughput for target scale |
| Live updates | Polling | WebSockets | Faster to build correctly; acceptable staleness |
| Multi-tenant isolation | Shared DB, org-scoped rows | Schema-per-tenant / DB-per-tenant | Operational simplicity at current scale |
| Access control | Single role per user | Full RBAC | Not required by core spec; listed as bonus |
| Horizontal queue scaling | Single logical queue, row locking | Queue sharding | Adds complexity not yet justified by load |
