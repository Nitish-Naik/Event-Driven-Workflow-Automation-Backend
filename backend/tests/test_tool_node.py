import pytest

from app.integrations.registry import IntegrationRegistry
from app.integrations.sentry_client import SentryClient
from app.workflow.tool_node import ToolNode


@pytest.mark.asyncio
async def test_tool_node_executes_registered_tool():
    class FakeSentryClient:
        async def get_issue(self, issue_id: str):
            return {
                "id": issue_id,
                "title": "Database error",
            }

    registry = IntegrationRegistry(
        sentry_client=FakeSentryClient()
    )

    tool_node = ToolNode(registry)

    result = await tool_node.execute(
        context=None,
        config={
            "integration": "sentry",
            "tool": "sentry.get_issue",
        },
        inputs={
            "issue_id": "123",
        },
    )

    assert result == {
        "id": "123",
        "title": "Database error",
    }


@pytest.mark.asyncio
async def test_tool_node_rejects_unknown_integration():
    registry = IntegrationRegistry()
    tool_node = ToolNode(registry)

    with pytest.raises(ValueError, match="Unknown integration: github"):
        await tool_node.execute(
            context=None,
            config={
                "integration": "github",
                "tool": "github.get_issue",
            },
            inputs={},
        )

@pytest.mark.asyncio
async def test_tool_node_rejects_unknown_tool():
    registry = IntegrationRegistry()
    tool_node = ToolNode(registry)

    with pytest.raises(ValueError, match="Unknown tool: sentry.unknown"):
        await tool_node.execute(
            context=None,
            config={
                "integration": "sentry",
                "tool": "sentry.unknown",
            },
            inputs={},
        )

@pytest.mark.asyncio
async def test_tool_node_passes_inputs_to_tool():
    class FakeSentryClient:
        def __init__(self):
            self.issue_id = None

        async def get_issue(self, issue_id: str):
            self.issue_id = issue_id
            return {"id": issue_id}

    client = FakeSentryClient()
    registry = IntegrationRegistry(sentry_client=client)
    tool_node = ToolNode(registry)

    result = await tool_node.execute(
        context=None,
        config={
            "integration": "sentry",
            "tool": "sentry.get_issue",
        },
        inputs={
            "issue_id": "456",
        },
    )

    assert client.issue_id == "456"
    assert result == {"id": "456"}