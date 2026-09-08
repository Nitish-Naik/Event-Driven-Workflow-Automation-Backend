import httpx
import pytest

from app.integrations.sentry_client import SentryClient


class FakeAsyncClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, *, headers, params=None):
        self.calls.append((url, headers, params))
        return self.response


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code
        self.raise_for_status_called = False

    def raise_for_status(self):
        self.raise_for_status_called = True
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "request failed",
                request=httpx.Request("GET", "https://sentry.test"),
                response=httpx.Response(self.status_code),
            )

    def json(self):
        return self.payload


@pytest.mark.asyncio
async def test_list_projects_uses_bearer_auth_and_expected_endpoint(monkeypatch):
    response = FakeResponse([{"id": "project-1"}])
    client_instance = FakeAsyncClient(response)

    def fake_async_client(*, timeout):
        assert timeout == 7.5
        return client_instance

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)

    client = SentryClient(
        base_url="https://sentry.test/",
        auth_token="secret-token",
        timeout=7.5,
    )

    result = await client.list_projects("my-org")

    assert result == [{"id": "project-1"}]
    assert response.raise_for_status_called is True
    assert client_instance.calls == [
        (
            "https://sentry.test/api/0/organizations/my-org/projects/",
            {
                "Accept": "application/json",
                "Authorization": "Bearer secret-token",
            },
            None,
        )
    ]


@pytest.mark.asyncio
async def test_list_issues_uses_expected_endpoint_and_returns_json(monkeypatch):
    response = FakeResponse([{"id": "issue-1", "title": "Something broke"}])
    client_instance = FakeAsyncClient(response)

    def fake_async_client(*, timeout):
        assert timeout == 5.0
        return client_instance

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)

    client = SentryClient(
        base_url="https://sentry.test/",
        auth_token="secret-token",
        timeout=5.0,
    )

    result = await client.list_issues("my-org")

    assert result == [{"id": "issue-1", "title": "Something broke"}]
    assert response.raise_for_status_called is True
    assert client_instance.calls == [
        (
            "https://sentry.test/api/0/organizations/my-org/issues/",
            {
                "Accept": "application/json",
                "Authorization": "Bearer secret-token",
            },
            None,
        )
    ]


@pytest.mark.asyncio
async def test_client_omits_authorization_header_without_token(monkeypatch):
    response = FakeResponse([])
    client_instance = FakeAsyncClient(response)

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda *, timeout: client_instance,
    )

    client = SentryClient(base_url="https://sentry.test", auth_token=None)

    await client.list_projects("my-org")

    assert client_instance.calls[0][1] == {"Accept": "application/json"}


@pytest.mark.asyncio
async def test_client_propagates_http_errors(monkeypatch):
    response = FakeResponse({}, status_code=401)
    client_instance = FakeAsyncClient(response)

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda *, timeout: client_instance,
    )

    client = SentryClient(base_url="https://sentry.test", auth_token="bad-token")

    with pytest.raises(httpx.HTTPStatusError):
        await client.list_projects("my-org")

    assert response.raise_for_status_called is True

@pytest.mark.asyncio
async def test_get_issue_uses_expected_endpoint(monkeypatch):
    response = FakeResponse({"id": "123", "title": "Database error"})
    client_instance = FakeAsyncClient(response)

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda *, timeout: client_instance,
    )

    client = SentryClient(
        base_url="https://sentry.test",
        auth_token="secret-token",
    )

    result = await client.get_issue("123")

    assert result == {
        "id": "123",
        "title": "Database error",
    }

    assert client_instance.calls == [
        (
            "https://sentry.test/api/0/issues/123/",
            {
                "Accept": "application/json",
                "Authorization": "Bearer secret-token",
            },
            None,
        )
    ]