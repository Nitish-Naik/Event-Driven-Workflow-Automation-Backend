import pytest

from app.services.retry import (
    PermanentExecutionError,
    RetryableExecutionError,
    calculate_retry_delay,
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


def test_retry_delay_doubles_for_each_attempt_without_jitter():
    assert calculate_retry_delay(1, jitter_ratio=0) == 1.0
    assert calculate_retry_delay(2, jitter_ratio=0) == 2.0
    assert calculate_retry_delay(3, jitter_ratio=0) == 4.0
    assert calculate_retry_delay(4, jitter_ratio=0) == 8.0


def test_retry_delay_is_capped_at_max_delay():
    assert calculate_retry_delay(10, max_delay=10, jitter_ratio=0) == 10.0


def test_retry_delay_jitter_stays_within_expected_range(monkeypatch):
    monkeypatch.setattr("app.services.retry.random.uniform", lambda start, end: end)

    delay = calculate_retry_delay(3, base_delay=2, jitter_ratio=0.1)

    assert delay == 8.8


def test_retry_delay_rejects_invalid_attempt():
    with pytest.raises(ValueError, match="attempt must be at least 1"):
        calculate_retry_delay(0)


def test_retry_delay_rejects_invalid_delay_configuration():
    with pytest.raises(ValueError, match="base_delay must be non-negative"):
        calculate_retry_delay(1, base_delay=-1)

    with pytest.raises(
        ValueError,
        match="max_delay must be greater than or equal to base_delay",
    ):
        calculate_retry_delay(1, base_delay=10, max_delay=5)

    with pytest.raises(ValueError, match="jitter_ratio must be non-negative"):
        calculate_retry_delay(1, jitter_ratio=-0.1)
