import pytest
from app.integrations.sentry import normalize_sentry_event

from app.integrations.sentry_client import SentryClient
from app.integrations.sentry_integration import SentryIntegration


def test_normalize_sentry_event():
    payload = {
        "project": {"slug": "python-fastapi"},
        "group": {
            "id": "7724399607",
            "shortId": "PYTHON-FASTAPI-2",
            "title": "RuntimeError: Sentry integration test",
        },
        "event": {
            "id": "1335834e97624c3f94a46aba40fe54c2",
            "eventID": "1335834e97624c3f94a46aba40fe54c2",
            "projectID": "4512062696390656",
        },
    }

    event = normalize_sentry_event(payload)

    assert event.event_id == "1335834e97624c3f94a46aba40fe54c2"
    assert event.source == "sentry"
    assert event.event_type == "event.created"
    assert event.payload == payload
    assert event.received_at is not None


def test_normalize_sentry_event_accepts_event_id_fallback():
    payload = {
        "event": {
            "id": "sentry-123",
        },
    }

    event = normalize_sentry_event(payload)

    assert event.event_id == "sentry-123"
    assert event.event_type == "event.created"


def test_normalize_sentry_event_requires_event_object():
    with pytest.raises(ValueError, match="missing event object"):
        normalize_sentry_event({})


def test_normalize_sentry_event_requires_event_id():
    payload = {"event": {}}

    with pytest.raises(ValueError, match="missing event ID"):
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