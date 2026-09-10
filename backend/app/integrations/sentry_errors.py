from __future__ import annotations

from app.execution.types import RetryableWorkflowExecutionError, WorkflowExecutionError


class SentryAPIError(WorkflowExecutionError):
    """Base error for Sentry API failures."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class SentryRetryableAPIError(RetryableWorkflowExecutionError, SentryAPIError):
    """Raised when a Sentry API failure should be retried."""


class SentryPermanentAPIError(SentryAPIError):
    """Raised when a Sentry API failure should not be retried."""
