from datetime import datetime, timezone

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


def test_workflow_run_statuses():
    assert RunStatus.QUEUED == "queued"
    assert RunStatus.PROCESSING == "processing"
    assert RunStatus.COMPLETED == "completed"
    assert RunStatus.FAILED == "failed"
    assert RunStatus.RETRYING == "retrying"
    assert RunStatus.DEAD_LETTER == "dead_letter"