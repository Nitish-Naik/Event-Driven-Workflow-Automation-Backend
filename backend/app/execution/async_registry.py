from __future__ import annotations

from typing import Any

from app.execution.builtins import builtin_handlers
from app.execution.registry import NodeRegistry
from app.integrations.registry import IntegrationRegistry
from app.workflow.tool_node import ToolNode


def create_async_registry(
    integration_registry: IntegrationRegistry | None = None,
) -> NodeRegistry:
    """Create a registry containing built-ins and the integration tool node."""
    registry = NodeRegistry(builtin_handlers())
    integrations = integration_registry or IntegrationRegistry()
    tool_node = ToolNode(integrations)

    async def execute_tool(
        context: Any,
        config: dict[str, Any],
        inputs: dict[str, Any],
    ) -> Any:
        return await tool_node.execute(context, config, inputs)

    registry.register("tool", execute_tool)
    return registry
