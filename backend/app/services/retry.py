import random

from app.execution.types import RetryableWorkflowExecutionError, WorkflowExecutionError


class RetryableExecutionError(RetryableWorkflowExecutionError):
    """Raised when an execution failure may succeed on a later attempt."""


class PermanentExecutionError(WorkflowExecutionError):
    """Raised when an execution failure should not be retried."""


def is_retryable_error(error: Exception) -> bool:
    """Return whether an execution error is safe to retry."""
    return isinstance(error, RetryableExecutionError)


def calculate_retry_delay(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter_ratio: float = 0.1,
) -> float:
    """Calculate exponential backoff delay with bounded positive jitter."""
    if attempt < 1:
        raise ValueError("attempt must be at least 1")
    if base_delay < 0:
        raise ValueError("base_delay must be non-negative")
    if max_delay < base_delay:
        raise ValueError("max_delay must be greater than or equal to base_delay")
    if jitter_ratio < 0:
        raise ValueError("jitter_ratio must be non-negative")

    exponential_delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
    jitter = random.uniform(0, exponential_delay * jitter_ratio)
    return min(exponential_delay + jitter, max_delay)
