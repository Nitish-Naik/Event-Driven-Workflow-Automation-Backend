from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app.execution.async_executor import AsyncWorkflowNodeExecutor
from app.execution.async_registry import create_async_registry
from app.execution.contracts import ExecutionContext
from app.schemas.event import Event
from app.schemas.workflow import Workflow, WorkflowStatus
from app.schemas.workflow_api import CreateWorkflowResponse, UpdateWorkflowRequest, WorkflowListResponse, WorkflowStatusResponse, WorkflowTestRequest, WorkflowTestResponse
from app.services.exceptions import ArchivedWorkflowError, WorkflowAlreadyExistsError, WorkflowNotFoundError
from app.services.workflow import WorkflowService

router = APIRouter(prefix="/workflows", tags=["workflows"])


def get_workflow_service():
    return WorkflowService()


@router.get("", response_model=WorkflowListResponse)
def list_workflows(service: WorkflowService = Depends(get_workflow_service)):
    return WorkflowListResponse(workflows=service.list_workflows())


@router.post("", response_model=CreateWorkflowResponse, status_code=status.HTTP_201_CREATED)
def create_workflow(workflow: Workflow, service: WorkflowService = Depends(get_workflow_service)):
    try:
        workflow_id = service.create_workflow(workflow)
    except WorkflowAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return CreateWorkflowResponse(workflow_id=workflow_id)


@router.get("/{workflow_id}/versions/{version}", response_model=Workflow)
def get_workflow(workflow_id: str, version: int, service: WorkflowService = Depends(get_workflow_service)):
    workflow = service.get_workflow(workflow_id, version)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


@router.get("/{workflow_id}/active", response_model=Workflow)
def get_active_workflow(workflow_id: str, service: WorkflowService = Depends(get_workflow_service)):
    workflow = service.get_active_workflow(workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Active workflow not found")
    return workflow


@router.put("/{workflow_id}/versions/{version}", response_model=Workflow)
def update_workflow(workflow_id: str, version: int, request: UpdateWorkflowRequest, service: WorkflowService = Depends(get_workflow_service)):
    existing = service.get_workflow(workflow_id, version)
    if existing is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    values = request.model_dump(exclude_unset=True)
    updated = existing.model_copy(update={**values, "updated_at": datetime.now(timezone.utc)})
    try:
        updated = Workflow(**updated.model_dump())
        return service.update_workflow(updated)
    except ArchivedWorkflowError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{workflow_id}/versions/{version}/activate", response_model=WorkflowStatusResponse)
def activate_workflow(workflow_id: str, version: int, service: WorkflowService = Depends(get_workflow_service)):
    try:
        service.activate_workflow(workflow_id, version)
    except WorkflowNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ArchivedWorkflowError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return WorkflowStatusResponse(workflow_id=workflow_id, version=version, status=WorkflowStatus.ACTIVE)


@router.post("/{workflow_id}/versions/{version}/deactivate", response_model=WorkflowStatusResponse)
def deactivate_workflow(workflow_id: str, version: int, service: WorkflowService = Depends(get_workflow_service)):
    try:
        service.deactivate_workflow(workflow_id, version)
    except WorkflowNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return WorkflowStatusResponse(workflow_id=workflow_id, version=version, status=WorkflowStatus.DRAFT)


@router.post("/{workflow_id}/versions/{version}/test", response_model=WorkflowTestResponse)
async def test_workflow(workflow_id: str, version: int, request: WorkflowTestRequest, service: WorkflowService = Depends(get_workflow_service)):
    workflow = service.get_workflow(workflow_id, version)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    event = Event(event_id=f"test-{uuid4()}", source=workflow.trigger, event_type=request.event_type, payload=request.payload, received_at=datetime.now(timezone.utc))
    executor = AsyncWorkflowNodeExecutor(create_async_registry())
    result = await executor.execute(ExecutionContext(workflow=workflow, event=event))
    return WorkflowTestResponse(outputs=result.outputs)
