from datetime import datetime, timezone

import pytest

from app.schemas.run import RunStatus, WorkflowRun


def test_create_workflow_run():
    now = datetime.now(timezone.utc)

    run = WorkflowRun(
        run_id="run-123",
        workflow_id="workflow-1",
        workflow_version=2,
        event_id="event-123",
        status=RunStatus.QUEUED,
        created_at=now,
        updated_at=now,
    )

    assert run.run_id == "run-123"
    assert run.workflow_id == "workflow-1"
    assert run.workflow_version == 2
    assert run.event_id == "event-123"
    assert run.status == RunStatus.QUEUED
    assert run.attempt == 1
    assert run.last_error is None


def test_workflow_run_retry_metadata():
    now = datetime.now(timezone.utc)

    run = WorkflowRun(
        run_id="run-123",
        workflow_id="workflow-1",
        workflow_version=2,
        event_id="event-123",
        status=RunStatus.FAILED,
        attempt=3,
        last_error="Sentry API timed out",
        created_at=now,
        updated_at=now,
    )

    assert run.attempt == 3
    assert run.last_error == "Sentry API timed out"


def test_workflow_run_attempt_must_be_positive():
    now = datetime.now(timezone.utc)

    with pytest.raises(ValueError):
        WorkflowRun(
            run_id="run-123",
            workflow_id="workflow-1",
            workflow_version=1,
            event_id="event-123",
            status=RunStatus.FAILED,
            attempt=0,
            created_at=now,
            updated_at=now,
        )


def test_workflow_run_statuses():
    assert RunStatus.QUEUED == "queued"
    assert RunStatus.PROCESSING == "processing"
    assert RunStatus.COMPLETED == "completed"
    assert RunStatus.FAILED == "failed"
    assert RunStatus.RETRYING == "retrying"
    assert RunStatus.DEAD_LETTER == "dead_letter"
