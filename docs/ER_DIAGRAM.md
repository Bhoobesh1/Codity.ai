# Entity-Relationship Diagram

The following diagram represents the database entity relationships used in this project.

![Entity Relationship Diagram](ER-Diagram.png)

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
