import pytest
from app.integrations.sentry import normalize_sentry_event

from app.integrations.sentry_client import SentryClient
from app.integrations.sentry_integration import SentryIntegration

def test_normalize_sentry_event():
    payload = {
        "event_id": "sentry-123",
        "event_type": "issue.created",
        "issue_id": "456",
        "message": "Database connection failed",
    }

    event = normalize_sentry_event(payload)

    assert event.event_id == "sentry-123"
    assert event.source == "sentry"
    assert event.event_type == "issue.created"
    assert event.payload == payload
    assert event.received_at is not None


def test_sentry_event_requires_event_id():
    payload = {
        "event_type": "issue.created",
    }

    with pytest.raises(KeyError):
        normalize_sentry_event(payload)

def test_sentry_integration_name():
    integration = SentryIntegration(SentryClient())

    assert integration.name == "sentry"

def test_sentry_integration_description():
    integration = SentryIntegration(SentryClient())

    assert integration.description == "Sentry issue monitoring and management integration."

def test_sentry_integration_returns_all_tools():
    integration = SentryIntegration(SentryClient())

    tools = integration.get_tools()

    assert len(tools) == 4

    assert [tool.name for tool in tools] == [
        "sentry.list_issues",
        "sentry.get_issue",
        "sentry.get_issue_events",
        "sentry.resolve_issue",
    ]

def test_sentry_integration_tools_share_same_client():
    client = SentryClient()
    integration = SentryIntegration(client)

    tools = integration.get_tools()

    assert all(tool.client is client for tool in tools)