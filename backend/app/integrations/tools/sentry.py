from typing import Any

from app.integrations.sentry_client import SentryClient
from app.integrations.tools.base import IntegrationTool

class ListIssuesTool(IntegrationTool):
    def __init__(self, client: SentryClient) -> None:
        self.client = client

    @property
    def name(self) -> str:
        return "sentry.list_issues"

    @property
    def description(self) -> str:
        return "List issues from a Sentry organization."

    async def execute(self, inputs: dict[str, Any]) -> Any:
        organization = inputs["organization"]
        return await self.client.list_issues(organization)
    
class GetIssueTool(IntegrationTool):
    def __init__(self, client: SentryClient) -> None:
        self.client = client

    @property
    def name(self) -> str:
        return "sentry.get_issue"

    @property
    def description(self) -> str:
        return "Get details for a Sentry issue."

    async def execute(self, inputs: dict[str, Any]) -> Any:
        issue_id = inputs["issue_id"]
        return await self.client.get_issue(issue_id)