from app.integrations.sentry_client import SentryClient
from app.integrations.tools.base import IntegrationTool
from app.integrations.tools.sentry import (
    GetIssueEventsTool,
    GetIssueTool,
    ListIssuesTool,
    ResolveIssueTool,
)

class SentryIntegration:
    @property
    def name(self) -> str:
        return "sentry"

    @property
    def description(self) -> str:
        return "Sentry issue monitoring and management integration."

    def __init__(self, client: SentryClient) -> None:
        self.client = client

    def get_tools(self) -> list[IntegrationTool]:
        return [
            ListIssuesTool(self.client),
            GetIssueTool(self.client),
            GetIssueEventsTool(self.client),
            ResolveIssueTool(self.client),
        ]