from collections.abc import Callable
from typing import Any

from app.execution.contracts import ExecutionContext, ExecutionResult
from app.execution.graph import WorkflowGraph


NodeHandler = Callable[[ExecutionContext, Any], dict[str, Any]]


class WorkflowExecutionError(Exception):
    """Raised when a workflow node cannot be executed."""


class WorkflowNodeExecutor:
    def __init__(self, handlers: dict[str, NodeHandler] | None = None):
        self.handlers = handlers or {}

    def execute(self, context: ExecutionContext) -> ExecutionResult:
        graph = WorkflowGraph(context.workflow)
        executed: set[str] = set()
        outputs: dict[str, Any] = {}

        def visit(node_id: str) -> None:
            if node_id in executed:
                return

            node = graph.get_node(node_id)
            if node is None:
                raise WorkflowExecutionError(
                    f"Workflow node '{node_id}' does not exist"
                )

            handler = self.handlers.get(node.type)
            if handler is None:
                raise WorkflowExecutionError(
                    f"No handler registered for node type '{node.type}'"
                )

            result = handler(context, node.config)
            if result is None:
                result = {}

            context.values[node.id] = result
            outputs[node.id] = result
            executed.add(node.id)

            for child_id in graph.get_children(node.id):
                visit(child_id)

        for start_node in graph.get_start_nodes():
            visit(start_node.id)

        return ExecutionResult(outputs=outputs)
