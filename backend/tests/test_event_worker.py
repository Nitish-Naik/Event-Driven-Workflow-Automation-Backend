import json
from datetime import datetime, timezone

from app.schemas.event import Event
from app.worker.event_worker import EventWorker
from app.schemas.run import RunStatus


class FakeRedis:
    def __init__(self, items=None):
        self.items = items or []

    def lpop(self, queue_name):
        if not self.items:
            return None

        return self.items.pop(0)


class FakeEventRepository:
    def __init__(self, events=None):
        self.events = events or {}

    def get_by_id(self, event_id):
        return self.events.get(event_id)


def test_process_next_event():
    event_id = "event-123"

    redis = FakeRedis(
        [
            json.dumps({"event_id": event_id})
        ]
    )

    event = Event(
        event_id=event_id,
        source="sentry",
        event_type="issue.created",
        received_at=datetime.now(timezone.utc)
    )

    repository = FakeEventRepository(
        {event_id: event}
    )

    worker = EventWorker(
        redis_client=redis,
        event_repository=repository,
    )

    assert worker.process_next() is True
    assert redis.items == []


def test_process_next_returns_false_when_queue_is_empty():
    redis = FakeRedis()
    repository = FakeEventRepository()

    worker = EventWorker(
        redis_client=redis,
        event_repository=repository,
    )

    assert worker.process_next() is False


class FakeRunRepository:
    def __init__(self):
        self.runs = []

    def create(self, run):
        self.runs.append(run)
        return run.run_id

def test_process_next_creates_workflow_run():
    event_id = "event-456"

    redis = FakeRedis(
        [
            json.dumps({"event_id": event_id})
        ]
    )

    event = Event(
        event_id=event_id,
        source="sentry",
        event_type="issue.created",
        received_at=datetime.now(timezone.utc),
    )

    event_repository = FakeEventRepository(
        {event_id: event}
    )

    run_repository = FakeRunRepository()

    worker = EventWorker(
        redis_client=redis,
        event_repository=event_repository,
        run_repository=run_repository,
    )

    assert worker.process_next() is True

    assert len(run_repository.runs) == 1

    run = run_repository.runs[0]

    assert run.event_id == event_id
    assert run.workflow_id == "default"
    assert run.workflow_version == 1
    assert run.status == RunStatus.PROCESSING