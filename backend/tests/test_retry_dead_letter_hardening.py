from datetime import datetime, timezone

import pytest

from app.schemas.event import Event
from app.schemas.run import RunStatus, WorkflowRun
from app.schemas.workflow import Workflow
from app.services.retry import (
    PermanentExecutionError,
    RetryableExecutionError,
    calculate_retry_delay,
)
from app.worker.event_worker import EventWorker


class FakeRedis:
    def __init__(self):
        self.items = []

    def lpop(self, _queue):
        return self.items.pop(0) if self.items else None


class FakeEventRepository:
    def __init__(self, event):
        self.event = event

    def get_by_id(self, event_id):
        return self.event if event_id == self.event.event_id else None


class FakeRunRepository:
    def __init__(self, run=None):
        self.runs = [] if run is None else [run]
        self.status_updates = []
        self.retry_updates = []

    def create(self, run):
        self.runs.append(run)
        return run.run_id

    def get_by_id(self, run_id):
        return next((run for run in self.runs if run.run_id == run_id), None)

    def update_status(self, run_id, status):
        self.status_updates.append((run_id, status))
        run = self.get_by_id(run_id)
        if run is not None:
            run.status = status
        return True

    def update_retry_metadata(self, run_id, attempt, last_error):
        run = self.get_by_id(run_id)
        if run is not None:
            run.attempt = attempt
            run.last_error = last_error
        self.retry_updates.append((run_id, attempt, last_error))
        return True


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


class FailingExecutor:
    def __init__(self, error):
        self.error = error
        self.calls = 0

    def execute(self, workflow, event):
        self.calls += 1
        raise self.error


def make_event():
    return Event(
        event_id="event-1",
        source="sentry",
        event_type="issue.created",
        received_at=datetime.now(timezone.utc),
    )


def make_workflow():
    now = datetime.now(timezone.utc)
    return Workflow(
        workflow_id="workflow-1",
        name="Sentry triage",
        trigger="sentry",
        version=1,
        status="active",
        nodes=[{"id": "trigger", "type": "sentry_trigger"}],
        edges=[],
        created_at=now,
        updated_at=now,
    )


def make_retrying_run(attempt=2, status=RunStatus.RETRYING):
    now = datetime.now(timezone.utc)
    return WorkflowRun(
        run_id="run-1",
        workflow_id="workflow-1",
        workflow_version=1,
        event_id="event-1",
        status=status,
        attempt=attempt,
        created_at=now,
        updated_at=now,
    )


def test_retry_delay_is_exponential_and_bounded(monkeypatch):
    monkeypatch.setattr("app.services.retry.random.uniform", lambda _low, _high: 0.0)

    assert calculate_retry_delay(1, base_delay=1, max_delay=10, jitter_ratio=0.1) == 1
    assert calculate_retry_delay(2, base_delay=1, max_delay=10, jitter_ratio=0.1) == 2
    assert calculate_retry_delay(3, base_delay=1, max_delay=10, jitter_ratio=0.1) == 4
    assert calculate_retry_delay(10, base_delay=1, max_delay=10, jitter_ratio=0.1) == 10


def test_retry_delay_rejects_invalid_policy():
    with pytest.raises(ValueError):
        calculate_retry_delay(0)
    with pytest.raises(ValueError):
        calculate_retry_delay(1, base_delay=-1)
    with pytest.raises(ValueError):
        calculate_retry_delay(1, base_delay=5, max_delay=1)
    with pytest.raises(ValueError):
        calculate_retry_delay(1, jitter_ratio=-0.1)


def test_retryable_failure_transitions_to_retrying_and_schedules_next_attempt(monkeypatch):
    event = make_event()
    workflow = make_workflow()
    runs = FakeRunRepository()
    retry_queue = FakeRetryQueue()
    executor = FailingExecutor(RetryableExecutionError("temporary upstream failure"))
    monkeypatch.setattr("app.worker.event_worker.calculate_retry_delay", lambda attempt: 4.0)

    worker = EventWorker(
        redis_client=FakeRedis(),
        event_repository=FakeEventRepository(event),
        run_repository=runs,
        workflow_service=FakeWorkflowService(workflow),
        workflow_executor=executor,
        retry_queue=retry_queue,
    )

    worker.redis.items.append('{"event_id":"event-1"}')
    assert worker.process_next() is True

    run = runs.runs[0]
    assert run.attempt == 2
    assert run.status == RunStatus.RETRYING
    assert run.last_error == "temporary upstream failure"
    assert retry_queue.scheduled == [("event-1", run.run_id, 2, 4.0)]
    assert runs.status_updates == [
        (run.run_id, RunStatus.PROCESSING),
        (run.run_id, RunStatus.FAILED),
        (run.run_id, RunStatus.RETRYING),
    ]


