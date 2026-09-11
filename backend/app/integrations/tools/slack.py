from typing import Any

from app.integrations.slack_client import SlackClient
from app.integrations.tools.base import IntegrationTool
from app.integrations.tools.validation import validate_tool_inputs
from app.integrations.tools.slack_schemas import SendSlackMessageInput


class SendSlackMessageTool(IntegrationTool):
    def __init__(self, client: SlackClient) -> None:
        self.client = client

    @property
    def name(self) -> str:
        return "slack.send_message"

    @property
    def description(self) -> str:
        return "Send a text message to a Slack channel."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "Slack channel ID or channel name the bot can access.",
                },
                "text": {
                    "type": "string",
                    "description": "Message text to send.",
                },
            },
            "required": ["channel", "text"],
        }

    async def execute(self, inputs: dict[str, Any]) -> Any:
        validated = validate_tool_inputs(SendSlackMessageInput, inputs)
        return await self.client.send_message(validated["channel"], validated["text"])
