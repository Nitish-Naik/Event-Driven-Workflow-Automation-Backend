import pytest

from app.integrations.tools.sentry import ListIssuesTool, GetIssueTool


class FakeSentryClient:
    async def list_issues(self, organization: str):
        return [
            {
                "id": "123",
                "title": "Database error",
                "organization": organization,
            }
        ]


@pytest.mark.asyncio
async def test_list_issues_tool():
    tool = ListIssuesTool(FakeSentryClient())

    assert tool.name == "sentry.list_issues"
    assert tool.description == "List issues from a Sentry organization."

    result = await tool.execute({"organization": "my-org"})

    assert result == [
        {
            "id": "123",
            "title": "Database error",
            "organization": "my-org",
        }
    ]

@pytest.mark.asyncio
async def test_list_issues_tool_delegates_to_client():
    class FakeSentryClient:
        def __init__(self):
            self.organization = None

        async def list_issues(self, organization: str):
            self.organization = organization
            return [{"id": "123"}]

    client = FakeSentryClient()
    tool = ListIssuesTool(client)


    result = await tool.execute({ "organization": "my-org"})

    assert client.organization == "my-org"
    assert result == [{"id": "123"}]

@pytest.mark.asyncio
async def test_get_issue_tool_delegates_to_client():
    class FakeSentryClient:
        def __init__(self):
            self.issue_id = None

        async def get_issue(self, issue_id: str):
            self.issue_id = issue_id
            return {
                "id": issue_id,
                "title": "Database error",
            }

    client = FakeSentryClient()
    tool = GetIssueTool(client)

    result = await tool.execute({"issue_id": "123"})

    assert client.issue_id == "123"
    assert result == {
        "id": "123",
        "title": "Database error",
    }