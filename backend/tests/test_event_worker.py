import json
from datetime import datetime, timezone

from app.schemas.event import Event
from app.schemas.run import RunStatus, WorkflowRun
from app.schemas.workflow import Workflow
from app.worker.event_worker import EventWorker
from app.services.retry import RetryableExecutionError
from app.services.retry import PermanentExecutionError


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

    def update_retry_metadata(self, run_id, attempt, last_error):
        for run in self.runs:
            if run.run_id == run_id:
                run.attempt = attempt
                run.last_error = last_error
                return True

        return True

    def get_by_id(self, run_id):
        for run in self.runs:
            if run.run_id == run_id:
                return run

        return None


class FakeWorkflowService:
    def __init__(self, workflow=None):
        self.workflow = workflow

    def get_active_workflow_by_trigger(self, trigger):
        if self.workflow is not None and self.workflow.trigger == trigger:
            return self.workflow

        return None

    def get_workflow(self, workflow_id, version):
        if self.workflow is None:
            return None

        if (
            self.workflow.workflow_id == workflow_id
            and self.workflow.version == version
        ):
            return self.workflow

        return None


class FakeWorkflowExecutor:
    def __init__(self, error=None):
        self.calls = []
        self.error = error

    def execute(self, workflow, event):
        self.calls.append((workflow, event))

        if self.error is not None:
            raise self.error

        return None


class FakeRetryQueue:
    def __init__(self):
        self.scheduled = []
        self.due = []

    def pop_due(self):
        if not self.due:
            return None

        return self.due.pop(0)

    def schedule(self, event_id, run_id, attempt, delay):
        self.scheduled.append(
            {
                "event_id": event_id,
                "run_id": run_id,
                "attempt": attempt,
                "delay": delay,
            }
        )


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


def test_process_next_returns_false_for_malformed_json():
    redis = FakeRedis(["not-json"])
    run_repository = FakeRunRepository()

    worker = EventWorker(
        redis_client=redis,
        event_repository=FakeEventRepository(),
        run_repository=run_repository,
        workflow_service=FakeWorkflowService(),
    )

    assert worker.process_next() is False
    assert run_repository.runs == []


def test_process_next_returns_false_when_event_id_is_missing():
    redis = FakeRedis([json.dumps({"foo": "bar"})])
    run_repository = FakeRunRepository()

    worker = EventWorker(
        redis_client=redis,
        event_repository=FakeEventRepository(),
        run_repository=run_repository,
        workflow_service=FakeWorkflowService(),
    )

    assert worker.process_next() is False
    assert run_repository.runs == []


def test_process_next_returns_false_when_event_is_missing():
    event_id = "missing-event"
    redis = FakeRedis([json.dumps({"event_id": event_id})])
    run_repository = FakeRunRepository()

    worker = EventWorker(
        redis_client=redis,
        event_repository=FakeEventRepository(),
        run_repository=run_repository,
        workflow_service=FakeWorkflowService(),
    )

    assert worker.process_next() is False
    assert run_repository.runs == []


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


def test_process_next_completes_run_after_successful_execution():
    event_id = "event-success"
    workflow = make_workflow()
    redis = FakeRedis([json.dumps({"event_id": event_id})])
    event_repository = FakeEventRepository({event_id: make_event(event_id)})
    run_repository = FakeRunRepository()
    executor = FakeWorkflowExecutor()

    worker = EventWorker(
        redis_client=redis,
        event_repository=event_repository,
        run_repository=run_repository,
        workflow_service=FakeWorkflowService(workflow),
        workflow_executor=executor,
    )

    assert worker.process_next() is True

    run = run_repository.runs[0]
    assert executor.calls == [(workflow, event_repository.events[event_id])]
    assert run_repository.status_updates == [
        (run.run_id, RunStatus.PROCESSING),
        (run.run_id, RunStatus.COMPLETED),
    ]


