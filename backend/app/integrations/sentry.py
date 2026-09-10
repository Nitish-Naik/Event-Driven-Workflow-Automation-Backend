from datetime import datetime, timezone

from app.schemas.event import Event


def normalize_sentry_event(payload: dict) -> Event:
    """Normalize a Sentry Service Hook event into the internal Event model."""
    event = payload.get("event")
    if not isinstance(event, dict):
        raise ValueError("Sentry webhook payload missing event object")

    event_id = event.get("eventID") or event.get("id")
    if not event_id:
        raise ValueError("Sentry webhook payload missing event ID")

    return Event(
        event_id=event_id,
        source="sentry",
        event_type="event.created",
        payload=payload,
        received_at=datetime.now(timezone.utc),
    )