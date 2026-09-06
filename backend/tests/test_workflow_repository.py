from datetime import datetime, timezone
import pytest
from pymongo.errors import DuplicateKeyError

from app.schemas.workflow import Workflow


def make_workflow(
    workflow_id="test-workflow",
    version=1,
    status="draft",
    trigger="sentry",
):
    now = datetime.now(timezone.utc)

    return Workflow(
        workflow_id=workflow_id,
        name="Test Workflow",
        trigger=trigger,
        version=version,
        status=status,
        nodes=[
            {
                "id": "trigger",
                "type": "sentry_trigger",
            },
            {
                "id": "ai",
                "type": "ai_analysis",
            },
        ],
        edges=[
            {
                "source": "trigger",
                "target": "ai",
            }
        ],
        created_at=now,
        updated_at=now,
    )


def test_create_and_get_workflow(repository):
    workflow = make_workflow()

    repository.create(workflow)

    result = repository.get_by_id(
        "test-workflow",
        1,
    )

    assert result is not None
    assert result.workflow_id == "test-workflow"
    assert result.version == 1


def test_duplicate_workflow_version_is_rejected(repository):
    workflow = make_workflow(
        workflow_id="duplicate-test",
        version=1,
    )

    repository.create(workflow)

    with pytest.raises(DuplicateKeyError):
        repository.create(workflow)


def test_get_active_by_trigger_returns_matching_workflow(repository):
    workflow = make_workflow(
        workflow_id="sentry-workflow",
        status="active",
        trigger="sentry",
    )

    repository.create(workflow)

    result = repository.get_active_by_trigger("sentry")

    assert result is not None
    assert result.workflow_id == "sentry-workflow"
    assert result.trigger == "sentry"
    assert result.status == "active"


def test_get_active_by_trigger_ignores_draft_workflow(repository):
    workflow = make_workflow(
        workflow_id="draft-sentry-workflow",
        status="draft",
        trigger="sentry",
    )

    repository.create(workflow)

    result = repository.get_active_by_trigger("sentry")

    assert result is None


def test_get_active_by_trigger_ignores_archived_workflow(repository):
    workflow = make_workflow(
        workflow_id="archived-sentry-workflow",
        status="archived",
        trigger="sentry",
    )

    repository.create(workflow)

    result = repository.get_active_by_trigger("sentry")

    assert result is None


def test_get_active_by_trigger_returns_none_for_unknown_trigger(repository):
    workflow = make_workflow(
        workflow_id="sentry-workflow",
        status="active",
        trigger="sentry",
    )

    repository.create(workflow)

    result = repository.get_active_by_trigger("github")

    assert result is None
