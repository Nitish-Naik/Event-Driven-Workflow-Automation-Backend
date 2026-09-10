import json
from datetime import datetime, timezone

import pytest

from app.schemas.event import Event
from app.schemas.run import RunStatus, WorkflowRun
from app.schemas.workflow import Workflow
from app.worker.async_event_worker import AsyncEventWorker


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
        self.outputs = {}

    def create(self, run):
        self.runs.append(run)
        return run.run_id

    def update_status(self, run_id, status):
        self.status_updates.append((run_id, status))
        return True

    def update_outputs(self, run_id, outputs):
        self.outputs[run_id] = outputs
        return True

    def update_retry_metadata(self, run_id, attempt, last_error):
        for run in self.runs:
            if run.run_id == run_id:
                run.attempt = attempt
                run.last_error = last_error
                return True
        return True

    def get_by_id(self, run_id):
        return next((run for run in self.runs if run.run_id == run_id), None)


class FakeWorkflowService:
    def __init__(self, workflow):
        self.workflow = workflow

    def get_active_workflow_by_trigger(self, trigger):
        if self.workflow and self.workflow.trigger == trigger:
            return self.workflow
        return None

    def get_workflow(self, workflow_id, version):
        if (
            self.workflow
            and self.workflow.workflow_id == workflow_id
            and self.workflow.version == version
        ):
            return self.workflow
        return None


class FakeRetryQueue:
    def __init__(self):
        self.due = []
        self.scheduled = []

    def pop_due(self):
        return self.due.pop(0) if self.due else None

    def schedule(self, event_id, run_id, attempt, delay):
        self.scheduled.append(
            {
                "event_id": event_id,
                "run_id": run_id,
                "attempt": attempt,
                "delay": delay,
            }
        )


class FakeAsyncExecutor:
    def __init__(self, result=None, error=None):
        self.calls = []
        self.result = result
        self.error = error

    async def execute(self, context):
        self.calls.append(context)
        if self.error:
            raise self.error
        return self.result


def make_event(event_id="event-1"):
    return Event(
        event_id=event_id,
        source="sentry",
        event_type="issue.created",
        received_at=datetime.now(timezone.utc),
    )


def make_workflow(version=3):
    now = datetime.now(timezone.utc)
    return Workflow(
        workflow_id="sentry-workflow",
        name="Sentry triage",
        trigger="sentry",
        version=version,
        status="active",
        nodes=[{"id": "trigger", "type": "sentry_trigger"}],
        edges=[],
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_process_next_uses_async_executor_and_persists_outputs():
    event = make_event()
    workflow = make_workflow(version=7)
    run_repository = FakeRunRepository()
    executor = FakeAsyncExecutor(result=type("Result", (), {"outputs": {"trigger": {"ok": True}}})())

    worker = AsyncEventWorker(
        redis_client=FakeRedis([json.dumps({"event_id": event.event_id})]),
        event_repository=FakeEventRepository({event.event_id: event}),
        run_repository=run_repository,
        workflow_service=FakeWorkflowService(workflow),
        workflow_executor=executor,
        retry_queue=FakeRetryQueue(),
    )

    assert await worker.process_next() is True

    run = run_repository.runs[0]
    assert executor.calls[0].workflow.version == 7
    assert executor.calls[0].event.event_id == event.event_id
    assert run.workflow_version == 7
    assert run_repository.outputs[run.run_id] == {"trigger": {"ok": True}}
    assert run_repository.status_updates == [
        (run.run_id, RunStatus.PROCESSING),
        (run.run_id, RunStatus.COMPLETED),
    ]


@pytest.mark.asyncio
async def test_process_retry_next_reuses_exact_workflow_version():
    event = make_event()
    workflow = make_workflow(version=9)
    run_repository = FakeRunRepository()
    run = WorkflowRun(
        run_id="run-1",
        workflow_id=workflow.workflow_id,
        workflow_version=workflow.version,
        event_id=event.event_id,
        status=RunStatus.RETRYING,
        attempt=2,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    run_repository.create(run)

    executor = FakeAsyncExecutor(result=type("Result", (), {"outputs": {"done": True}})())
    retry_queue = FakeRetryQueue()
    retry_queue.due.append(
        {"event_id": event.event_id, "run_id": run.run_id, "attempt": 2}
    )

    worker = AsyncEventWorker(
        redis_client=FakeRedis(),
        event_repository=FakeEventRepository({event.event_id: event}),
        run_repository=run_repository,
        workflow_service=FakeWorkflowService(workflow),
        workflow_executor=executor,
        retry_queue=retry_queue,
    )

    assert await worker.process_retry_next() is True
    assert executor.calls[0].workflow.version == 9
    assert run.attempt == 2
    assert run_repository.status_updates == [
        (run.run_id, RunStatus.PROCESSING),
        (run.run_id, RunStatus.COMPLETED),
    ]
