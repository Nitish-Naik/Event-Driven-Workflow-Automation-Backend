from __future__ import annotations

from app.execution.contracts import ExecutionContext, ExecutionResult
from app.execution.registry import NodeRegistry


class AsyncWorkflowNodeExecutor:
    """Executes workflow nodes through the registry's async execution path."""

    def __init__(self, registry: NodeRegistry) -> None:
        self.registry = registry

    async def execute(self, context: ExecutionContext) -> ExecutionResult:
        return ExecutionResult(outputs={})
