from datetime import datetime, timezone

import pytest

from app.execution.graph import WorkflowGraph
from app.schemas.workflow import Workflow, WorkflowEdge, WorkflowNode


def make_workflow(nodes, edges):
    now = datetime.now(timezone.utc)
    return Workflow(
        workflow_id="wf-1",
        name="test",
        trigger="sentry.issue",
        nodes=nodes,
        edges=edges,
        created_at=now,
        updated_at=now,
    )


def test_validate_acyclic_accepts_dag():
    workflow = make_workflow(
        [
            WorkflowNode(id="a", type="source"),
            WorkflowNode(id="b", type="transform"),
            WorkflowNode(id="c", type="sink"),
        ],
        [
            WorkflowEdge(source="a", target="b"),
            WorkflowEdge(source="b", target="c"),
        ],
    )

    WorkflowGraph(workflow).validate_acyclic()


def test_validate_acyclic_rejects_connected_cycle():
    workflow = make_workflow(
        [
            WorkflowNode(id="a", type="node"),
            WorkflowNode(id="b", type="node"),
            WorkflowNode(id="c", type="node"),
        ],
        [
            WorkflowEdge(source="a", target="b"),
            WorkflowEdge(source="b", target="c"),
            WorkflowEdge(source="c", target="a"),
        ],
    )

    with pytest.raises(ValueError, match="Workflow contains a cycle"):
        WorkflowGraph(workflow).validate_acyclic()


def test_validate_acyclic_rejects_disconnected_cycle():
    workflow = make_workflow(
        [
            WorkflowNode(id="a", type="node"),
            WorkflowNode(id="b", type="node"),
            WorkflowNode(id="c", type="node"),
            WorkflowNode(id="d", type="node"),
        ],
        [
            WorkflowEdge(source="a", target="b"),
            WorkflowEdge(source="c", target="d"),
            WorkflowEdge(source="d", target="c"),
        ],
    )

    with pytest.raises(ValueError, match="Workflow contains a cycle"):
        WorkflowGraph(workflow).validate_acyclic()
