# Design Decisions

## Why PostgreSQL (not a dedicated queue like Redis/RabbitMQ/SQS)

Because the project needs strong relational guarantees around jobs,
their retry history, DLQ entries, and multi-tenant access control — and
because Postgres's `SELECT ... FOR UPDATE SKIP LOCKED` gives you a
correct, atomic job queue *for free*, without introducing a second
system to keep consistent with the primary database. A dedicated queue
would likely be faster at extreme scale (that trade-off is discussed
below), but for this project's scope, one database that's both the
source of truth and the coordination mechanism is simpler to reason
about, test, and operate than a database plus a broker plus the
at-least-once/exactly-once semantics glue code needed to keep them in
sync.

## How atomic job claiming works

See `backend/app/repositories/job_repository.py::claim_jobs` for the
implementation and inline comments; the short version:

```sql
SELECT * FROM jobs
WHERE status IN ('queued', 'retrying') AND scheduled_at <= now()
ORDER BY priority DESC, scheduled_at ASC
FOR UPDATE SKIP LOCKED
LIMIT :n
```

`FOR UPDATE` locks each row it reads. `SKIP LOCKED` means that if
another transaction already holds a lock on a candidate row, this query
simply skips it instead of blocking. So when two workers run this query
at the same moment:
- Worker A's query starts locking rows 1, 2, 3.
- Worker B's query, running concurrently, tries the same candidate set,
  sees rows 1-3 are locked, and skips straight to rows 4, 5, 6.
- Neither worker blocks on the other. Both walk away with **disjoint**
  sets of jobs, guaranteed by Postgres's row-locking, not by any
  application-level coordination.

Per-queue `concurrency_limit` enforcement happens in a Python pass over
the locked candidates (see the comments in `claim_jobs`) rather than in
pure SQL, because it needs a live count of *other* queues' currently
CLAIMED/RUNNING jobs, which is simpler to express correctly as "read
headroom, then walk locked candidates respecting it" than as a single
SQL statement. This was verified under genuine concurrent load in
`backend/tests/test_claiming.py` — multiple real, separate DB
connections racing to claim from a shared pool of 30 jobs, with an
assertion that no job is ever claimed twice.

## Why the worker architecture was selected (dumb pollers, no coordinator)

Considered and rejected: a single "dispatcher" process that assigns
jobs to specific workers. Rejected because it becomes a single point of
failure and a bottleneck, and it needs its own crash-recovery story
(what happens when the dispatcher itself dies mid-assignment?). The
chosen design — every worker independently polls and claims via SKIP
LOCKED — has no leader, so there's nothing extra to fail. Scaling out is
just running more worker processes; scaling down is just stopping them
(gracefully, via SIGTERM). The trade-off is polling latency (jobs wait
up to `POLL_INTERVAL_SECONDS`, 2s by default, before being picked up)
versus a push-based system's near-zero latency — an acceptable trade
for a background job system, less so for anything latency-sensitive.

## How retries work

Each queue has a default `RetryPolicy` (strategy + base delay + max
delay); jobs inherit it at creation time. On failure, if
`retry_count < max_retries`, the job is requeued with
`scheduled_at = now() + delay`, where delay is:

- **fixed**: `base_delay_seconds`
- **linear**: `base_delay_seconds * retry_count`
- **exponential**: `base_delay_seconds * (2 ** retry_count)`, capped at
  `max_delay_seconds`

`max_retries` lives on the `Job` itself (not the policy) so each job can
independently cap its own attempts regardless of which policy it
borrows timing from. Once exhausted, the job moves to `DEAD_LETTER` and
a `DeadLetterQueueEntry` captures the failure reason plus a JSON
snapshot of the full attempt history.

## Stale job recovery / crash detection

Every worker independently runs a periodic check (default every 15s):
mark any worker whose heartbeat is older than the timeout (default 30s)
as `UNHEALTHY`, then requeue any job that unhealthy worker had
CLAIMED/RUNNING. Both steps are single atomic `UPDATE ... WHERE`
statements, safe to run concurrently from multiple workers without a
race — see `backend/app/scheduler/recovery.py`.

**Design choice**: recovery does *not* consume one of the job's own
retry attempts. A missed heartbeat is an infrastructure failure (the
worker crashed), not a failure of the job's logic — it wouldn't be fair
to burn down `max_retries` for something outside the job's control.

## At-least-once delivery, not exactly-once

Honest limitation: this system guarantees a job will eventually run
*at least* once, not *exactly* once. The gap: a worker could finish a
job's handler successfully, then crash before the `UPDATE jobs SET
status='completed'` commits. Recovery would then see the job still
`RUNNING`/`CLAIMED` with a stale heartbeat and requeue it — so it runs
again. Handlers are expected to be idempotent where that matters (e.g.
"send email" handlers should dedupe on some external ID, not just
"run this handler"). Building true exactly-once semantics (e.g. via an
idempotency-key table checked/set in the same transaction as the
status update) is a reasonable extension but adds real complexity for
a benefit that most job types don't strictly need.

## Limitations of the current implementation

- **At-least-once, not exactly-once** delivery (above).
- **No distributed rate limiting** beyond per-queue concurrency limits —
  a handler that calls a rate-limited external API needs to manage that
  itself.
- **Polling-based claiming and scheduling**, not push-based — adds up to
  a few seconds of latency between "job becomes due" and "job starts
  running." Fine for background jobs, not for anything needing
  sub-second dispatch.
- **DLQ listing has no dedicated aggregate endpoint** — the frontend
  currently walks projects → queues → per-queue DLQ jobs client-side
  (see `frontend/src/pages/DeadLetterQueuePage.tsx`). Fine at small
  scale; would need a real query at larger scale.
- **No per-project/queue role granularity** — any member of an
  organization can create/edit/delete any project or queue under it.
  Real production systems usually want finer roles (e.g. "can view but
  not delete").
- **Single Postgres instance** — no read replicas, no connection
  pooler (PgBouncer) in front of it. At meaningful scale, the claiming
  query's row locks would become a real contention point worth
  measuring and potentially sharding by queue.
- **JWT with no refresh flow** — tokens simply expire; there's no
  refresh-token rotation.

## What would change for a large-scale production system

- **A dedicated broker for job dispatch** (Kafka, SQS, or a Redis-backed
  queue) once claim-query contention on a single Postgres instance
  becomes the bottleneck — Postgres would remain the system of record
  for job/execution history, but active dispatch would move off it.
- **Idempotency keys** on job execution to close the at-least-once gap
  for handlers where exactly-once actually matters.
- **Per-project/queue RBAC**, not just per-organization membership.
- **Push-based claiming** (e.g. `LISTEN`/`NOTIFY` in Postgres, or a
  broker's native push) to cut dispatch latency instead of relying on
  fixed polling intervals.
- **Horizontal partitioning of the `jobs`/`job_executions` tables** by
  time or queue, once execution history volume gets large, plus a
  retention/archival policy (nothing currently prunes old completed job
  rows).
- **Real observability**: structured logs shipped to a log aggregator,
  metrics exported to Prometheus (the `/metrics/dashboard` endpoint here
  is a simple JSON summary for the frontend, not a Prometheus exporter),
  and distributed tracing across API → worker → handler.
- **Connection pooling** (PgBouncer) in front of Postgres once worker
  count grows enough that per-process connection overhead matters.
