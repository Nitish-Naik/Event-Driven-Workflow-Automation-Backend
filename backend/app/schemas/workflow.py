from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class WorkflowStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class WorkflowNode(BaseModel):
    id: str
    type: str
    config: dict = Field(default_factory=dict)


class WorkflowEdge(BaseModel):
    source: str
    target: str


class Workflow(BaseModel):
    workflow_id: str
    name: str
    version: int = Field(default=1, ge=1)
    status: WorkflowStatus = WorkflowStatus.DRAFT

    nodes: list[WorkflowNode] = Field(default_factory=list)
    edges: list[WorkflowEdge] = Field(default_factory=list)

    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def validate_graph(self):
        node_ids = [node.id for node in self.nodes]

        if len(node_ids) != len(set(node_ids)):
            raise ValueError("Node IDs must be unique")

        node_id_set = set(node_ids)

        for edge in self.edges:
            if edge.source not in node_id_set:
                raise ValueError(
                    f"Edge source '{edge.source}' does not exist"
                )

            if edge.target not in node_id_set:
                raise ValueError(
                    f"Edge target '{edge.target}' does not exist"
                )

        return self