import json
from datetime import datetime, timezone

from app.execution.contracts import ExecutionContext
from app.execution.executor import WorkflowNodeExecutor
from app.execution.registry import NodeRegistry
from app.schemas.event import Event
from app.schemas.run import RunStatus
from app.schemas.workflow import Workflow
from app.services.retry import RetryableExecutionError
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
        for run in self.runs:
            if run.run_id == run_id:
                run.status = status
                return True
        return False

    def update_retry_metadata(self, run_id, attempt, last_error):
        for run in self.runs:
            if run.run_id == run_id:
                run.attempt = attempt
                run.last_error = last_error
                return True
        return False

    def get_by_id(self, run_id):
        for run in self.runs:
            if run.run_id == run_id:
                return run
        return None


class FakeWorkflowService:
    def __init__(self, workflow):
        self.workflow = workflow

    def get_active_workflow_by_trigger(self, trigger):
        if self.workflow.trigger == trigger:
            return self.workflow
        return None

    def get_workflow(self, workflow_id, version):
        if (
            self.workflow.workflow_id == workflow_id
            and self.workflow.version == version
        ):
            return self.workflow
        return None


class FakeRetryQueue:
    def __init__(self):
        self.scheduled = []
        self.due = []

    def schedule(self, event_id, run_id, attempt, delay):
        self.scheduled.append(
            {
                "event_id": event_id,
                "run_id": run_id,
                "attempt": attempt,
                "delay": delay,
            }
        )

    def pop_due(self):
        if not self.due:
            return None
        return self.due.pop(0)


def make_event():
    return Event(
        event_id="event-integration",
        source="sentry",
        event_type="issue.created",
        payload={"message": "Database timeout"},
        received_at=datetime.now(timezone.utc),
    )


def make_workflow():
    now = datetime.now(timezone.utc)
    return Workflow(
        workflow_id="sentry-triage",
        name="Sentry Incident Triage",
        trigger="sentry",
        version=7,
        status="active",
        nodes=[
            {"id": "trigger", "type": "sentry_trigger"},
            {"id": "processor", "type": "processor"},
        ],
        edges=[{"source": "trigger", "target": "processor"}],
        created_at=now,
        updated_at=now,
    )


def test_worker_retries_real_executor_and_completes_same_run():
    event = make_event()
    workflow = make_workflow()
    redis = FakeRedis([json.dumps({"event_id": event.event_id})])
    event_repository = FakeEventRepository({event.event_id: event})
    run_repository = FakeRunRepository()
    workflow_service = FakeWorkflowService(workflow)
    retry_queue = FakeRetryQueue()

    attempts = []

    def processor_handler(
        context: ExecutionContext,
        config,
        inputs,
    ):
        attempts.append(context.event.event_id)
        if len(attempts) == 1:
            raise RetryableExecutionError("Sentry API unavailable")
        return {"processed": True}

    registry = NodeRegistry({"processor": processor_handler})
    executor = WorkflowNodeExecutor(registry=registry)
    worker = EventWorker(
        redis_client=redis,
        event_repository=event_repository,
        run_repository=run_repository,
        workflow_service=workflow_service,
        workflow_executor=executor,
        retry_queue=retry_queue,
    )

    assert worker.process_next() is True

    run = run_repository.runs[0]
    assert run.workflow_id == workflow.workflow_id
    assert run.workflow_version == workflow.version
    assert run.event_id == event.event_id
    assert run.status == RunStatus.RETRYING
    assert run.attempt == 2
    assert run.last_error == "Sentry API unavailable"
    assert len(retry_queue.scheduled) == 1
    assert retry_queue.scheduled[0]["run_id"] == run.run_id
    assert retry_queue.scheduled[0]["attempt"] == 2

    retry_queue.due.append(
        {
            "event_id": event.event_id,
            "run_id": run.run_id,
            "attempt": 2,
        }
    )

    assert worker.process_retry_next() is True

    assert run.status == RunStatus.COMPLETED
    assert run.attempt == 2
    assert attempts == [event.event_id, event.event_id]
    assert run_repository.status_updates == [
        (run.run_id, RunStatus.PROCESSING),
        (run.run_id, RunStatus.FAILED),
        (run.run_id, RunStatus.RETRYING),
        (run.run_id, RunStatus.PROCESSING),
        (run.run_id, RunStatus.COMPLETED),
    ]
