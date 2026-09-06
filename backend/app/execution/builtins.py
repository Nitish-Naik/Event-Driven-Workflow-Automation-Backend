from typing import Any

from app.execution.contracts import ExecutionContext
from app.execution.types import NodeHandler


SENTRY_TRIGGER = "sentry_trigger"
NORMALIZE_EVENT = "normalize_event"


def sentry_trigger_handler(context: ExecutionContext, config: Any, inputs: dict[str, Any],) -> dict[str, Any]:
    """Expose the incoming Sentry event as the node output."""
    return {
        "event_id": context.event.event_id,
        "event_type": context.event.event_type,
        "source": context.event.source,
        "payload": context.event.payload,
    }


def normalize_event_handler(context: ExecutionContext, config: Any, inputs: dict[str, Any],) -> dict[str, Any]:
    """Create a stable event shape for downstream workflow nodes."""
    payload = context.event.payload
    return {
        "event_id": context.event.event_id,
        "event_type": context.event.event_type,
        "source": context.event.source,
        "message": payload.get("message"),
        "level": payload.get("level"),
        "project": payload.get("project"),
        "payload": payload,
    }


def builtin_handlers() -> dict[str, NodeHandler]:
    return {
        SENTRY_TRIGGER: sentry_trigger_handler,
        NORMALIZE_EVENT: normalize_event_handler,
    }
