from datetime import datetime, timezone
import json

from app.execution.builtins import NORMALIZE_EVENT, SENTRY_TRIGGER
from app.schemas.event import Event
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
    def __init__(self, event):
        self.event = event

    def get_by_id(self, event_id):
        if event_id == self.event.event_id:
            return self.event
        return None


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


def make_workflow(now):
    return Workflow(
        workflow_id="default-registry-workflow",
        name="Sentry normalization",
        trigger="sentry",
        version=1,
        status="active",
        nodes=[
            {"id": "trigger", "type": SENTRY_TRIGGER},
            {"id": "normalize", "type": NORMALIZE_EVENT},
        ],
        edges=[{"source": "trigger", "target": "normalize"}],
        created_at=now,
        updated_at=now,
    )


def make_event(now):
    return Event(
        event_id="event-default-registry",
        source="sentry",
        event_type="issue.created",
        payload={"message": "Production error", "level": "error"},
        received_at=now,
    )


def test_worker_uses_default_registry_for_builtin_workflow_nodes():
    now = datetime.now(timezone.utc)
    event = make_event(now)
    workflow = make_workflow(now)
    run_repository = FakeRunRepository()

    worker = EventWorker(
        redis_client=FakeRedis([json.dumps({"event_id": event.event_id})]),
        event_repository=FakeEventRepository(event),
        run_repository=run_repository,
        workflow_service=type(
            "FakeWorkflowService",
            (),
            {
                "get_active_workflow_by_trigger": lambda self, trigger: (
                    workflow if trigger == workflow.trigger else None
                )
            },
        )(),
    )

    assert worker.workflow_executor is not None
    assert worker.process_next() is True
    assert run_repository.status_updates == [
        (run_repository.runs[0].run_id, "processing"),
        (run_repository.runs[0].run_id, "completed"),
    ]
