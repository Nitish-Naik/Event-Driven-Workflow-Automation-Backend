from __future__ import annotations

from typing import Any

from app.execution.contracts import ExecutionContext
from app.integrations.registry import IntegrationRegistry


class SlackNotificationNode:
    """Send a resolved message through the Slack integration."""

    def __init__(self, integration_registry: IntegrationRegistry) -> None:
        self.integration_registry = integration_registry

    async def execute(
        self,
        context: ExecutionContext,
        config: dict[str, Any],
        inputs: dict[str, Any],
    ) -> dict[str, Any]:
        channel = inputs.get("channel", config.get("channel"))
        text = inputs.get("text", config.get("text"))
        if not channel or not text:
            raise ValueError("Slack notification requires 'channel' and 'text'")

        integration = self.integration_registry.get("slack")
        if integration is None:
            raise ValueError("Slack integration is not configured")

        for tool in integration.get_tools():
            if tool.name == "slack.send_message":
                response = await tool.execute({"channel": channel, "text": text})
                return {"channel": channel, "text": text, "response": response}

        raise ValueError("Slack send_message tool is not configured")
