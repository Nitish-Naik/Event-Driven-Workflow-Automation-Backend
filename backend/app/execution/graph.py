from collections import defaultdict

from app.schemas.workflow import Workflow


class WorkflowGraph:
    def __init__(self, workflow: Workflow):
        self.workflow = workflow
        self.nodes = {node.id: node for node in workflow.nodes}
        self.children: dict[str, list[str]] = defaultdict(list)

        for edge in workflow.edges:
            self.children[edge.source].append(edge.target)

        for node_id in self.children:
            self.children[node_id].sort()

    def get_node(self, node_id: str):
        return self.nodes.get(node_id)

    def get_children(self, node_id: str):
        return list(self.children.get(node_id, []))

    def get_start_nodes(self):
        targets = {edge.target for edge in self.workflow.edges}
        return sorted(
            (node for node in self.workflow.nodes if node.id not in targets),
            key=lambda node: node.id,
        )

    def validate_acyclic(self) -> None:
        """Raise ValueError if any workflow component contains a cycle."""
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node_id: str) -> None:
            if node_id in visiting:
                raise ValueError(f"Workflow contains a cycle involving node '{node_id}'")
            if node_id in visited:
                return

            visiting.add(node_id)
            for child_id in self.get_children(node_id):
                visit(child_id)
            visiting.remove(node_id)
            visited.add(node_id)

        for node_id in sorted(self.nodes):
            visit(node_id)
