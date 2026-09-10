from __future__ import annotations

from typing import Any

import httpx

from app.config import settings
from app.integrations.sentry_errors import (
    SentryPermanentAPIError,
    SentryRetryableAPIError,
)


class SentryClient:
    """Async HTTP client for the Sentry REST API."""

    def __init__(
        self,
        base_url: str | None = None,
        auth_token: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")

        self.base_url = (base_url or settings.sentry_base_url).rstrip("/")
        self.auth_token = auth_token or settings.sentry_auth_token
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    @staticmethod
    def _rate_limit_reset(headers: httpx.Headers) -> float | None:
        value = headers.get("X-Sentry-Rate-Limit-Reset")
        if value is None:
            return None
        try:
            return float(value)
        except ValueError:
            return None

    @classmethod
    def _raise_for_response(cls, response: httpx.Response) -> None:
        if response.is_success:
            return

        status = response.status_code
        reset_at = cls._rate_limit_reset(response.headers)
        retry_after = response.headers.get("Retry-After")

        if status == 429 or status >= 500:
            details = f"Sentry API returned HTTP {status}"
            if retry_after:
                details += f"; retry-after={retry_after}"
            elif reset_at is not None:
                details += f"; rate-limit-reset={reset_at}"
            raise SentryRetryableAPIError(details, status_code=status)

        raise SentryPermanentAPIError(
            f"Sentry API returned HTTP {status}",
            status_code=status,
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method,
                    url,
                    headers=self._headers(),
                    params=params,
                    json=json,
                )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise SentryRetryableAPIError(
                f"Sentry API request failed: {exc}"
            ) from exc

        self._raise_for_response(response)
        return response.json()

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return await self._request("GET", path, params=params)

    async def _put(
        self,
        path: str,
        json: dict[str, Any] | None = None,
    ) -> Any:
        return await self._request("PUT", path, json=json)

    async def list_projects(self, organization: str) -> Any:
        return await self._get(f"/api/0/organizations/{organization}/projects/")

    async def list_issues(self, organization: str) -> Any:
        return await self._get(f"/api/0/organizations/{organization}/issues/")

    async def get_issue(self, issue_id: str) -> Any:
        return await self._get(f"/api/0/issues/{issue_id}/")

    async def get_issue_events(self, issue_id: str) -> Any:
        return await self._get(f"/api/0/issues/{issue_id}/events/")

    async def resolve_issue(self, issue_id: str) -> Any:
        return await self._put(
            f"/api/0/issues/{issue_id}/",
            json={"status": "resolved"},
        )
