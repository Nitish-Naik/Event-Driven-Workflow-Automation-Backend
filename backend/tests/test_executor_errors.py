import pytest

from app.execution.executor import WorkflowNodeExecutor
from app.execution.types import WorkflowExecutionError
from app.schemas.workflow import WorkflowEdge, WorkflowNode

from test_node_executor import make_context, make_workflow


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
