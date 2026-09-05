from datetime import datetime, timezone
import pytest 

from app.schemas.workflow import Workflow
from app.services.exceptions import WorkflowAlreadyExistsError, ArchivedWorkflowError, WorkflowNotFoundError
from app.services.workflow import WorkflowService


def make_workflow(
    workflow_id="test-workflow",
    version=1,
    status="draft"
):
    now = datetime.now(timezone.utc)

    return Workflow(
        workflow_id=workflow_id,
        name="Test Workflow",
        version=version,
        status=status,
        nodes=[],
        edges=[],
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


class FakeWorkflowRepository:
    def __init__(self):
        self.workflows = {}

    def create(self, workflow):
        key = (workflow.workflow_id, workflow.version)

        if key in self.workflows:
            from pymongo.errors import DuplicateKeyError

            raise DuplicateKeyError("duplicate")

        self.workflows[key] = workflow
        return "fake-id"

    def get_by_id(self, workflow_id, version):
        return self.workflows.get((workflow_id, version))

    def get_active(self, workflow_id):
        for workflow in self.workflows.values():
            if (
                workflow.workflow_id == workflow_id
                and workflow.status == "active"
            ):
                return workflow

        return None

    def update_status(
        self,
        workflow_id,
        version,
        status,
    ):
        key = (workflow_id, version)

        if key not in self.workflows:
            return False

        workflow = self.workflows[key]

        self.workflows[key] = workflow.model_copy(
            update={"status": status}
        )

        return True

def test_create_workflow():
    repository = FakeWorkflowRepository()
    service = WorkflowService(repository)

    workflow = make_workflow()

    result = service.create_workflow(workflow)

    assert result == "fake-id"
    assert repository.workflows[
        ("test-workflow", 1)
    ] == workflow


def test_duplicate_workflow_raises_domain_error():
    repository = FakeWorkflowRepository()
    service = WorkflowService(repository)

    workflow = make_workflow()

    service.create_workflow(workflow)

    with pytest.raises(WorkflowAlreadyExistsError):
        service.create_workflow(workflow)


def test_get_workflow():
    repository = FakeWorkflowRepository()
    service = WorkflowService(repository)

    workflow = make_workflow()

    service.create_workflow(workflow)

    result = service.get_workflow(
        "test-workflow",
        1,
    )

    assert result == workflow

def test_activate_draft_workflow():
    repository = FakeWorkflowRepository()
    service = WorkflowService(repository=repository)

    workflow = make_workflow(
        workflow_id="wf-1",
        version=1,
        status="draft",
    )
    repository.create(workflow)

    service.activate_workflow("wf-1", 1)

    result = service.get_workflow("wf-1", 1)

    assert result.status == "active"

def test_activate_new_version_archives_previous_active():
    repository = FakeWorkflowRepository()
    service = WorkflowService(repository=repository)

    v1 = make_workflow(
        workflow_id="wf-1",
        version=1,
        status="active",
    )
    v2 = make_workflow(
        workflow_id="wf-1",
        version=2,
        status="draft",
    )

    repository.create(v1)
    repository.create(v2)

    service.activate_workflow("wf-1", 2)

    old_version = service.get_workflow("wf-1", 1)
    new_version = service.get_workflow("wf-1", 2)

    assert old_version.status == "archived"
    assert new_version.status == "active"


def test_archived_workflow_cannot_be_activated():
    repository = FakeWorkflowRepository()
    service = WorkflowService(repository=repository)

    workflow = make_workflow(
        workflow_id="wf-1",
        version=1,
        status="archived",
    )
    repository.create(workflow)

    with pytest.raises(ArchivedWorkflowError):
        service.activate_workflow("wf-1", 1)

def test_missing_workflow_cannot_be_activated():
    repository = FakeWorkflowRepository()
    service = WorkflowService(repository=repository)

    with pytest.raises(WorkflowNotFoundError):
        service.activate_workflow("wf-1", 1)