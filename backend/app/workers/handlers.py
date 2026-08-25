"""
Example job handlers, keyed by `Job.name`.

In a real system these would dispatch to actual business logic (send an
email, process a payment, etc.). For this project, a handful of simple
handlers are enough to exercise and test the full lifecycle: success,
deterministic failure, and a handler that fails a configurable number
of times before succeeding (useful for exercising the retry system
end-to-end).

Handlers receive the job's JSON payload and either return normally
(success) or raise an exception (failure, whose message becomes the
JobExecution's error_message).
"""

import time
from collections.abc import Callable

HandlerFn = Callable[[dict], None]


def echo_handler(payload: dict) -> None:
    """Always succeeds; simulates near-instant work."""
    return None


def sleep_handler(payload: dict) -> None:
    """Succeeds after sleeping for payload['seconds'] (default 1)."""
    time.sleep(float(payload.get("seconds", 1)))


def always_fail_handler(payload: dict) -> None:
    """Always fails; useful for exercising retries and the DLQ."""
    raise RuntimeError(payload.get("error_message", "Simulated permanent failure."))


def flaky_handler(payload: dict) -> None:
    """
    Fails until the job's current retry_count reaches payload['fail_until'],
    then succeeds. Lets tests exercise "fails twice, then works".
    """
    fail_until = int(payload.get("fail_until", 0))
    current_attempt = int(payload.get("__retry_count__", 0))
    if current_attempt < fail_until:
        raise RuntimeError(f"Flaky failure on attempt {current_attempt}")


HANDLERS: dict[str, HandlerFn] = {
    "echo": echo_handler,
    "sleep": sleep_handler,
    "always_fail": always_fail_handler,
    "flaky": flaky_handler,
}


def get_handler(name: str) -> HandlerFn:
    return HANDLERS.get(name, echo_handler)
