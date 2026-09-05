import pytest
from datetime import datetime, timezone
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

from app.config import settings
from app.db.repositories.event import EventRepository
from app.schemas.event import Event


@pytest.fixture
def repository():
    client = MongoClient(settings.mongodb_uri)
    database = client["sentry_workflow_event_test"]

    database.drop_collection("events")

    repository = EventRepository(database=database)
    repository.create_indexes()

    yield repository

    database.drop_collection("events")
    client.close()


def make_event(
    event_id="event-123",
):
    return Event(
        event_id=event_id,
        source="sentry",
        event_type="issue.created",
        payload={"issue_id": "123"},
        received_at=datetime.now(timezone.utc),
    )


def test_create_and_get_event(repository):
    event = make_event()

    result = repository.create(event)

    assert result

    stored_event = repository.get_by_id("event-123")

    assert stored_event == event


def test_duplicate_event_id_is_rejected(repository):
    event = make_event()

    repository.create(event)

    with pytest.raises(DuplicateKeyError):
        repository.create(event)