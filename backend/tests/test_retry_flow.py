import json
from datetime import datetime, timezone

import pytest

from app.execution.async_executor import AsyncWorkflowNodeExecutor
from app.execution.async_registry import create_async_registry
from app.integrations.registry import IntegrationRegistry
from app.integrations.slack_errors import SlackRetryableAPIError
from app.schemas.event import Event
from app.schemas.run import RunStatus
from app.schemas.workflow import Workflow, WorkflowEdge, WorkflowNode
from app.worker.event_worker import EventWorker


class FakeRedis:
    def __init__(self, items=None):
        self.items = items or []

    def lpop(self, queue_name):
        return self.items.pop(0) if self.items else None


class FakeEventRepository:
    def __init__(self, events):
        self.events = events

    def get_by_id(self, event_id):
        return self.events.get(event_id)


class FakeRunRepository:
    def __init__(self):
        self.runs = []
        self.outputs = {}

    def create(self, run):
        self.runs.append(run)
        return run.run_id

    def update_status(self, run_id, status):
        run = self.get_by_id(run_id)
        if run is None:
            return False
        run.status = status
        return True

    def update_retry_metadata(self, run_id, attempt, last_error):
        run = self.get_by_id(run_id)
        if run is None:
            return False
        run.attempt = attempt
        run.last_error = last_error
        return True

    def update_outputs(self, run_id, outputs):
        self.outputs[run_id] = outputs
        return True

    def get_by_id(self, run_id):
        return next((run for run in self.runs if run.run_id == run_id), None)

    def get_by_execution_key(self, execution_key):
        return next(
            (run for run in self.runs if run.execution_key == execution_key),
            None,
        )


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
        self.scheduled = []
        self.due = []

    def schedule(self, event_id, run_id, attempt, delay):
        self.scheduled.append(
            ({"event_id": event_id, "run_id": run_id, "attempt": attempt}, delay)
        )

    def pop_due(self):
        return self.due.pop(0) if self.due else None


class FailingOnceSlackClient:
    """Fail once, then return a successful Slack response."""

    def __init__(self):
        self.attempts = 0
        self.messages = []

    async def send_message(self, channel: str, text: str):
        self.attempts += 1
        if self.attempts == 1:
            raise SlackRetryableAPIError("Simulated Slack HTTP 500", status_code=500)

        self.messages.append({"channel": channel, "text": text})
        return {"ok": True, "channel": channel, "ts": "retry-success"}


def make_event():
    return Event(
        event_id="retry-event",
        source="sentry",
        event_type="issue.created",
        payload={"message": "PostgreSQL connection timeout", "level": "error"},
        received_at=datetime.now(timezone.utc),
    )


def make_workflow():
    now = datetime.now(timezone.utc)
    return Workflow(
        workflow_id="retry-workflow",
        name="Retry Workflow",
        trigger="sentry",
        version=1,
        status="active",
        nodes=[
            WorkflowNode(id="trigger", type="sentry_trigger"),
            WorkflowNode(
                id="slack",
                type="slack",
                config={
                    "inputs": {
                        "channel": "#incidents",
                        "text": "Retry test notification",
                    },
                },
            ),
        ],
        edges=[WorkflowEdge(source="trigger", target="slack")],
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_retryable_slack_failure_retries_and_completes():
    event = make_event()
    workflow = make_workflow()
    slack_client = FailingOnceSlackClient()
    integrations = IntegrationRegistry(slack_client=slack_client)
    executor = AsyncWorkflowNodeExecutor(create_async_registry(integrations))
    redis = FakeRedis([json.dumps({"event_id": event.event_id})])
    runs = FakeRunRepository()
    retry_queue = FakeRetryQueue()

    worker = EventWorker(
        redis_client=redis,
        event_repository=FakeEventRepository({event.event_id: event}),
        run_repository=runs,
        workflow_service=FakeWorkflowService(workflow),
        async_workflow_executor=executor,
        retry_queue=retry_queue,
    )

    # First attempt: Slack fails with a retryable error.
    assert await worker.process_next_async() is True

    run = runs.runs[0]
    assert run.status == RunStatus.RETRYING
    assert run.attempt == 2
    assert slack_client.attempts == 1
    assert len(retry_queue.scheduled) == 1

    # Make the scheduled retry available to the worker without waiting for time.
    retry_queue.due.append(retry_queue.scheduled[0][0])

    # Second attempt: the same workflow executes again and Slack succeeds.
    assert await worker.process_retry_next_async() is True

    assert run.status == RunStatus.COMPLETED
    assert run.attempt == 2
    assert slack_client.attempts == 2
    assert slack_client.messages == [
        {"channel": "#incidents", "text": "Retry test notification"},
    ]
    assert runs.outputs[run.run_id]["slack"]["response"] == {
        "ok": True,
        "channel": "#incidents",
        "ts": "retry-success",
    }
