from __future__ import annotations

from typing import Any

from app.execution.contracts import ExecutionContext, ExecutionResult
from app.execution.graph import validate_acyclic
from app.execution.registry import NodeRegistry
from app.execution.types import InputResolutionError, WorkflowExecutionError


class AsyncWorkflowNodeExecutor:
    """Executes workflow nodes while supporting sync and async handlers."""

    def __init__(self, registry: NodeRegistry) -> None:
        self.registry = registry

    async def execute(self, context: ExecutionContext) -> ExecutionResult:
        workflow = context.workflow
        validate_acyclic(workflow.nodes, workflow.edges)

        nodes_by_id = {node.id: node for node in workflow.nodes}
        incoming = {node.id: 0 for node in workflow.nodes}
        for edge in workflow.edges:
            incoming[edge.target] += 1

        outputs: dict[str, Any] = {}
        visiting: set[str] = set()
        visited: set[str] = set()

        async def visit(node_id: str) -> None:
            if node_id in visited:
                return
            if node_id in visiting:
                raise WorkflowExecutionError(
                    f"Cycle detected while executing node '{node_id}'"
                )

            visiting.add(node_id)
            node = nodes_by_id[node_id]
            inputs = self._resolve_inputs(node.config.get("inputs", {}), context.values)

            try:
                result = await self.registry.execute_async(
                    node.type,
                    context,
                    node.config,
                    inputs,
                )
            except (WorkflowExecutionError, InputResolutionError):
                raise
            except Exception as exc:
                raise WorkflowExecutionError(
                    f"Node '{node_id}' ({node.type}) failed: {exc}"
                ) from exc

            context.values[node_id] = result
            outputs[node_id] = result
            visiting.remove(node_id)
            visited.add(node_id)

            for edge in workflow.edges:
                if edge.source == node_id:
                    await visit(edge.target)

        for node_id, count in incoming.items():
            if count == 0:
                await visit(node_id)

        return ExecutionResult(outputs=outputs)

    @staticmethod
    def _resolve_inputs(value: Any, values: dict[str, Any]) -> Any:
        if isinstance(value, str) and value.startswith("$"):
            ref = value[1:]
            if ref not in values:
                raise InputResolutionError(f"Unknown input reference '{ref}'")
            return values[ref]
        if isinstance(value, dict):
            return {
                key: AsyncWorkflowNodeExecutor._resolve_inputs(item, values)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [AsyncWorkflowNodeExecutor._resolve_inputs(item, values) for item in value]
        return value
