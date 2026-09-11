from __future__ import annotations

from app.integrations.slack_client import SlackClient
from app.integrations.slack_integration import SlackIntegration
from app.integrations.sentry_client import SentryClient
from app.integrations.sentry_integration import SentryIntegration


class IntegrationRegistry:
    def __init__(
        self,
        sentry_client: SentryClient | None = None,
        slack_client: SlackClient | None = None,
    ) -> None:
        self._integrations = {
            "sentry": SentryIntegration(sentry_client or SentryClient()),
            "slack": SlackIntegration(slack_client or SlackClient()),
        }

    def get(self, name: str):
        return self._integrations.get(name)

    def list_integrations(self):
        return list(self._integrations.values())
