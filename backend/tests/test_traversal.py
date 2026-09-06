from datetime import datetime, timezone

from app.execution.graph import WorkflowGraph
from app.execution.traversal import WorkflowTraversal
from app.schemas.workflow import Workflow, WorkflowEdge, WorkflowNode


def make_workflow(nodes: list[str], edges: list[tuple[str, str]]) -> Workflow:
    now = datetime.now(timezone.utc)
    return Workflow(
        workflow_id="workflow-1",
        name="Test Workflow",
        trigger="sentry.issue",
        nodes=[WorkflowNode(id=node_id, type=node_id) for node_id in nodes],
        edges=[WorkflowEdge(source=source, target=target) for source, target in edges],
        created_at=now,
        updated_at=now,
    )


def test_traverse_linear_workflow():
    workflow = make_workflow(
        ["a", "b", "c"],
        [("a", "b"), ("b", "c")],
    )

    assert WorkflowTraversal().traverse(WorkflowGraph(workflow)) == ["a", "b", "c"]


def test_traverse_branching_workflow_is_deterministic():
    workflow = make_workflow(
        ["a", "b", "c", "d"],
        [("a", "c"), ("a", "b"), ("b", "d")],
    )

    assert WorkflowTraversal().traverse(WorkflowGraph(workflow)) == [
        "a",
        "b",
        "d",
        "c",
    ]


def test_traverse_does_not_execute_shared_node_twice():
    workflow = make_workflow(
        ["a", "b", "c", "d"],
        [("a", "b"), ("a", "c"), ("b", "d"), ("c", "d")],
    )

    order = WorkflowTraversal().traverse(WorkflowGraph(workflow))

    assert order == ["a", "b", "d", "c"]
    assert order.count("d") == 1


def test_traverse_multiple_start_nodes_is_deterministic():
    workflow = make_workflow(
        ["a", "b", "c", "d"],
        [("a", "b"), ("c", "d")],
    )

    assert WorkflowTraversal().traverse(WorkflowGraph(workflow)) == [
        "a",
        "b",
        "c",
        "d",
    ]
