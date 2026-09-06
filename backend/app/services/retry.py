class RetryableExecutionError(Exception):
    """Raised when an execution failure may succeed on a later attempt."""


class PermanentExecutionError(Exception):
    """Raised when an execution failure should not be retried."""


def is_retryable_error(error: Exception) -> bool:
    """Return whether an execution error is safe to retry."""
    return isinstance(error, RetryableExecutionError)
