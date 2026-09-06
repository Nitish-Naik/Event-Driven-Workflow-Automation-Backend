import pytest

from app.execution.executor import WorkflowNodeExecutor
from app.execution.types import WorkflowExecutionError
from app.execution.inputs import InputResolutionError


# These tests intentionally use the existing test helpers and schemas through
# the executor's public contract.


def test_executor_wraps_unexpected_handler_exception(make_workflow, make_context):
    workflow = make_workflow(
        [
            {"id": "source", "type": "source"},
        ],
        [],
    )
    context = make_context(workflow)

    def failing_handler(ctx, config, inputs):
        raise RuntimeError("database connection failed")

    executor = WorkflowNodeExecutor({"source": failing_handler})

    with pytest.raises(
        WorkflowExecutionError,
        match="Node 'source' \(source\) failed during execution",
    ):
        executor.execute(context)


def test_executor_preserves_workflow_execution_error(make_workflow, make_context):
    workflow = make_workflow(
        [
            {"id": "source", "type": "source"},
        ],
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


def test_executor_wraps_input_resolution_error(make_workflow, make_context):
    workflow = make_workflow(
        [
            {"id": "source", "type": "source"},
            {
                "id": "consumer",
                "type": "consumer",
                "config": {
                    "inputs": {
                        "message": {"$ref": "source.missing"},
                    }
                },
            },
        ],
        [{"source": "source", "target": "consumer"}],
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

    # The source executes first, so this test verifies that input resolution
    # failures are converted into workflow-level execution failures.
    workflow.nodes[0].config = {}
    workflow.nodes[1].config["inputs"]["message"] = {
        "$ref": "source.missing"
    }

    with pytest.raises(
        WorkflowExecutionError,
        match="Failed to resolve inputs for node 'consumer'",
    ):
        executor.execute(context)
