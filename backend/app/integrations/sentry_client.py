from __future__ import annotations

from typing import Any

import httpx

from app.config import settings


class SentryClient:
    """Small async HTTP client for the Sentry REST API."""

    def __init__(
        self,
        base_url: str | None = None,
        auth_token: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.base_url = (base_url or settings.sentry_base_url).rstrip("/")
        self.auth_token = auth_token or settings.sentry_auth_token
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, headers=self._headers(), params=params)
            response.raise_for_status()
            return response.json()

    async def list_projects(self, organization: str) -> Any:
        return await self._get(f"/api/0/organizations/{organization}/projects/")

    async def list_issues(self, organization: str) -> Any:
        return await self._get(f"/api/0/organizations/{organization}/issues/")
