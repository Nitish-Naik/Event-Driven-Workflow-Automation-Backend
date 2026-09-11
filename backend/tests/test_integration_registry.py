from app.integrations.registry import IntegrationRegistry
from app.integrations.sentry_client import SentryClient


def test_registry_returns_sentry_integration():
    registry = IntegrationRegistry()

    integration = registry.get("sentry")

    assert integration is not None
    assert integration.name == "sentry"


def test_registry_returns_none_for_unknown_integration():
    registry = IntegrationRegistry()

    assert registry.get("github") is None


def test_registry_lists_registered_integrations():
    registry = IntegrationRegistry()

    integrations = registry.list_integrations()

    names = {integration.name for integration in integrations}

    assert names == {"sentry", "slack"}

def test_registry_uses_injected_sentry_client():
    client = SentryClient()
    registry = IntegrationRegistry(sentry_client=client)

    integration = registry.get("sentry")

    assert integration is not None

    tools = integration.get_tools()

    assert all(tool.client is client for tool in tools)