def test_max_attempts_moves_retryable_failure_to_dead_letter(monkeypatch):
    event = make_event()
    workflow = make_workflow()
    run = make_retrying_run(attempt=EventWorker.MAX_ATTEMPTS)
    runs = FakeRunRepository(run)
    retry_queue = FakeRetryQueue()
    executor = FailingExecutor(RetryableExecutionError("still unavailable"))
    monkeypatch.setattr("app.worker.event_worker.calculate_retry_delay", lambda _attempt: 99.0)

    worker = EventWorker(
        redis_client=FakeRedis(),
        event_repository=FakeEventRepository(event),
        run_repository=runs,
        workflow_service=FakeWorkflowService(workflow),
        workflow_executor=executor,
        retry_queue=retry_queue,
    )

    retry_queue.due.append({"event_id": "event-1", "run_id": "run-1", "attempt": 3})
    assert worker.process_retry_next() is True

    assert executor.calls == 1
    assert run.status == RunStatus.DEAD_LETTER
    assert retry_queue.scheduled == []
    assert runs.status_updates == [
        ("run-1", RunStatus.PROCESSING),
        ("run-1", RunStatus.FAILED),
        ("run-1", RunStatus.DEAD_LETTER),
    ]


def test_permanent_failure_never_schedules_retry():
    event = make_event()
    workflow = make_workflow()
    runs = FakeRunRepository()
    retry_queue = FakeRetryQueue()
    executor = FailingExecutor(PermanentExecutionError("invalid request"))

    worker = EventWorker(
        redis_client=FakeRedis(),
        event_repository=FakeEventRepository(event),
        run_repository=runs,
        workflow_service=FakeWorkflowService(workflow),
        workflow_executor=executor,
        retry_queue=retry_queue,
    )

    worker.redis.items.append('{"event_id":"event-1"}')
    assert worker.process_next() is True

    run = runs.runs[0]
    assert run.status == RunStatus.FAILED
    assert retry_queue.scheduled == []


def test_stale_retry_message_is_not_executed():
    event = make_event()
    workflow = make_workflow()
    run = make_retrying_run(attempt=3)
    runs = FakeRunRepository(run)
    retry_queue = FakeRetryQueue()
    executor = FailingExecutor(RetryableExecutionError("should not run"))

    worker = EventWorker(
        redis_client=FakeRedis(),
        event_repository=FakeEventRepository(event),
        run_repository=runs,
        workflow_service=FakeWorkflowService(workflow),
        workflow_executor=executor,
        retry_queue=retry_queue,
    )

    retry_queue.due.append({"event_id": "event-1", "run_id": "run-1", "attempt": 2})
    assert worker.process_retry_next() is False
    assert executor.calls == 0
    assert runs.status_updates == []


def test_terminal_run_ignores_late_retry_message():
    event = make_event()
    workflow = make_workflow()
    run = make_retrying_run(attempt=2, status=RunStatus.COMPLETED)
    runs = FakeRunRepository(run)
    retry_queue = FakeRetryQueue()
    executor = FailingExecutor(RetryableExecutionError("should not run"))

    worker = EventWorker(
        redis_client=FakeRedis(),
        event_repository=FakeEventRepository(event),
        run_repository=runs,
        workflow_service=FakeWorkflowService(workflow),
        workflow_executor=executor,
        retry_queue=retry_queue,
    )

    retry_queue.due.append({"event_id": "event-1", "run_id": "run-1", "attempt": 2})
    assert worker.process_retry_next() is False
    assert executor.calls == 0
    assert runs.status_updates == []
