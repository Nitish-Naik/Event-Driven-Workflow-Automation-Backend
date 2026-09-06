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


class FakeWorkflowService:
    def __init__(self, workflow):
        self.workflow = workflow

    def get_active_workflow_by_trigger(self, trigger):
        if trigger == self.workflow.trigger:
            return self.workflow
        return None


def test_worker_uses_default_registry_for_builtin_workflow_nodes():
    now = datetime.now(timezone.utc)
    event = Event(
        event_id="event-default-registry",
        source="sentry",
        event_type="issue.created",
        payload={"message": "Production error", "level": "error"},
        received_at=now,
    )
    workflow = Workflow(
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

    worker = EventWorker(
        redis_client=FakeRedis([json.dumps({"event_id": event.event_id})]),
        event_repository=FakeEventRepository(event),
        run_repository=FakeRunRepository(),
        workflow_service=FakeWorkflowService(workflow),
    )

    assert worker.workflow_executor is not None
    assert worker.workflow_executor.execute(workflow, event).outputs == {
        "trigger": {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "source": event.source,
            "payload": event.payload,
        },
        "normalize": {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "source": event.source,
            "message": "Production error",
            "level": "error",
            "project": None,
            "payload": event.payload,
        },
    }
