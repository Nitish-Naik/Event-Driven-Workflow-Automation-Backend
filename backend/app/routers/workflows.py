from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.workflow import Workflow
from app.services.workflow import WorkflowService

from app.services.exceptions import (
    ArchivedWorkflowError,
    WorkflowAlreadyExistsError,
    WorkflowNotFoundError,
)


router = APIRouter(
    prefix="/workflows",
    tags=["workflows"],
)

def get_workflow_service():
    return WorkflowService()

@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
)
def create_workflow(
    workflow: Workflow,
    service: WorkflowService = Depends(get_workflow_service),
):
    workflow_id = service.create_workflow(workflow)

    return {
        "workflow_id": workflow_id,
    }



@router.get(
    "/{workflow_id}/versions/{version}",
    response_model=Workflow,
)
def get_workflow(
    workflow_id: str,
    version: int, 
    service: WorkflowService = Depends(get_workflow_service),
):
    workflow = service.get_workflow(
        workflow_id,
        version,
    )

    if workflow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    return workflow

@router.get(
    "/{workflow_id}/active",
    response_model=Workflow,
)
def get_active_workflow(
    workflow_id: str,
    service: WorkflowService = Depends(get_workflow_service),
):
    workflow = service.get_active_workflow(workflow_id)

    if workflow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active workflow not found",
        )

    return workflow

@router.post(
    "/{workflow_id}/versions/{version}/activate",
    status_code=status.HTTP_204_NO_CONTENT,
)
def activate_workflow(
    workflow_id: str,
    version: int,
    service: WorkflowService = Depends(get_workflow_service),
):
    try:
        service.activate_workflow(
            workflow_id,
            version,
        )
    except WorkflowNotFoundError as exc: 
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    
    except ArchivedWorkflowError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_CONFLICT,
            detail=str(exc),
        ) from exc