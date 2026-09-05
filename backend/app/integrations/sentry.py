from datetime import datetime, timezone

from app.schemas.event import Event

def normalize_sentry_event(payload: dict) -> Event:
    return Event(
        event_id=payload["event_id"],
        source="sentry",
        event_type=payload["event_type"],
        payload=payload,
        received_at=datetime.now(timezone.utc),
    )