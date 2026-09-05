import pytest

from app.schemas.event import Event
from app.services.event import EventService
from app.services.exceptions import EventAlreadyExistsError


class FakeEventRepository:
    def __init__(self):
        self.events = {}

    def create(self, event):
        if event.event_id in self.events:
            from pymongo.errors import DuplicateKeyError

            raise DuplicateKeyError(
                "duplicate event_id"
            )

        self.events[event.event_id] = event

        return "fake-event-id"

    def get_by_id(self, event_id):
        return self.events.get(event_id)


def make_event(event_id="event-123"):
    from datetime import datetime, timezone

    return Event(
        event_id=event_id,
        source="sentry",
        event_type="issue.created",
        payload={"issue_id": "123"},
        received_at=datetime.now(timezone.utc),
    )


def test_create_event():
    repository = FakeEventRepository()
    service = EventService(repository)

    event = make_event()

    result = service.create_event(event)

    assert result == "fake-event-id"
    assert repository.events["event-123"] == event


def test_duplicate_event_raises_domain_error():
    repository = FakeEventRepository()
    service = EventService(repository)

    event = make_event()

    service.create_event(event)

    with pytest.raises(EventAlreadyExistsError):
        service.create_event(event)


def test_get_event():
    repository = FakeEventRepository()
    service = EventService(repository)

    event = make_event()

    service.create_event(event)

    result = service.get_event("event-123")

    assert result == event