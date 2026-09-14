from datetime import datetime, timezone

from app.schemas.event import Event


def _first_identifier(value: object) -> str | None:
    if not isinstance(value, dict):
        return None
    for key in ("eventID", "event_id", "id", "issueId"):
        identifier = value.get(key)
        if identifier:
            return str(identifier)
    for nested in value.values():
        identifier = _first_identifier(nested)
        if identifier:
            return identifier
    return None


def normalize_sentry_event(payload: dict) -> Event:
    """Normalize a Sentry Service Hook event into the internal Event model."""
    event = payload.get("event")
    data = payload.get("data")

    if event is None and data is None:
        raise ValueError("Sentry webhook payload missing event object")

    event_id = _first_identifier(event)
    if event_id is None:
        event_id = _first_identifier(data)
    if event_id is None:
        event_id = _first_identifier(payload)
    if not event_id:
        raise ValueError("Sentry webhook payload missing event ID")

    resource = payload.get("resource")
    action = payload.get("action")
    event_type = payload.get("event_type")
    if not event_type and resource and action:
        event_type = f"{resource}.{action}"

    return Event(
        event_id=event_id,
        source="sentry",
        event_type=event_type or "event.created",
        payload=payload,
        received_at=datetime.now(timezone.utc),
    )