from datetime import datetime, timezone

import pytest

from app.execution.contracts import ExecutionContext
from app.execution.registry import NodeRegistry
from app.execution.executor import WorkflowExecutionError
from app.schemas.event import Event
from app.schemas.workflow import Workflow


def make_context():
    now = datetime.now(timezone.utc)
    workflow = Workflow(
        workflow_id="wf-1",
        name="test",
        trigger="sentry.issue",
        created_at=now,
        updated_at=now,
    )
    event = Event(
        event_id="event-1",
        source="sentry",
        event_type="sentry.issue",
        payload={},
        received_at=now,
    )
    return ExecutionContext(workflow=workflow, event=event)


def test_registry_registers_and_returns_handler():
    registry = NodeRegistry()

    def handler(context, config):
        return {"ok": True}

    registry.register("normalize", handler)

    assert registry.get("normalize") is handler


def test_registry_can_be_initialized_with_handlers():
    handler = lambda context, config: {"ok": True}
    registry = NodeRegistry({"normalize": handler})

    assert registry.get("normalize") is handler
    assert registry.handlers() == {"normalize": handler}


def test_registry_executes_registered_handler():
    calls = []

    def handler(context, config, inputs):
        calls.append(config)
        return {"normalized": True}

    registry = NodeRegistry({"normalize": handler})
    result = registry.execute("normalize", make_context(), {"field": "message"})

    assert result == {"normalized": True}
    assert calls == [{"field": "message"}]


def test_registry_rejects_empty_node_type():
    with pytest.raises(ValueError, match="Node type must not be empty"):
        NodeRegistry().register("", lambda context, config: {})


def test_registry_raises_for_missing_handler():
    with pytest.raises(
        WorkflowExecutionError,
        match="No handler registered for node type 'unknown'",
    ):
        NodeRegistry().get("unknown")
