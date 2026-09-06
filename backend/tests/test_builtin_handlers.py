from datetime import datetime, timezone

from app.execution.builtins import (
    NORMALIZE_EVENT,
    SENTRY_TRIGGER,
    builtin_handlers,
    normalize_event_handler,
    sentry_trigger_handler,
)
from app.execution.contracts import ExecutionContext
from app.schemas.event import Event
from app.schemas.workflow import Workflow


def make_context(payload):
    now = datetime.now(timezone.utc)
    event = Event(
        event_id="event-1",
        source="sentry",
        event_type="sentry.issue",
        payload=payload,
        received_at=now,
    )
    workflow = Workflow(
        workflow_id="wf-1",
        name="test",
        trigger="sentry.issue",
        created_at=now,
        updated_at=now,
    )
    return ExecutionContext(workflow=workflow, event=event)


def test_sentry_trigger_exposes_incoming_event():
    context = make_context({"message": "database timeout"})

    result = sentry_trigger_handler(context, {}, {})

    assert result == {
        "event_id": "event-1",
        "event_type": "sentry.issue",
        "source": "sentry",
        "payload": {"message": "database timeout"},
    }


def test_normalize_event_creates_stable_shape():
    context = make_context(
        {
            "message": "database timeout",
            "level": "error",
            "project": "payments",
            "extra": {"region": "ap-south-1"},
        }
    )

    result = normalize_event_handler(context, {}, {})

    assert result["event_id"] == "event-1"
    assert result["event_type"] == "sentry.issue"
    assert result["source"] == "sentry"
    assert result["message"] == "database timeout"
    assert result["level"] == "error"
    assert result["project"] == "payments"
    assert result["payload"]["extra"]["region"] == "ap-south-1"


def test_normalize_event_handles_optional_fields():
    context = make_context({"message": "timeout"})

    result = normalize_event_handler(context, {}, {})

    assert result["message"] == "timeout"
    assert result["level"] is None
    assert result["project"] is None


def test_builtin_handlers_register_expected_node_types():
    handlers = builtin_handlers()

    assert set(handlers) == {SENTRY_TRIGGER, NORMALIZE_EVENT}
    assert handlers[SENTRY_TRIGGER] is sentry_trigger_handler
    assert handlers[NORMALIZE_EVENT] is normalize_event_handler
