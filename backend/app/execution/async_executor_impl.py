from __future__ import annotations

from app.execution.contracts import ExecutionContext, ExecutionResult
from app.execution.registry import NodeRegistry


class AsyncWorkflowNodeExecutorImpl:
    """Temporary async execution adapter used to validate async node handlers."""

    def __init__(self, registry: NodeRegistry) -> None:
        self.registry = registry

    async def execute(self, context: ExecutionContext) -> ExecutionResult:
        outputs = {}
        for node in context.workflow.nodes:
            inputs = node.config.get("inputs", {})
            result = await self.registry.execute_async(
                node.type, context, node.config, inputs
            )
            context.values[node.id] = result
            outputs[node.id] = result
        return ExecutionResult(outputs=outputs)
