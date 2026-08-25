"""
Retry delay computation.

`retry_count` here is the number of attempts already made *before* this
delay is computed (0 on the first failure), matching the formula given
in the project spec:  retry_delay = base_delay * (2 ** retry_count)
"""

from app.models.base import RetryStrategy
from app.models.retry_policy import RetryPolicy


def compute_retry_delay_seconds(policy: RetryPolicy, *, retry_count: int) -> int:
    if policy.strategy == RetryStrategy.FIXED:
        delay = policy.base_delay_seconds
    elif policy.strategy == RetryStrategy.LINEAR:
        delay = policy.base_delay_seconds * max(retry_count, 1)
    else:  # EXPONENTIAL
        delay = policy.base_delay_seconds * (2**retry_count)

    return min(delay, policy.max_delay_seconds)
