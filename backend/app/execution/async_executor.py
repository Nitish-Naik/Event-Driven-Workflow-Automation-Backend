from __future__ import annotations

from typing import Any

from app.execution.contracts import ExecutionContext, ExecutionResult
from app.execution.graph import WorkflowGraph
from app.execution.inputs import InputResolutionError, resolve_input_value
from app.execution.registry import NodeRegistry
from app.execution.types import WorkflowExecutionError


class AsyncWorkflowNodeExecutor:
    """Executes workflow nodes while supporting sync and async handlers."""

    def __init__(self, registry: NodeRegistry) -> None:
        self.registry = registry

    async def execute(self, context: ExecutionContext) -> ExecutionResult:
        graph = WorkflowGraph(context.workflow)
        try:
            graph.validate_acyclic()
        except ValueError as exc:
            raise WorkflowExecutionError(str(exc)) from exc

        executed: set[str] = set()
        outputs: dict[str, Any] = {}

        async def visit(node_id: str) -> None:
            if node_id in executed:
                return

            node = graph.get_node(node_id)
            if node is None:
                raise WorkflowExecutionError(
                    f"Workflow node '{node_id}' does not exist"
                )

            node_inputs: dict[str, Any] = {}
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
                result = await self.registry.execute_async(
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
                await visit(child_id)

        for start_node in graph.get_start_nodes():
            await visit(start_node.id)

        return ExecutionResult(outputs=outputs)


__all__ = ["AsyncWorkflowNodeExecutor"]
