from app.integrations.sentry_client import SentryClient
from app.integrations.sentry_integration import SentryIntegration


class IntegrationRegistry:
    def __init__(self, sentry_client: SentryClient | None = None) -> None:
        client = sentry_client or SentryClient()

        self._integrations = {
            "sentry": SentryIntegration(client),
        }

    def get(self, name: str):
        return self._integrations.get(name)

    def list_integrations(self):
        return list(self._integrations.values())