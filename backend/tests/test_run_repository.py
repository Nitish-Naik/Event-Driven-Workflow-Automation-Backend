from datetime import datetime, timezone

import pytest
from pymongo.errors import DuplicateKeyError

from app.db.repositories.run import WorkflowRunRepository
from app.schemas.run import RunStatus, WorkflowRun


@pytest.fixture
def run_repository():
    from app.db.mongodb import get_database

    database = get_database().client["sentry_workflow_run_test"]
    database.drop_collection("workflow_runs")

    repository = WorkflowRunRepository(database=database)
    repository.create_indexes()

    yield repository

    database.drop_collection("workflow_runs")


def create_run(run_id="run-123"):
    now = datetime.now(timezone.utc)

    return WorkflowRun(
        run_id=run_id,
        workflow_id="workflow-1",
        workflow_version=1,
        event_id="event-123",
        status=RunStatus.QUEUED,
        created_at=now,
        updated_at=now,
    )


def test_create_and_get_run(run_repository):
    run = create_run()

    run_repository.create(run)

    result = run_repository.get_by_id("run-123")

    assert result is not None
    assert result.run_id == "run-123"
    assert result.workflow_id == "workflow-1"
    assert result.workflow_version == 1
    assert result.event_id == "event-123"
    assert result.status == RunStatus.QUEUED


def test_run_id_is_unique(run_repository):
    run_repository.create(create_run("run-123"))

    with pytest.raises(DuplicateKeyError):
        run_repository.create(create_run("run-123"))


def test_update_status(run_repository):
    run_repository.create(create_run())

    updated = run_repository.update_status(
        "run-123",
        RunStatus.PROCESSING,
    )

    assert updated is True

    result = run_repository.get_by_id("run-123")

    assert result.status == RunStatus.PROCESSING


def test_update_status_for_missing_run(run_repository):
    updated = run_repository.update_status(
        "missing-run",
        RunStatus.PROCESSING,
    )

    assert updated is False