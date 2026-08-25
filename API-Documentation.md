# API Documentation — Distributed Job Scheduler

Base URL: `/api/v1`

## Conventions

**Authentication:** All endpoints except `/auth/register` and `/auth/login` require a Bearer token:

```
Authorization: Bearer <jwt>
```

**Pagination:** List endpoints accept `page` (default `1`) and `limit` (default `20`, max `100`) query params and return:

```json
{
  "data": [ ... ],
  "pagination": { "page": 1, "limit": 20, "total": 143, "total_pages": 8 }
}
```

**Filtering:** List endpoints accept relevant `filter[...]` query params (documented per-endpoint below).

**Error format:**

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "handler_name is required",
    "details": [ { "field": "handler_name", "issue": "required" } ]
  }
}
```

Common error codes: `VALIDATION_ERROR` (400), `UNAUTHORIZED` (401), `FORBIDDEN` (403), `NOT_FOUND` (404), `CONFLICT` (409, e.g. pausing an already-paused queue), `RATE_LIMITED` (429), `INTERNAL_ERROR` (500).

---

## Auth

### `POST /auth/register`
Create a user and organization.

**Body:**
```json
{ "email": "a@b.com", "password": "••••••••", "organization_name": "Acme Inc" }
```
**201 Response:** `{ "user": { "user_id": "...", "email": "..." }, "token": "<jwt>" }`

### `POST /auth/login`
**Body:** `{ "email": "a@b.com", "password": "••••••••" }`
**200 Response:** `{ "token": "<jwt>", "expires_at": "2026-08-26T00:00:00Z" }`

### `POST /auth/refresh`
**Body:** `{ "refresh_token": "..." }` → **200:** `{ "token": "<jwt>" }`

---

## Projects

### `GET /projects`
List projects in the caller's organization. Supports pagination.

### `POST /projects`
**Body:** `{ "name": "Payments Service" }` → **201:** project object incl. generated `api_key`.

### `GET /projects/:projectId`
Fetch a single project.

### `PATCH /projects/:projectId`
**Body:** `{ "name": "New name" }`

### `DELETE /projects/:projectId`
Deletes the project and all owned queues/jobs (cascade). **204** on success.

---

## Queues

### `GET /projects/:projectId/queues`
List queues for a project. Filters: `filter[is_paused]=true|false`.

### `POST /projects/:projectId/queues`
**Body:**
```json
{
  "name": "email-sending",
  "priority": 5,
  "concurrency_limit": 10,
  "retry_policy": { "strategy": "exponential", "base_delay_ms": 1000, "max_delay_ms": 60000, "max_attempts": 5 }
}
```

### `GET /queues/:queueId`
Fetch queue detail including current retry policy and live stats (queued/running/failed counts).

### `PATCH /queues/:queueId`
Update `priority`, `concurrency_limit`, or `retry_policy`.

### `DELETE /queues/:queueId`
Deletes the queue. Fails with `409 CONFLICT` if jobs are currently `running` unless `?force=true`.

### `POST /queues/:queueId/pause`
Pauses the queue — workers stop claiming new jobs from it. **200:** updated queue object.

### `POST /queues/:queueId/resume`
Resumes a paused queue.

### `GET /queues/:queueId/stats`
Returns counts by status, throughput over the last hour, and average execution time.

---

## Jobs

### `POST /queues/:queueId/jobs`
Submit a job.

**Body (immediate):**
```json
{ "handler_name": "echo", "type": "immediate", "payload": {} }
```

**Body (delayed):**
```json
{ "handler_name": "echo", "type": "delayed", "delay_seconds": 60, "payload": {} }
```

**Body (scheduled):**
```json
{ "handler_name": "echo", "type": "scheduled", "run_at": "2026-09-01T09:00:00Z", "payload": {} }
```

**Body (recurring):**
```json
{ "handler_name": "cleanup", "type": "recurring", "cron_expression": "0 * * * *", "payload": {} }
```

**Body (batch):**
```json
{ "handler_name": "resize_image", "type": "batch", "items": [ { "payload": { "url": "a.jpg" } }, { "payload": { "url": "b.jpg" } } ] }
```

**201 Response:** created job (or, for batch, `{ "batch_id": "...", "job_count": 2 }`).

### `GET /queues/:queueId/jobs`
List jobs in a queue. Filters: `filter[status]=queued|claimed|running|completed|failed|dead_letter`, `filter[handler_name]`, `filter[created_after]`, `filter[created_before]`.

### `GET /jobs/:jobId`
Fetch job detail: current status, attempt count, payload, timestamps, assigned worker.

### `GET /jobs/:jobId/executions`
List all execution attempts for a job (status, duration, error per attempt).

### `GET /jobs/:jobId/logs`
List structured log lines emitted during execution. Supports `filter[level]=info|warn|error`.

### `POST /jobs/:jobId/cancel`
Cancels a job that is still `queued` or `scheduled`. Returns `409 CONFLICT` if already `running`/`completed`.

---

## Workers

### `GET /projects/:projectId/workers`
List workers registered to a project, with current `status` (`healthy`/`unhealthy`/`stopped`), `capacity`, and `current_load`.

### `GET /workers/:workerId`
Fetch a single worker's detail.

### `GET /workers/:workerId/heartbeats`
List recent heartbeat records (timestamp, CPU, memory, active job count). Supports `?since=<ISO timestamp>`.

---

## Dead Letter Queue

### `GET /dlq`
List permanently failed jobs across the caller's projects. Filters: `filter[project_id]`, `filter[queue_id]`, `filter[is_resolved]`.

### `GET /dlq/:dlqId`
Fetch full detail: original job payload, final error, total attempts, per-attempt history.

### `POST /dlq/:dlqId/retry`
Re-queues the job (resets `attempt_count` to 0, sets status back to `queued`) and marks the DLQ entry `is_resolved = true`.

---

## Metrics

### `GET /metrics/overview`
**200 Response:**
```json
{
  "total_jobs": 12034,
  "success_rate": 0.982,
  "avg_execution_time_ms": 214,
  "throughput_per_minute": 87,
  "workers_healthy": 4,
  "workers_unhealthy": 0
}
```

### `GET /metrics/throughput`
Query params: `from`, `to`, `interval` (`minute`|`hour`|`day`). Returns a time-bucketed series of `{ timestamp, completed, failed }` used to render the dashboard's throughput chart.
