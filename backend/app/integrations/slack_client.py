from __future__ import annotations

from typing import Any

import httpx

from app.config import settings
from app.integrations.slack_errors import (
    SlackPermanentAPIError,
    SlackRetryableAPIError,
)


class SlackClient:
    """Async HTTP client for the Slack Web API."""

    def __init__(
        self,
        base_url: str | None = None,
        bot_token: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")
        self.base_url = (base_url or settings.slack_base_url).rstrip("/")
        self.bot_token = bot_token or settings.slack_bot_token
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self.bot_token:
            headers["Authorization"] = f"Bearer {self.bot_token}"
        return headers

    @staticmethod
    def _raise_for_response(response: httpx.Response) -> None:
        if response.is_success:
            return
        status = response.status_code
        if status == 429 or status >= 500:
            raise SlackRetryableAPIError(
                f"Slack API returned HTTP {status}", status_code=status
            )
        raise SlackPermanentAPIError(
            f"Slack API returned HTTP {status}", status_code=status
        )

    async def send_message(self, channel: str, text: str) -> Any:
        if not self.bot_token:
            raise SlackPermanentAPIError("Slack bot token is not configured")
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat.postMessage",
                    headers=self._headers(),
                    json={"channel": channel, "text": text},
                )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise SlackRetryableAPIError(f"Slack API request failed: {exc}") from exc

        self._raise_for_response(response)
        payload = response.json()
        if payload.get("ok") is False:
            error = payload.get("error", "unknown_error")
            if error in {"ratelimited", "internal_error", "service_unavailable"}:
                raise SlackRetryableAPIError(f"Slack API error: {error}")
            raise SlackPermanentAPIError(f"Slack API error: {error}")
        return payload
