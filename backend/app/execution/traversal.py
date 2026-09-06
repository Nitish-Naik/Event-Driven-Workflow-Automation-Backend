from app.execution.graph import WorkflowGraph


class WorkflowTraversal:
    """Produce a deterministic execution order for a workflow graph."""

    def traverse(self, graph: WorkflowGraph) -> list[str]:
        visited: set[str] = set()
        order: list[str] = []

        def visit(node_id: str) -> None:
            if node_id in visited:
                return

            visited.add(node_id)
            order.append(node_id)

            for child_id in sorted(graph.get_children(node_id)):
                visit(child_id)

        for node in sorted(graph.get_start_nodes(), key=lambda item: item.id):
            visit(node.id)

        return order
