from pymongo.errors import DuplicateKeyError

from app.db.repositories.workflow import WorkflowRepository
from app.schemas.workflow import Workflow
from app.services.exceptions import (
    ArchivedWorkflowError,
    WorkflowAlreadyExistsError,
    WorkflowNotFoundError,
)


class WorkflowService:
    def __init__(self, repository=None):
        self.repository = repository if repository is not None else WorkflowRepository()

    def create_workflow(self, workflow: Workflow) -> str:
        try:
            return self.repository.create(workflow)
        except DuplicateKeyError as exc:
            raise WorkflowAlreadyExistsError(
                f"Workflow version already exists: {workflow.workflow_id} v{workflow.version}"
            ) from exc

    def list_workflows(self) -> list[Workflow]:
        return self.repository.list_all()

    def get_workflow(self, workflow_id: str, version: int) -> Workflow | None:
        return self.repository.get_by_id(workflow_id, version)

    def get_active_workflow(self, workflow_id: str) -> Workflow | None:
        return self.repository.get_active(workflow_id)

    def get_active_workflow_by_trigger(self, trigger: str) -> Workflow | None:
        return self.repository.get_active_by_trigger(trigger)

    def update_workflow(self, workflow: Workflow) -> Workflow:
        existing = self.repository.get_by_id(workflow.workflow_id, workflow.version)
        if existing is None:
            raise WorkflowNotFoundError(f"Workflow not found: {workflow.workflow_id} v{workflow.version}")
        if existing.status == "archived":
            raise ArchivedWorkflowError(f"Archived workflow cannot be updated: {workflow.workflow_id} v{workflow.version}")
        self.repository.update(workflow)
        return workflow

    def activate_workflow(self, workflow_id: str, version: int) -> None:
        workflow = self.repository.get_by_id(workflow_id, version)
        if workflow is None:
            raise WorkflowNotFoundError(f"Workflow not found: {workflow_id} v{version}")
        if workflow.status == "archived":
            raise ArchivedWorkflowError(f"Archived workflow cannot be activated: {workflow_id} v{version}")
        if workflow.status == "active":
            return
        current_active = self.repository.get_active(workflow_id)
        if current_active is not None:
            self.repository.update_status(workflow_id, current_active.version, "archived")
        self.repository.update_status(workflow_id, version, "active")

    def deactivate_workflow(self, workflow_id: str, version: int) -> None:
        workflow = self.repository.get_by_id(workflow_id, version)
        if workflow is None:
            raise WorkflowNotFoundError(f"Workflow not found: {workflow_id} v{version}")
        if workflow.status != "active":
            raise ValueError(f"Workflow is not active: {workflow_id} v{version}")
        self.repository.update_status(workflow_id, version, "draft")
