from typing import Any

from app.integrations.sentry_client import SentryClient
from app.integrations.tools.base import IntegrationTool

from app.integrations.tools.schemas import GetIssueInput, GetIssueEventsInput, ResolveIssueInput
from app.integrations.tools.validation import validate_tool_inputs

class ListIssuesTool(IntegrationTool):
    def __init__(self, client: SentryClient) -> None:
        self.client = client

    @property
    def name(self) -> str:
        return "sentry.list_issues"

    @property
    def description(self) -> str:
        return "List issues from a Sentry organization."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "organization": {
                    "type": "string",
                    "description": "Sentry organization slug.",
                },
            },
            "required": ["organization"],
        }

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

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "issue_id": {
                    "type": "string",
                    "description": "Sentry issue ID.",
                },
            },
            "required": ["issue_id"],
        }

    async def execute(self, inputs: dict[str, Any]) -> Any:
        validated_inputs = validate_tool_inputs(GetIssueInput, inputs)
        return await self.client.get_issue(validated_inputs["issue_id"])

class GetIssueEventsTool(IntegrationTool):
    def __init__(self, client: SentryClient) -> None:
        self.client = client

    @property
    def name(self) -> str:
        return "sentry.get_issue_events"

    @property
    def description(self) -> str:
        return "Get events for a Sentry issue."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "issue_id": {
                    "type": "string",
                    "description": "Sentry issue ID.",
                },
            },
            "required": ["issue_id"],
        }

    async def execute(self, inputs: dict[str, Any]) -> Any:
        validated_inputs = validate_tool_inputs(GetIssueEventsInput, inputs)
        return await self.client.get_issue_events(validated_inputs["issue_id"])


class ResolveIssueTool(IntegrationTool):
    def __init__(self, client: SentryClient) -> None:
            self.client = client
    
    @property
    def name(self) -> str:
        return "sentry.resolve_issue"

    @property
    def description(self) -> str:
        return "Resolve a Sentry issue."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "issue_id": {
                    "type": "string",
                    "description": "Sentry issue ID.",
                },
            },
            "required": ["issue_id"],
        }
    
    async def execute(self, inputs: dict[str, Any]) -> Any:
        validated_inputs = validate_tool_inputs(ResolveIssueInput, inputs)
        return await self.client.resolve_issue(validated_inputs["issue_id"])