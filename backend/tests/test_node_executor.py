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


def test_executes_linear_workflow_and_propagates_values():
    workflow = make_workflow(
        [
            WorkflowNode(id="a", type="source"),
            WorkflowNode(id="b", type="transform"),
            WorkflowNode(id="c", type="sink"),
        ],
        [WorkflowEdge(source="a", target="b"), WorkflowEdge(source="b", target="c")],
    )
    context = make_context(workflow)
    calls = []

    def source(ctx, config):
        calls.append("a")
        return {"value": 10}

    def transform(ctx, config):
        calls.append("b")
        return {"value": ctx.values["a"]["value"] * 2}

    def sink(ctx, config):
        calls.append("c")
        return {"value": ctx.values["b"]["value"] + 5}

    result = WorkflowNodeExecutor(
        {"source": source, "transform": transform, "sink": sink}
    ).execute(context)

    assert calls == ["a", "b", "c"]
    assert result.outputs["c"] == {"value": 25}
    assert context.values["b"] == {"value": 20}


def test_shared_downstream_node_executes_only_once():
    workflow = make_workflow(
        [
            WorkflowNode(id="a", type="source"),
            WorkflowNode(id="b", type="branch"),
            WorkflowNode(id="c", type="branch"),
            WorkflowNode(id="d", type="sink"),
        ],
        [
            WorkflowEdge(source="a", target="b"),
            WorkflowEdge(source="a", target="c"),
            WorkflowEdge(source="b", target="d"),
            WorkflowEdge(source="c", target="d"),
        ],
    )
    context = make_context(workflow)
    calls = []

    def handler(ctx, config):
        calls.append(config["name"])
        return {"name": config["name"]}

    for node in workflow.nodes:
        node.config["name"] = node.id

    WorkflowNodeExecutor({
        "source": handler,
        "branch": handler,
        "sink": handler,
    }).execute(context)

    assert calls.count("d") == 1
    assert set(calls) == {"a", "b", "c", "d"}


def test_sibling_execution_order_is_deterministic():
    workflow = make_workflow(
        [
            WorkflowNode(id="root", type="node"),
            WorkflowNode(id="z", type="node"),
            WorkflowNode(id="a", type="node"),
        ],
        [
            WorkflowEdge(source="root", target="z"),
            WorkflowEdge(source="root", target="a"),
        ],
    )
    context = make_context(workflow)
    calls = []

    def handler(ctx, config):
        calls.append(config["id"])
        return {}

    for node in workflow.nodes:
        node.config["id"] = node.id

    WorkflowNodeExecutor({"node": handler}).execute(context)

    assert calls == ["root", "a", "z"]


def test_missing_handler_raises_execution_error():
    workflow = make_workflow([WorkflowNode(id="a", type="unknown")], [])

    with pytest.raises(
        WorkflowExecutionError,
        match="No handler registered for node type 'unknown'",
    ):
        WorkflowNodeExecutor().execute(make_context(workflow))
