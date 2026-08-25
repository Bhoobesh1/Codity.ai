"""
The worker process. Run with:  python -m app.workers.worker

Loop, roughly:
  1. Send a heartbeat.
  2. Periodically run stale-job recovery (crash detection).
  3. Claim as many due jobs as we have free capacity for (atomically,
     via SELECT ... FOR UPDATE SKIP LOCKED -- see job_repository.claim_jobs).
  4. Execute claimed jobs concurrently on a thread pool, up to
     max_concurrency.
  5. Repeat, with a short sleep, until asked to shut down.

Graceful shutdown: on SIGTERM/SIGINT, stop claiming new jobs, let
in-flight jobs finish (each execute_job() call commits its own outcome,
so nothing is left half-done), then mark the worker STOPPED and exit.
Multiple workers can run this same script at once; nothing here is
worker-count-aware -- that's the whole point of atomic claiming.
"""

import argparse
import logging
import signal
import socket
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.core.database import SessionLocal
from app.core.logging import configure_logging
from app.models.base import WorkerStatus
from app.repositories import job_repository, worker_repository
from app.scheduler.recovery import recover_stale_jobs
from app.workers.executor import execute_job

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 2
HEARTBEAT_INTERVAL_SECONDS = 5
RECOVERY_INTERVAL_SECONDS = 15
HEARTBEAT_TIMEOUT_SECONDS = 30


class Worker:
    def __init__(self, name: str | None, max_concurrency: int):
        self.name = name or f"worker-{uuid.uuid4().hex[:8]}"
        self.max_concurrency = max_concurrency
        self._shutdown_requested = False
        self._in_flight = 0

        db = SessionLocal()
        try:
            record = worker_repository.register(
                db, name=self.name, hostname=socket.gethostname(), max_concurrency=max_concurrency
            )
            self.worker_id = record.id
        finally:
            db.close()

        logger.info("Worker %s (%s) registered", self.name, self.worker_id)

    def request_shutdown(self, *_args) -> None:
        logger.info("Shutdown requested for worker %s; finishing in-flight jobs...", self.name)
        self._shutdown_requested = True

    def _heartbeat(self, status: WorkerStatus) -> None:
        db = SessionLocal()
        try:
            worker_repository.record_heartbeat(
                db, worker_id=self.worker_id, status=status, current_job_count=self._in_flight
            )
        finally:
            db.close()

    def _run_recovery(self) -> None:
        db = SessionLocal()
        try:
            recovered = recover_stale_jobs(db, heartbeat_timeout_seconds=HEARTBEAT_TIMEOUT_SECONDS)
            if recovered:
                logger.info("Recovered %d stale job(s) from crashed workers", recovered)
        finally:
            db.close()

    def _claim_and_run_batch(self, executor: ThreadPoolExecutor) -> None:
        free_slots = self.max_concurrency - self._in_flight
        if free_slots <= 0:
            return

        db = SessionLocal()
        try:
            claimed = job_repository.claim_jobs(db, worker_id=self.worker_id, max_jobs=free_slots)
        finally:
            db.close()

        if not claimed:
            return

        logger.info("Worker %s claimed %d job(s)", self.name, len(claimed))
        futures = []
        for job in claimed:
            self._in_flight += 1
            futures.append(executor.submit(self._run_one, job.id))

        # We don't block on completion here -- futures are tracked by the
        # caller's loop via as_completed in run(), so claiming can keep
        # happening while earlier jobs are still executing.
        self._pending_futures = getattr(self, "_pending_futures", [])
        self._pending_futures.extend(futures)

    def _run_one(self, job_id: str) -> None:
        db = SessionLocal()
        try:
            job = job_repository.get_by_id(db, job_id)
            if job is None:
                return
            execute_job(db, job=job, worker_id=self.worker_id)
        except Exception:  # noqa: BLE001
            logger.exception("Unexpected error executing job %s", job_id)
        finally:
            db.close()
            self._in_flight -= 1

    def run(self) -> None:
        try:
            signal.signal(signal.SIGTERM, self.request_shutdown)
            signal.signal(signal.SIGINT, self.request_shutdown)
        except ValueError:
            # signal.signal() only works in the main thread of the main
            # interpreter. If this worker is embedded elsewhere (e.g. run
            # on a background thread in a test or a larger application),
            # we still want the polling loop to run -- just without OS
            # signal handling; callers can still stop it via
            # request_shutdown() directly.
            logger.warning(
                "Not running in the main thread; SIGTERM/SIGINT handlers not installed. "
                "Call request_shutdown() directly to stop this worker."
            )

        last_heartbeat = 0.0
        last_recovery = 0.0
        self._pending_futures = []

        with ThreadPoolExecutor(max_workers=self.max_concurrency) as executor:
            while not self._shutdown_requested:
                now = time.monotonic()

                if now - last_heartbeat >= HEARTBEAT_INTERVAL_SECONDS:
                    status = WorkerStatus.BUSY if self._in_flight > 0 else WorkerStatus.IDLE
                    self._heartbeat(status)
                    last_heartbeat = now

                if now - last_recovery >= RECOVERY_INTERVAL_SECONDS:
                    self._run_recovery()
                    last_recovery = now

                self._claim_and_run_batch(executor)

                # Drop completed futures so the list doesn't grow forever.
                self._pending_futures = [f for f in self._pending_futures if not f.done()]

                time.sleep(POLL_INTERVAL_SECONDS)

            logger.info("Waiting for %d in-flight job(s) to finish...", self._in_flight)
            for future in as_completed(self._pending_futures):
                future.result()  # re-raise any unexpected exception for visibility

        db = SessionLocal()
        try:
            worker_repository.mark_stopped(db, worker_id=self.worker_id)
        finally:
            db.close()
        logger.info("Worker %s stopped cleanly", self.name)


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description="Distributed job scheduler worker process")
    parser.add_argument("--name", default=None, help="Worker name (default: random)")
    parser.add_argument(
        "--concurrency", type=int, default=5, help="Max jobs this worker runs at once"
    )
    args = parser.parse_args()

    worker = Worker(name=args.name, max_concurrency=args.concurrency)
    worker.run()


if __name__ == "__main__":
    main()
