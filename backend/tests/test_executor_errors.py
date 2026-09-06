from datetime import datetime, timezone

import pytest

from app.execution.contracts import ExecutionContext
from app.execution.executor import WorkflowExecutionError, WorkflowNodeExecutor
from app.schemas.event import Event
from app.schemas.workflow import Workflow, WorkflowEdge, WorkflowNode


def make_workflow(nodes, edges):
    now = datetime.now(timezone.utc)
    return Workflow(
        workflow_id="wf-1",
        name="test",
        trigger="sentry.issue",
        nodes=nodes,
        edges=edges,
        created_at=now,
        updated_at=now,
    )


def make_context(workflow):
    event = Event(
        event_id="event-1",
        source="sentry",
        event_type="sentry.issue",
        payload={"message": "test"},
        received_at=datetime.now(timezone.utc),
    )
    return ExecutionContext(workflow=workflow, event=event)


def test_executor_wraps_unexpected_handler_exception():
    workflow = make_workflow(
        [WorkflowNode(id="source", type="source")],
        [],
    )
    context = make_context(workflow)

    def failing_handler(ctx, config, inputs):
        raise RuntimeError("database connection failed")

    executor = WorkflowNodeExecutor({"source": failing_handler})

    with pytest.raises(
        WorkflowExecutionError,
        match=r"Node 'source' \(source\) failed during execution",
    ) as exc_info:
        executor.execute(context)

    assert isinstance(exc_info.value.__cause__, RuntimeError)
    assert str(exc_info.value.__cause__) == "database connection failed"


def test_executor_preserves_workflow_execution_error():
    workflow = make_workflow(
        [WorkflowNode(id="source", type="source")],
        [],
    )
    context = make_context(workflow)
    expected = WorkflowExecutionError("known execution failure")

    def failing_handler(ctx, config, inputs):
        raise expected

    executor = WorkflowNodeExecutor({"source": failing_handler})

    with pytest.raises(WorkflowExecutionError) as exc_info:
        executor.execute(context)

    assert exc_info.value is expected


def test_executor_wraps_input_resolution_error():
    workflow = make_workflow(
        [
            WorkflowNode(id="source", type="source"),
            WorkflowNode(
                id="consumer",
                type="consumer",
                config={
                    "inputs": {
                        "message": {"$ref": "source.missing"},
                    }
                },
            ),
        ],
        [WorkflowEdge(source="source", target="consumer")],
    )
    context = make_context(workflow)

    def source_handler(ctx, config, inputs):
        return {"message": "available"}

    def consumer_handler(ctx, config, inputs):
        return {"received": inputs["message"]}

    executor = WorkflowNodeExecutor(
        {
            "source": source_handler,
            "consumer": consumer_handler,
        }
    )

    with pytest.raises(
        WorkflowExecutionError,
        match="Failed to resolve inputs for node 'consumer'",
    ) as exc_info:
        executor.execute(context)

    assert exc_info.value.__cause__ is not None
