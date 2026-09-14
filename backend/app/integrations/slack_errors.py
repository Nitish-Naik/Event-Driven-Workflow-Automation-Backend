from app.execution.types import (
    RetryableWorkflowExecutionError,
    WorkflowExecutionError,
)


class SlackAPIError(WorkflowExecutionError):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class SlackRetryableAPIError(SlackAPIError, RetryableWorkflowExecutionError):
    pass


class SlackPermanentAPIError(SlackAPIError):
    pass
