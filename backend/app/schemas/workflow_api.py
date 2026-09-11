from typing import Any

from pydantic import BaseModel, Field

from app.schemas.workflow import Workflow, WorkflowEdge, WorkflowNode, WorkflowStatus


class CreateWorkflowResponse(BaseModel):
    workflow_id: str


class WorkflowListResponse(BaseModel):
    workflows: list[Workflow]


class UpdateWorkflowRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    trigger: str | None = Field(default=None, min_length=1)
    nodes: list[WorkflowNode] | None = None
    edges: list[WorkflowEdge] | None = None


class WorkflowTestRequest(BaseModel):
    event_type: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)


class WorkflowTestResponse(BaseModel):
    outputs: dict[str, Any]


class WorkflowStatusResponse(BaseModel):
    workflow_id: str
    version: int
    status: WorkflowStatus
