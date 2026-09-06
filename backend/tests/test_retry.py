import pytest

from app.services.retry import (
    PermanentExecutionError,
    RetryableExecutionError,
    is_retryable_error,
)


def test_retryable_execution_error_is_retryable():
    error = RetryableExecutionError("temporary failure")

    assert is_retryable_error(error) is True


def test_permanent_execution_error_is_not_retryable():
    error = PermanentExecutionError("permanent failure")

    assert is_retryable_error(error) is False


@pytest.mark.parametrize(
    "error",
    [
        ValueError("invalid input"),
        RuntimeError("unexpected failure"),
        Exception("unknown failure"),
    ],
)
def test_unknown_errors_are_not_retryable(error):
    assert is_retryable_error(error) is False
