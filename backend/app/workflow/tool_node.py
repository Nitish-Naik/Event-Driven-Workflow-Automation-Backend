from typing import Any

from app.integrations.registry import IntegrationRegistry



class ToolNode:
    def __init__(self, registry: IntegrationRegistry) -> None:
        self.registry = registry

    async def execute(
        self,
        context: Any,
        config: dict[str, Any],
        inputs: dict[str, Any],
    ) -> Any:
        integration_name = config["integration"]
        tool_name = config["tool"]

        integration = self.registry.get(integration_name)

        if integration is None:
            raise ValueError(
                f"Unknown integration: {integration_name}"
            )

        tools = integration.get_tools()

        for tool in tools:
            if tool.name == tool_name:
                return await tool.execute(inputs)

        raise ValueError(
            f"Unknown tool: {tool_name}"
        )