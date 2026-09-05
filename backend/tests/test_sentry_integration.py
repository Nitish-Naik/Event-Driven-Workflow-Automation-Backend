import pytest
from app.integrations.sentry import normalize_sentry_event

def test_normalize_sentry_event():
    payload = {
        "event_id": "sentry-123",
        "event_type": "issue.created",
        "issue_id": "456",
        "message": "Database connection failed",
    }

    event = normalize_sentry_event(payload)

    assert event.event_id == "sentry-123"
    assert event.source == "sentry"
    assert event.event_type == "issue.created"
    assert event.payload == payload
    assert event.received_at is not None


def test_sentry_event_requires_event_id():
    payload = {
        "event_type": "issue.created",
    }

    with pytest.raises(KeyError):
        normalize_sentry_event(payload)