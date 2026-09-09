from collections.abc import Mapping
import inspect

from app.execution.contracts import ExecutionContext
from app.execution.types import NodeHandler, WorkflowExecutionError


class NodeRegistry:
    """Maps workflow node types to their execution handlers."""

    def __init__(self, handlers: Mapping[str, NodeHandler] | None = None):
        self._handlers: dict[str, NodeHandler] = dict(handlers or {})

    def register(self, node_type: str, handler: NodeHandler) -> None:
        if not node_type:
            raise ValueError("Node type must not be empty")
        self._handlers[node_type] = handler

    def get(self, node_type: str) -> NodeHandler:
        handler = self._handlers.get(node_type)
        if handler is None:
            raise WorkflowExecutionError(
                f"No handler registered for node type '{node_type}'"
            )
        return handler

    def handlers(self) -> dict[str, NodeHandler]:
        return dict(self._handlers)

    def execute(
        self,
        node_type: str,
        context: ExecutionContext,
        config: object,
        inputs: dict | None = None,
    ) -> dict:
        return self.get(node_type)(
            context,
            config,
            inputs or {},
        )

    async def execute_async(
        self,
        node_type: str,
        context: ExecutionContext,
        config: object,
        inputs: dict | None = None,
    ) -> dict:
        result = self.get(node_type)(
            context,
            config,
            inputs or {},
        )
        if inspect.isawaitable(result):
            result = await result
        return result
