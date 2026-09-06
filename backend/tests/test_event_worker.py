import json
from datetime import datetime, timezone

from app.schemas.event import Event
from app.schemas.run import RunStatus
from app.schemas.workflow import Workflow
from app.worker.event_worker import EventWorker


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


class FakeRunRepository:
    def __init__(self):
        self.runs = []
        self.status_updates = []

    def create(self, run):
        self.runs.append(run)
        return run.run_id

    def update_status(self, run_id, status):
        self.status_updates.append((run_id, status))
        return True


class FakeWorkflowService:
    def __init__(self, workflow=None):
        self.workflow = workflow

    def get_active_workflow_by_trigger(self, trigger):
        if self.workflow is not None and self.workflow.trigger == trigger:
            return self.workflow

        return None


def make_event(event_id="event-123"):
    return Event(
        event_id=event_id,
        source="sentry",
        event_type="issue.created",
        received_at=datetime.now(timezone.utc),
    )


def make_workflow(
    workflow_id="sentry-workflow",
    version=3,
    trigger="sentry",
):
    now = datetime.now(timezone.utc)

    return Workflow(
        workflow_id=workflow_id,
        name="Sentry Incident Triage",
        trigger=trigger,
        version=version,
        status="active",
        nodes=[
            {"id": "trigger", "type": "sentry_trigger"},
            {"id": "ai", "type": "ai_analysis"},
        ],
        edges=[
            {"source": "trigger", "target": "ai"},
        ],
        created_at=now,
        updated_at=now,
    )


def test_process_next_event():
    event_id = "event-123"
    redis = FakeRedis([json.dumps({"event_id": event_id})])
    event_repository = FakeEventRepository({event_id: make_event(event_id)})

    worker = EventWorker(
        redis_client=redis,
        event_repository=event_repository,
        workflow_service=FakeWorkflowService(make_workflow()),
    )

    assert worker.process_next() is True
    assert redis.items == []


def test_process_next_returns_false_when_queue_is_empty():
    worker = EventWorker(
        redis_client=FakeRedis(),
        event_repository=FakeEventRepository(),
        workflow_service=FakeWorkflowService(),
    )

    assert worker.process_next() is False


def test_process_next_creates_and_starts_run_with_active_workflow():
    event_id = "event-456"
    workflow = make_workflow(
        workflow_id="sentry-triage",
        version=7,
    )

    redis = FakeRedis([json.dumps({"event_id": event_id})])
    event_repository = FakeEventRepository({event_id: make_event(event_id)})
    run_repository = FakeRunRepository()

    worker = EventWorker(
        redis_client=redis,
        event_repository=event_repository,
        run_repository=run_repository,
        workflow_service=FakeWorkflowService(workflow),
    )

    assert worker.process_next() is True

    assert len(run_repository.runs) == 1

    run = run_repository.runs[0]

    assert run.event_id == event_id
    assert run.workflow_id == "sentry-triage"
    assert run.workflow_version == 7
    assert run.status == RunStatus.QUEUED
    assert run_repository.status_updates == [
        (run.run_id, RunStatus.PROCESSING),
    ]


def test_process_next_returns_false_when_no_active_workflow_matches_event():
    event_id = "event-789"
    redis = FakeRedis([json.dumps({"event_id": event_id})])
    event_repository = FakeEventRepository({event_id: make_event(event_id)})
    run_repository = FakeRunRepository()

    worker = EventWorker(
        redis_client=redis,
        event_repository=event_repository,
        run_repository=run_repository,
        workflow_service=FakeWorkflowService(
            make_workflow(trigger="github")
        ),
    )

    assert worker.process_next() is False
    assert run_repository.runs == []
