import pytest

from app.execution.contracts import ExecutionContext
from app.execution.inputs import (
    InputResolutionError,
    resolve_node_input,
    resolve_input_value,
)
from app.schemas.event import Event
from app.schemas.workflow import Workflow


def make_context(values=None):
    workflow = Workflow(
        workflow_id="workflow-1",
        name="Test Workflow",
        trigger="sentry",
        nodes=[],
        edges=[],
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )

    event = Event(
        event_id="event-1",
        source="sentry",
        event_type="issue.created",
        payload={},
        received_at="2026-01-01T00:00:00Z",
    )

    return ExecutionContext(
        workflow=workflow,
        event=event,
        values=values or {},
    )


def test_resolve_node_input_returns_upstream_value():
    context = make_context(
        {
            "trigger": {
                "event_id": "event-123",
                "event_type": "issue.created",
            }
        }
    )

    result = resolve_node_input(
        context,
        "trigger",
        "event_id",
    )

    assert result == "event-123"


def test_resolve_node_input_raises_when_node_has_not_executed():
    context = make_context()

    with pytest.raises(
        InputResolutionError,
        match="No output available for node 'trigger'",
    ):
        resolve_node_input(
            context,
            "trigger",
            "event_id",
        )


def test_resolve_node_input_raises_when_field_is_missing():
    context = make_context(
        {
            "trigger": {
                "event_type": "issue.created",
            }
        }
    )

    with pytest.raises(
        InputResolutionError,
        match="Field 'event_id' not found",
    ):
        resolve_node_input(
            context,
            "trigger",
            "event_id",
        )


def test_resolve_node_input_raises_for_non_dictionary_output():
    context = make_context(
        {
            "trigger": "invalid-output",
        }
    )

    with pytest.raises(
        InputResolutionError,
        match="must be a dictionary",
    ):
        resolve_node_input(
            context,
            "trigger",
            "event_id",
        )


def test_resolve_input_value_returns_literal():
    context = make_context()

    result = resolve_input_value(
        context,
        "hello",
    )

    assert result == "hello"


def test_resolve_input_value_resolves_reference():
    context = make_context(
        {
            "normalize": {
                "message": "Database connection failed",
            }
        }
    )

    result = resolve_input_value(
        context,
        {"$ref": "normalize.message"},
    )

    assert result == "Database connection failed"


def test_resolve_input_value_resolves_nested_references():
    context = make_context(
        {
            "normalize": {
                "message": "Database connection failed",
                "level": "error",
            }
        }
    )

    result = resolve_input_value(
        context,
        {
            "payload": {
                "message": {"$ref": "normalize.message"},
                "level": {"$ref": "normalize.level"},
            },
            "static": "value",
        },
    )

    assert result == {
        "payload": {
            "message": "Database connection failed",
            "level": "error",
        },
        "static": "value",
    }


def test_resolve_input_value_resolves_references_inside_lists():
    context = make_context(
        {
            "normalize": {
                "message": "Database connection failed",
            }
        }
    )

    result = resolve_input_value(
        context,
        [
            "static",
            {"$ref": "normalize.message"},
        ],
    )

    assert result == [
        "static",
        "Database connection failed",
    ]


def test_resolve_input_value_rejects_invalid_reference():
    context = make_context()

    with pytest.raises(
        InputResolutionError,
        match="Invalid node input reference",
    ):
        resolve_input_value(
            context,
            {"$ref": "invalid-reference"},
        )


def test_resolve_input_value_propagates_missing_field():
    context = make_context(
        {
            "normalize": {
                "level": "error",
            }
        }
    )

    with pytest.raises(
        InputResolutionError,
        match="Field 'message' not found",
    ):
        resolve_input_value(
            context,
            {"$ref": "normalize.message"},
        )
