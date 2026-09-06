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
