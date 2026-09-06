from datetime import datetime, timezone

import pytest

from app.execution.contracts import ExecutionContext
from app.execution.executor import WorkflowNodeExecutor
from app.execution.types import WorkflowExecutionError
from app.schemas.event import Event
from app.schemas.workflow import Workflow, WorkflowNode
from app.services.retry import RetryableExecutionError


def make_workflow():
    now = datetime.now(timezone.utc)
    return Workflow(
        workflow_id="wf-1",
        name="test",
        trigger="sentry.issue",
        nodes=[WorkflowNode(id="source", type="source")],
        edges=[],
        created_at=now,
        updated_at=now,
    )


def make_context():
    return ExecutionContext(
        workflow=make_workflow(),
        event=Event(
            event_id="event-1",
            source="sentry",
            event_type="sentry.issue",
            payload={},
            received_at=datetime.now(timezone.utc),
        ),
    )


def test_executor_preserves_retryable_error_type():
    expected = RetryableExecutionError("Sentry API unavailable")

    def handler(ctx, config, inputs):
        raise expected

    with pytest.raises(RetryableExecutionError) as exc_info:
        WorkflowNodeExecutor({"source": handler}).execute(make_context())

    assert exc_info.value is expected
    assert isinstance(exc_info.value, WorkflowExecutionError)
