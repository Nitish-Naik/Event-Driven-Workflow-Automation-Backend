import json
from datetime import datetime, timezone

import pytest

from app.execution.async_executor import AsyncWorkflowNodeExecutor
from app.execution.async_registry import create_async_registry
from app.execution.contracts import ExecutionResult
from app.integrations.registry import IntegrationRegistry
from app.schemas.event import Event
from app.schemas.run import RunStatus
from app.schemas.workflow import Workflow, WorkflowEdge, WorkflowNode
from app.worker.event_worker import EventWorker


class FakeRedis:
    def __init__(self, items=None):
        self.items = items or []

    def lpop(self, queue_name):
        if not self.items:
            return None
        return self.items.pop(0)


class FakeEventRepository:
    def __init__(self, events):
        self.events = events

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
        for run in self.runs:
            if run.run_id == run_id:
                run.status = status
                return True
        return False

    def update_outputs(self, run_id, outputs):
        self.outputs[run_id] = outputs
        return True

    def get_by_id(self, run_id):
        return next((run for run in self.runs if run.run_id == run_id), None)


class FakeWorkflowService:
    def __init__(self, workflow):
        self.workflow = workflow

    def get_active_workflow_by_trigger(self, trigger):
        return self.workflow if self.workflow.trigger == trigger else None

    def get_workflow(self, workflow_id, version):
        if self.workflow.workflow_id == workflow_id and self.workflow.version == version:
            return self.workflow
        return None


class FakeRetryQueue:
    def __init__(self):
        self.due = []
        self.scheduled = []

    def pop_due(self):
        return self.due.pop(0) if self.due else None

    def schedule(self, event_id, run_id, attempt, delay):
        self.scheduled.append((event_id, run_id, attempt, delay))


class FakeAsyncExecutor:
    def __init__(self):
        self.contexts = []

    async def execute(self, context):
        self.contexts.append(context)
        return ExecutionResult(outputs={"tool": {"ok": True}})


def make_event():
    return Event(
        event_id="async-event",
        source="sentry",
        event_type="issue.created",
        payload={"message": "failure"},
        received_at=datetime.now(timezone.utc),
    )


def make_workflow():
    now = datetime.now(timezone.utc)
    return Workflow(
        workflow_id="async-workflow",
        name="Async Workflow",
        trigger="sentry",
        version=3,
        status="active",
        nodes=[],
        edges=[],
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_process_next_async_executes_and_persists_outputs():
    event = make_event()
    workflow = make_workflow()
    redis = FakeRedis([json.dumps({"event_id": event.event_id})])
    runs = FakeRunRepository()
    executor = FakeAsyncExecutor()

    worker = EventWorker(
        redis_client=redis,
        event_repository=FakeEventRepository({event.event_id: event}),
        run_repository=runs,
        workflow_service=FakeWorkflowService(workflow),
        async_workflow_executor=executor,
        retry_queue=FakeRetryQueue(),
    )

    assert await worker.process_next_async() is True

    run = runs.runs[0]
    assert run.workflow_id == workflow.workflow_id
    assert run.workflow_version == workflow.version
    assert run.event_id == event.event_id
    assert run.status == RunStatus.COMPLETED
    assert runs.outputs[run.run_id] == {"tool": {"ok": True}}
    assert executor.contexts[0].event.event_id == event.event_id
    assert runs.status_updates == [
        (run.run_id, RunStatus.PROCESSING),
        (run.run_id, RunStatus.COMPLETED),
    ]


@pytest.mark.asyncio
async def test_process_next_async_executes_real_sentry_tool_workflow():
    class FakeSentryClient:
        async def get_issue(self, issue_id: str):
            return {
                "id": issue_id,
                "title": "Database connection failed",
                "status": "unresolved",
            }

    event = Event(
        event_id="sentry-event-e2e",
        source="sentry",
        event_type="issue.created",
        payload={"message": "Database connection failed"},
        received_at=datetime.now(timezone.utc),
    )
    now = datetime.now(timezone.utc)
    workflow = Workflow(
        workflow_id="sentry-tool-workflow",
        name="Sentry Tool Workflow",
        trigger="sentry",
        version=1,
        status="active",
        nodes=[
            WorkflowNode(id="trigger", type="sentry_trigger"),
            WorkflowNode(
                id="get_issue",
                type="tool",
                config={
                    "integration": "sentry",
                    "tool": "sentry.get_issue",
                    "inputs": {"issue_id": "123"},
                },
            ),
        ],
        edges=[WorkflowEdge(source="trigger", target="get_issue")],
        created_at=now,
        updated_at=now,
    )

    integrations = IntegrationRegistry(sentry_client=FakeSentryClient())
    executor = AsyncWorkflowNodeExecutor(create_async_registry(integrations))
    redis = FakeRedis([json.dumps({"event_id": event.event_id})])
    runs = FakeRunRepository()

    worker = EventWorker(
        redis_client=redis,
        event_repository=FakeEventRepository({event.event_id: event}),
        run_repository=runs,
        workflow_service=FakeWorkflowService(workflow),
        async_workflow_executor=executor,
        retry_queue=FakeRetryQueue(),
    )

    assert await worker.process_next_async() is True

    run = runs.runs[0]
    assert run.status == RunStatus.COMPLETED
    assert runs.outputs[run.run_id]["trigger"]["event_id"] == event.event_id
    assert runs.outputs[run.run_id]["get_issue"] == {
        "id": "123",
        "title": "Database connection failed",
        "status": "unresolved",
    }
