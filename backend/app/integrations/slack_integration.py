from app.integrations.slack_client import SlackClient
from app.integrations.tools.base import IntegrationTool
from app.integrations.tools.slack import SendSlackMessageTool


class SlackIntegration:
    @property
    def name(self) -> str:
        return "slack"

    @property
    def description(self) -> str:
        return "Slack messaging integration."

    def __init__(self, client: SlackClient) -> None:
        self.client = client

    def get_tools(self) -> list[IntegrationTool]:
        return [SendSlackMessageTool(self.client)]
