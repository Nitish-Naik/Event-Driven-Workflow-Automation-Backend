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


def create_run(
    run_id="run-123",
    status=RunStatus.QUEUED,
    attempt=1,
):
    now = datetime.now(timezone.utc)

    return WorkflowRun(
        run_id=run_id,
        workflow_id="workflow-1",
        workflow_version=1,
        event_id="event-123",
        status=status,
        attempt=attempt,
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
    assert result.attempt == 1


def test_get_by_id_returns_none_for_unknown_run(run_repository):
    result = run_repository.get_by_id("does-not-exist")

    assert result is None


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


def test_processing_run_can_complete(run_repository):
    run_repository.create(
        create_run(status=RunStatus.PROCESSING)
    )

    updated = run_repository.update_status(
        "run-123",
        RunStatus.COMPLETED,
    )

    assert updated is True
    assert (
        run_repository.get_by_id("run-123").status
        == RunStatus.COMPLETED
    )


def test_processing_run_can_fail(run_repository):
    run_repository.create(
        create_run(status=RunStatus.PROCESSING)
    )

    updated = run_repository.update_status(
        "run-123",
        RunStatus.FAILED,
    )

    assert updated is True
    assert (
        run_repository.get_by_id("run-123").status
        == RunStatus.FAILED
    )


def test_failed_run_can_enter_retrying(run_repository):
    run_repository.create(
        create_run(status=RunStatus.FAILED)
    )

    updated = run_repository.update_status(
        "run-123",
        RunStatus.RETRYING,
    )

    assert updated is True
    assert (
        run_repository.get_by_id("run-123").status
        == RunStatus.RETRYING
    )


def test_failed_run_can_enter_dead_letter(run_repository):
    run_repository.create(
        create_run(
            status=RunStatus.FAILED,
            attempt=3,
        )
    )

    updated = run_repository.update_status(
        "run-123",
        RunStatus.DEAD_LETTER,
    )

    assert updated is True
    assert (
        run_repository.get_by_id("run-123").status
        == RunStatus.DEAD_LETTER
    )


def test_retrying_run_can_return_to_processing(run_repository):
    run_repository.create(
        create_run(status=RunStatus.RETRYING)
    )

    updated = run_repository.update_status(
        "run-123",
        RunStatus.PROCESSING,
    )

    assert updated is True
    assert (
        run_repository.get_by_id("run-123").status
        == RunStatus.PROCESSING
    )


@pytest.mark.parametrize(
    "initial_status,target_status",
    [
        (RunStatus.QUEUED, RunStatus.COMPLETED),
        (RunStatus.QUEUED, RunStatus.FAILED),
        (RunStatus.PROCESSING, RunStatus.RETRYING),
        (RunStatus.PROCESSING, RunStatus.DEAD_LETTER),
        (RunStatus.COMPLETED, RunStatus.PROCESSING),
        (RunStatus.COMPLETED, RunStatus.FAILED),
        (RunStatus.DEAD_LETTER, RunStatus.PROCESSING),
    ],
)
def test_invalid_status_transition_is_rejected(
    run_repository,
    initial_status,
    target_status,
):
    run_repository.create(
        create_run(status=initial_status)
    )

    with pytest.raises(
        ValueError,
        match="Invalid workflow run transition",
    ):
        run_repository.update_status(
            "run-123",
            target_status,
        )

    assert (
        run_repository.get_by_id("run-123").status
        == initial_status
    )


def test_update_status_for_missing_run(run_repository):
    updated = run_repository.update_status(
        "missing-run",
        RunStatus.PROCESSING,
    )

    assert updated is False


def test_update_retry_metadata(run_repository):
    run = WorkflowRun(
        run_id="run-123",
        workflow_id="workflow-123",
        workflow_version=1,
        event_id="event-123",
        status=RunStatus.FAILED,
        attempt=1,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    run_repository.create(run)

    result = run_repository.update_retry_metadata(
        run_id="run-123",
        attempt=2,
        last_error="Sentry API returned 503",
    )

    assert result is True

    updated_run = run_repository.collection.find_one(
        {"run_id": "run-123"}
    )

    assert updated_run["attempt"] == 2
    assert updated_run["last_error"] == "Sentry API returned 503"