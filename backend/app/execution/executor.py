from typing import Any

from app.execution.contracts import ExecutionContext, ExecutionResult
from app.execution.graph import WorkflowGraph
from app.execution.inputs import InputResolutionError, resolve_input_value
from app.execution.registry import NodeRegistry
from app.execution.types import NodeHandler, WorkflowExecutionError


class WorkflowNodeExecutor:
    def __init__(
        self,
        handlers: dict[str, NodeHandler] | None = None,
        registry: NodeRegistry | None = None,
    ):
        if handlers is not None and registry is not None:
            raise ValueError("Provide either handlers or registry, not both")

        self.registry = registry or NodeRegistry(handlers)

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

            node_inputs = {}

            if isinstance(node.config, dict):
                configured_inputs = node.config.get("inputs", {})

                if isinstance(configured_inputs, dict):
                    try:
                        node_inputs = {
                            name: resolve_input_value(context, value)
                            for name, value in configured_inputs.items()
                        }
                    except InputResolutionError as exc:
                        raise WorkflowExecutionError(
                            f"Failed to resolve inputs for node '{node.id}': {exc}"
                        ) from exc

            try:
                result = self.registry.execute(
                    node.type,
                    context,
                    node.config,
                    node_inputs,
                )
            except WorkflowExecutionError:
                raise
            except Exception as exc:
                raise WorkflowExecutionError(
                    f"Node '{node.id}' ({node.type}) failed during execution"
                ) from exc

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


__all__ = ["NodeHandler", "WorkflowExecutionError", "WorkflowNodeExecutor"]
