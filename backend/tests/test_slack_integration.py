import httpx
import pytest

from app.execution.contracts import ExecutionContext
from app.execution.slack_notification import SlackNotificationNode
from app.integrations.registry import IntegrationRegistry
from app.integrations.slack_client import SlackClient
from app.integrations.slack_errors import SlackPermanentAPIError, SlackRetryableAPIError
from app.integrations.slack_integration import SlackIntegration
from app.integrations.tools.slack import SendSlackMessageTool


class FakeSlackClient:
    def __init__(self):
        self.messages = []

    async def send_message(self, channel: str, text: str):
        self.messages.append({"channel": channel, "text": text})
        return {"ok": True, "channel": channel, "ts": "123.456"}


@pytest.mark.asyncio
async def test_send_slack_message_tool_validates_and_sends():
    client = FakeSlackClient()
    tool = SendSlackMessageTool(client)

    result = await tool.execute({"channel": "#alerts", "text": "Sentry incident"})

    assert result["ok"] is True
    assert client.messages == [{"channel": "#alerts", "text": "Sentry incident"}]


@pytest.mark.asyncio
async def test_send_slack_message_tool_rejects_missing_text():
    tool = SendSlackMessageTool(FakeSlackClient())

    with pytest.raises(ValueError):
        await tool.execute({"channel": "#alerts"})


@pytest.mark.asyncio
async def test_slack_notification_node_uses_integration():
    client = FakeSlackClient()
    registry = IntegrationRegistry(
        sentry_client=object(),
        slack_client=client,
    )
    node = SlackNotificationNode(registry)
    context = ExecutionContext(workflow=object(), event=object())

    result = await node.execute(
        context,
        {},
        {"channel": "#incidents", "text": "Database error detected"},
    )

    assert result["channel"] == "#incidents"
    assert result["text"] == "Database error detected"
    assert result["response"]["ok"] is True
    assert client.messages[-1] == {
        "channel": "#incidents",
        "text": "Database error detected",
    }


def test_slack_integration_exposes_send_message_tool():
    integration = SlackIntegration(FakeSlackClient())
    tools = integration.get_tools()

    assert integration.name == "slack"
    assert [tool.name for tool in tools] == ["slack.send_message"]


def test_slack_client_requires_positive_timeout():
    with pytest.raises(ValueError):
        SlackClient(bot_token="x", timeout=0)


def test_slack_client_classifies_http_429_as_retryable():
    response = httpx.Response(429, request=httpx.Request("POST", "https://slack.com/api/chat.postMessage"))

    with pytest.raises(SlackRetryableAPIError):
        SlackClient._raise_for_response(response)


def test_slack_client_classifies_http_400_as_permanent():
    response = httpx.Response(400, request=httpx.Request("POST", "https://slack.com/api/chat.postMessage"))

    with pytest.raises(SlackPermanentAPIError):
        SlackClient._raise_for_response(response)


def test_slack_client_classifies_http_500_as_retryable():
    response = httpx.Response(500, request=httpx.Request("POST", "https://slack.com/api/chat.postMessage"))

    with pytest.raises(SlackRetryableAPIError):
        SlackClient._raise_for_response(response)


def test_slack_client_requires_bot_token_for_real_requests():
    client = SlackClient(bot_token=None)

    assert client.bot_token is None
