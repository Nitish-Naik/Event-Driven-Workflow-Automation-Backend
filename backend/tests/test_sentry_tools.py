import pytest

from app.integrations.tools.sentry import ListIssuesTool, GetIssueTool, GetIssueEventsTool, ResolveIssueTool

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

@pytest.mark.asyncio
async def test_get_issue_events_tool_delegates_to_client():
    class FakeSentryClient:
        def __init__(self):
            self.issue_id = None

        async def get_issue_events(self, issue_id: str):
            self.issue_id = issue_id
            return [
                {"event_id": "event-1"},
                {"event_id": "event-2"},
            ]

    client = FakeSentryClient()
    tool = GetIssueEventsTool(client)

    result = await tool.execute({"issue_id": "123"})

    assert client.issue_id == "123"
    assert result == [
        {"event_id": "event-1"},
        {"event_id": "event-2"},
    ]

@pytest.mark.asyncio
async def test_resolve_issue_tool_delegates_to_client():
    class FakeSentryClient:
        def __init__(self):
            self.issue_id = None

        async def resolve_issue(self, issue_id: str):
            self.issue_id = issue_id
            return {
                "id": issue_id,
                "status": "resolved",
            }

    client = FakeSentryClient()
    tool = ResolveIssueTool(client)

    result = await tool.execute({"issue_id": "123"})

    assert client.issue_id == "123"
    assert result == {
        "id": "123",
        "status": "resolved",
    }

def test_list_issues_tool_input_schema():
    tool = ListIssuesTool(FakeSentryClient())

    assert tool.input_schema == {
        "type": "object",
        "properties": {
            "organization": {
                "type": "string",
                "description": "Sentry organization slug.",
            },
        },
        "required": ["organization"],
    }

def test_get_issue_tool_input_schema():
    tool = GetIssueTool(FakeSentryClient())

    assert tool.input_schema == {
        "type": "object",
        "properties": {
            "issue_id": {
                "type": "string",
                "description": "Sentry issue ID.",
            },
        },
        "required": ["issue_id"],
    }


def test_get_issue_events_tool_input_schema():
    tool = GetIssueEventsTool(FakeSentryClient())

    assert tool.input_schema == {
        "type": "object",
        "properties": {
            "issue_id": {
                "type": "string",
                "description": "Sentry issue ID.",
            },
        },
        "required": ["issue_id"],
    }


def test_resolve_issue_tool_input_schema():
    tool = ResolveIssueTool(FakeSentryClient())

    assert tool.input_schema == {
        "type": "object",
        "properties": {
            "issue_id": {
                "type": "string",
                "description": "Sentry issue ID.",
            },
        },
        "required": ["issue_id"],
    }

@pytest.mark.asyncio
async def test_get_issue_tool_rejects_missing_issue_id():
    from app.integrations.tools.validation import ToolInputValidationError

    tool = GetIssueTool(FakeSentryClient())

    with pytest.raises(ToolInputValidationError):
        await tool.execute({})

@pytest.mark.asyncio
async def test_get_issue_tool_rejects_none_issue_id():
    from app.integrations.tools.validation import ToolInputValidationError

    tool = GetIssueTool(FakeSentryClient())

    with pytest.raises(ToolInputValidationError):
        await tool.execute({"issue_id": None})

@pytest.mark.asyncio
async def test_get_issue_tool_does_not_call_client_when_input_is_invalid():
    from app.integrations.tools.validation import ToolInputValidationError

    class FakeSentryClient:
        def __init__(self):
            self.called = False

        async def get_issue(self, issue_id: str):
            self.called = True
            return {"id": issue_id}

    client = FakeSentryClient()
    tool = GetIssueTool(client)

    with pytest.raises(ToolInputValidationError):
        await tool.execute({})

    assert client.called is False



from app.integrations.tools.validation import ToolInputValidationError

@pytest.mark.asyncio
async def test_get_issue_events_tool_rejects_missing_issue_id():

    tool = GetIssueEventsTool(FakeSentryClient())

    with pytest.raises(ToolInputValidationError):
        await tool.execute({})

@pytest.mark.asyncio
async def test_get_issue_events_tool_rejects_none_issue_id():
    tool = GetIssueEventsTool(FakeSentryClient())

    with pytest.raises(ToolInputValidationError):
        await tool.execute({"issue_id": None})

@pytest.mark.asyncio
async def test_get_issue_events_tool_does_not_call_client_when_input_is_invalid():
    class FakeSentryClient:
        def __init__(self):
            self.called = False

        async def get_issue_events(self, issue_id: str):
            self.called = True
            return [{"event_id": "event-1"}]

    client = FakeSentryClient()
    tool = GetIssueEventsTool(client)

    with pytest.raises(ToolInputValidationError):
        await tool.execute({})

    assert client.called is False

@pytest.mark.asyncio
async def test_resolve_issue_tool_delegates_to_client():
    class FakeSentryClient:
        def __init__(self):
            self.issue_id = None

        async def resolve_issue(self, issue_id: str):
            self.issue_id = issue_id
            return {
                "id": issue_id,
                "status": "resolved",
            }

    client = FakeSentryClient()
    tool = ResolveIssueTool(client)

    result = await tool.execute({"issue_id": "123"})

    assert client.issue_id == "123"
    assert result == {
        "id": "123",
        "status": "resolved",
    }

@pytest.mark.asyncio
async def test_resolve_issue_tool_rejects_missing_issue_id():
    tool = ResolveIssueTool(FakeSentryClient())

    with pytest.raises(ToolInputValidationError):
        await tool.execute({})

@pytest.mark.asyncio
async def test_resolve_issue_tool_rejects_none_issue_id():
    tool = ResolveIssueTool(FakeSentryClient())

    with pytest.raises(ToolInputValidationError):
        await tool.execute({"issue_id": None})

@pytest.mark.asyncio
async def test_resolve_issue_tool_does_not_call_client_when_input_is_invalid():
    class FakeSentryClient:
        def __init__(self):
            self.called = False

        async def resolve_issue(self, issue_id: str):
            self.called = True
            return {
                "id": issue_id,
                "status": "resolved",
            }

    client = FakeSentryClient()
    tool = ResolveIssueTool(client)

    with pytest.raises(ToolInputValidationError):
        await tool.execute({})

    assert client.called is False



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

    result = await tool.execute({"organization": "my-org"})

    assert client.organization == "my-org"
    assert result == [{"id": "123"}]

@pytest.mark.asyncio
async def test_list_issues_tool_rejects_missing_organization():
    tool = ListIssuesTool(FakeSentryClient())

    with pytest.raises(ToolInputValidationError):
        await tool.execute({})

@pytest.mark.asyncio
async def test_list_issues_tool_rejects_none_organization():
    tool = ListIssuesTool(FakeSentryClient())

    with pytest.raises(ToolInputValidationError):
        await tool.execute({"organization": None})

@pytest.mark.asyncio
async def test_list_issues_tool_does_not_call_client_when_input_is_invalid():
    class FakeSentryClient:
        def __init__(self):
            self.called = False

        async def list_issues(self, organization: str):
            self.called = True
            return [{"id": "123"}]

    client = FakeSentryClient()
    tool = ListIssuesTool(client)

    with pytest.raises(ToolInputValidationError):
        await tool.execute({})

    assert client.called is False