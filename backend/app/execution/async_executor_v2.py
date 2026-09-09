from __future__ import annotations

from app.execution.contracts import ExecutionContext, ExecutionResult
from app.execution.registry import NodeRegistry


class AsyncWorkflowNodeExecutor:
    """Executes workflow nodes through the registry async execution path."""

    def __init__(self, registry: NodeRegistry) -> None:
        self.registry = registry

    async def execute(self, context: ExecutionContext) -> ExecutionResult:
        outputs = {}
        for node in context.workflow.nodes:
            result = await self.registry.execute_async(
                node.type, context, node.config, node.config.get("inputs", {})
            )
            context.values[node.id] = result
            outputs[node.id] = result
        return ExecutionResult(outputs=outputs)
