from __future__ import annotations

from typing import Any

from app.ai.provider import FakeAIProvider
from app.execution.ai_analysis import AIAnalysisNode
from app.execution.builtins import builtin_handlers
from app.execution.registry import NodeRegistry
from app.execution.slack_notification import SlackNotificationNode
from app.integrations.registry import IntegrationRegistry
from app.workflow.tool_node import ToolNode


def create_async_registry(
    integration_registry: IntegrationRegistry | None = None,
) -> NodeRegistry:
    """Create a registry containing built-ins, tools, and action nodes."""
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

    ai_node = AIAnalysisNode(FakeAIProvider())

    async def execute_ai_analysis(
        context: Any,
        config: dict[str, Any],
        inputs: dict[str, Any],
    ) -> Any:
        return await ai_node.execute(context, config, inputs)

    registry.register("ai_analysis", execute_ai_analysis)

    slack_node = SlackNotificationNode(integrations)

    async def execute_slack(
        context: Any,
        config: dict[str, Any],
        inputs: dict[str, Any],
    ) -> Any:
        return await slack_node.execute(context, config, inputs)

    registry.register("slack", execute_slack)
    return registry