def test_process_next_fails_run_when_execution_raises():
    event_id = "event-failure"
    workflow = make_workflow()
    redis = FakeRedis([json.dumps({"event_id": event_id})])
    event_repository = FakeEventRepository({event_id: make_event(event_id)})
    run_repository = FakeRunRepository()
    executor = FakeWorkflowExecutor(error=RuntimeError("node failed"))

    worker = EventWorker(
        redis_client=redis,
        event_repository=event_repository,
        run_repository=run_repository,
        workflow_service=FakeWorkflowService(workflow),
        workflow_executor=executor,
    )

    assert worker.process_next() is True

    run = run_repository.runs[0]
    assert executor.calls == [(workflow, event_repository.events[event_id])]
    assert run_repository.status_updates == [
        (run.run_id, RunStatus.PROCESSING),
        (run.run_id, RunStatus.FAILED),
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


def test_retryable_execution_error_schedules_retry():
    redis = FakeRedis()
    event_repository = FakeEventRepository()
    run_repository = FakeRunRepository()
    workflow_service = FakeWorkflowService()
    retry_queue = FakeRetryQueue()

    event = make_event()
    workflow = make_workflow()

    event_repository.events[event.event_id] = event
    workflow_service.workflow = workflow

    class FailingExecutor:
        def execute(self, workflow, event):
            raise RetryableExecutionError("Sentry API unavailable")

    worker = EventWorker(
        redis_client=redis,
        event_repository=event_repository,
        run_repository=run_repository,
        workflow_service=workflow_service,
        workflow_executor=FailingExecutor(),
        retry_queue=retry_queue,
    )

    redis.items.append(json.dumps({"event_id": event.event_id}))

    result = worker.process_next()

    assert result is True
    assert len(retry_queue.scheduled) == 1

    scheduled = retry_queue.scheduled[0]

    assert scheduled["event_id"] == event.event_id
    assert scheduled["attempt"] == 2
    assert scheduled["delay"] > 0


def test_permanent_execution_error_does_not_schedule_retry():
    redis = FakeRedis()
    event_repository = FakeEventRepository()
    run_repository = FakeRunRepository()
    workflow_service = FakeWorkflowService()
    retry_queue = FakeRetryQueue()

    event = make_event()
    workflow = make_workflow()

    event_repository.events[event.event_id] = event
    workflow_service.workflow = workflow

    class FailingExecutor:
        def execute(self, workflow, event):
            raise PermanentExecutionError("Invalid workflow configuration")

    worker = EventWorker(
        redis_client=redis,
        event_repository=event_repository,
        run_repository=run_repository,
        workflow_service=workflow_service,
        workflow_executor=FailingExecutor(),
        retry_queue=retry_queue,
    )

    redis.items.append(json.dumps({"event_id": event.event_id}))

    result = worker.process_next()

    assert result is True
    assert retry_queue.scheduled == []


def test_process_retry_next_returns_false_when_no_retry_is_due():
    worker = EventWorker(
        redis_client=FakeRedis(),
        event_repository=FakeEventRepository(),
        run_repository=FakeRunRepository(),
        workflow_service=FakeWorkflowService(),
        retry_queue=FakeRetryQueue(),
    )

    assert worker.process_retry_next() is False


def test_process_retry_next_returns_false_when_event_is_missing():
    workflow = make_workflow()
    run = WorkflowRun(
        run_id="run-missing-event",
        workflow_id=workflow.workflow_id,
        workflow_version=workflow.version,
        event_id="missing-event",
        status=RunStatus.RETRYING,
        attempt=2,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    run_repository = FakeRunRepository()
    run_repository.create(run)

    retry_queue = FakeRetryQueue()
    retry_queue.due.append(
        {
            "event_id": run.event_id,
            "run_id": run.run_id,
            "attempt": run.attempt,
        }
    )

    worker = EventWorker(
        redis_client=FakeRedis(),
        event_repository=FakeEventRepository(),
        run_repository=run_repository,
        workflow_service=FakeWorkflowService(workflow),
        retry_queue=retry_queue,
    )

    assert worker.process_retry_next() is False
    assert run_repository.status_updates == []


def test_process_retry_next_returns_false_when_run_is_missing():
    event = make_event()
    workflow = make_workflow()

    retry_queue = FakeRetryQueue()
    retry_queue.due.append(
        {
            "event_id": event.event_id,
            "run_id": "missing-run",
            "attempt": 2,
        }
    )

    worker = EventWorker(
        redis_client=FakeRedis(),
        event_repository=FakeEventRepository({event.event_id: event}),
        run_repository=FakeRunRepository(),
        workflow_service=FakeWorkflowService(workflow),
        retry_queue=retry_queue,
    )

    assert worker.process_retry_next() is False


def test_process_retry_next_returns_false_when_workflow_version_is_missing():
    event = make_event()
    stored_workflow = make_workflow(version=3)
    current_workflow = make_workflow(version=4)

    run = WorkflowRun(
        run_id="run-missing-workflow-version",
        workflow_id=stored_workflow.workflow_id,
        workflow_version=stored_workflow.version,
        event_id=event.event_id,
        status=RunStatus.RETRYING,
        attempt=2,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    run_repository = FakeRunRepository()
    run_repository.create(run)

    retry_queue = FakeRetryQueue()
    retry_queue.due.append(
        {
            "event_id": event.event_id,
            "run_id": run.run_id,
            "attempt": run.attempt,
        }
    )

    worker = EventWorker(
        redis_client=FakeRedis(),
        event_repository=FakeEventRepository({event.event_id: event}),
        run_repository=run_repository,
        workflow_service=FakeWorkflowService(current_workflow),
        retry_queue=retry_queue,
    )

    assert worker.process_retry_next() is False
    assert run_repository.status_updates == []


def test_process_retry_next_completes_existing_run():
    event = make_event()
    workflow = make_workflow()

    event_repository = FakeEventRepository({event.event_id: event})
    run_repository = FakeRunRepository()

    run = WorkflowRun(
        run_id="run-retry",
        workflow_id=workflow.workflow_id,
        workflow_version=workflow.version,
        event_id=event.event_id,
        status=RunStatus.RETRYING,
        attempt=2,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    run_repository.create(run)

    workflow_service = FakeWorkflowService(workflow)
    retry_queue = FakeRetryQueue()

    retry_queue.due.append(
        {
            "event_id": event.event_id,
            "run_id": run.run_id,
            "attempt": 2,
        }
    )

    executor = FakeWorkflowExecutor()

    worker = EventWorker(
        redis_client=FakeRedis(),
        event_repository=event_repository,
        run_repository=run_repository,
        workflow_service=workflow_service,
        workflow_executor=executor,
        retry_queue=retry_queue,
    )

    assert worker.process_retry_next() is True
    assert executor.calls == [(workflow, event)]
    assert run_repository.status_updates == [
        (run.run_id, RunStatus.PROCESSING),
        (run.run_id, RunStatus.COMPLETED),
    ]
    assert run.run_id == "run-retry"
    assert run.attempt == 2


def test_process_retry_next_dead_letters_after_max_attempts():
    event = make_event()
    workflow = make_workflow()

    run = WorkflowRun(
        run_id="run-123",
        workflow_id=workflow.workflow_id,
        workflow_version=workflow.version,
        event_id=event.event_id,
        status=RunStatus.RETRYING,
        attempt=3,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    redis = FakeRedis()
    event_repository = FakeEventRepository({event.event_id: event})

    run_repository = FakeRunRepository()
    run_repository.runs.append(run)

    workflow_service = FakeWorkflowService(workflow)
    executor = FakeWorkflowExecutor(RetryableExecutionError("temporary failure"))

    retry_queue = FakeRetryQueue()
    retry_queue.due.append(
        {
            "event_id": event.event_id,
            "run_id": run.run_id,
            "attempt": 3,
        }
    )

    worker = EventWorker(
        redis_client=redis,
        event_repository=event_repository,
        run_repository=run_repository,
        workflow_service=workflow_service,
        workflow_executor=executor,
        retry_queue=retry_queue,
    )

    result = worker.process_retry_next()

    assert result is True
    assert run_repository.status_updates == [
        (run.run_id, RunStatus.PROCESSING),
        (run.run_id, RunStatus.FAILED),
        (run.run_id, RunStatus.DEAD_LETTER),
    ]
    assert retry_queue.scheduled == []


def test_process_retry_next_permanent_failure_does_not_retry():
    event = make_event()
    workflow = make_workflow()

    run = WorkflowRun(
        run_id="run-456",
        workflow_id=workflow.workflow_id,
        workflow_version=workflow.version,
        event_id=event.event_id,
        status=RunStatus.RETRYING,
        attempt=2,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    redis = FakeRedis()
    event_repository = FakeEventRepository({event.event_id: event})

    run_repository = FakeRunRepository()
    run_repository.runs.append(run)

    workflow_service = FakeWorkflowService(workflow)
    executor = FakeWorkflowExecutor(PermanentExecutionError("invalid configuration"))

    retry_queue = FakeRetryQueue()
    retry_queue.due.append(
        {
            "event_id": event.event_id,
            "run_id": run.run_id,
            "attempt": 2,
        }
    )

    worker = EventWorker(
        redis_client=redis,
        event_repository=event_repository,
        run_repository=run_repository,
        workflow_service=workflow_service,
        workflow_executor=executor,
        retry_queue=retry_queue,
    )

    result = worker.process_retry_next()

    assert result is True
    assert run_repository.status_updates == [
        (run.run_id, RunStatus.PROCESSING),
        (run.run_id, RunStatus.FAILED),
    ]
    assert retry_queue.scheduled == []
