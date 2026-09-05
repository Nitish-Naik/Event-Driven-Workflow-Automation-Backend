from datetime import datetime, timezone

from app.schemas.event import Event


def test_create_event():
    event = Event(
        event_id="event-123",
        source="sentry",
        event_type="issue.created",
        payload={"issue_id": "123"},
        received_at=datetime.now(timezone.utc),
    )

    assert event.event_id == "event-123"
    assert event.source == "sentry"
    assert event.event_type == "issue.created"
    assert event.payload["issue_id"] == "123"

def test_event_payload_defaults_to_empty_dict():
    event = Event(
        event_id="event-123",
        source="sentry",
        event_type="issue.created",
        received_at=datetime.now(timezone.utc),
    )

    assert event.payload == {}