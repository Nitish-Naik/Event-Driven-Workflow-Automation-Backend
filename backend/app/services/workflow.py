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
        self.repository = (
            repository
            if repository is not None
            else WorkflowRepository()
        )

    def create_workflow(self, workflow: Workflow) -> str:
        try:
            return self.repository.create(workflow)
        except DuplicateKeyError as exc:
            raise WorkflowAlreadyExistsError(
                f"Workflow version already exists: "
                f"{workflow.workflow_id} v{workflow.version}"
            ) from exc

    def get_workflow(
        self,
        workflow_id: str,
        version: int,
    ) -> Workflow | None:
        return self.repository.get_by_id(
            workflow_id,
            version,
        )

    def get_active_workflow(
        self,
        workflow_id: str,
    ) -> Workflow | None:
        return self.repository.get_active(workflow_id)

    def get_active_workflow_by_trigger(
        self,
        trigger: str,
    ) -> Workflow | None:
        return self.repository.get_active_by_trigger(trigger)

    def activate_workflow(
        self,
        workflow_id: str,
        version: int,
    ) -> None:
        workflow = self.repository.get_by_id(
            workflow_id,
            version,
        )

        if workflow is None:
            raise WorkflowNotFoundError(
                f"Workflow not found: {workflow_id} v{version}"
            )

        if workflow.status == "archived":
            raise ArchivedWorkflowError(
                f"Archived workflow cannot be activated: "
                f"{workflow_id} v{version}"
            )

        if workflow.status == "active":
            return

        current_active = self.repository.get_active(workflow_id)

        if current_active is not None:
            self.repository.update_status(
                workflow_id,
                current_active.version,
                "archived",
            )

        self.repository.update_status(
            workflow_id,
            version,
            "active",
        )
