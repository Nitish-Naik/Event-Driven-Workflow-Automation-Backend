import httpx
import pytest

from app.config import settings
from app.integrations.sentry_client import SentryClient
from app.integrations.sentry_errors import (
    SentryPermanentAPIError,
    SentryRetryableAPIError,
)


class FakeResponse:
    def __init__(self, payload, status_code=200, headers=None):
        self.payload = payload
        self.status_code = status_code
        self.headers = httpx.Headers(headers or {})

    @property
    def is_success(self):
        return 200 <= self.status_code < 300

    def json(self):
        return self.payload


class FakeAsyncClient:
    def __init__(self, response=None, exception=None):
        self.response = response
        self.exception = exception
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def request(self, method, url, *, headers, params=None, json=None):
        self.calls.append((method, url, headers, params, json))
        if self.exception:
            raise self.exception
        return self.response


def patch_client(monkeypatch, fake_client):
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda *, timeout: fake_client,
    )


@pytest.mark.asyncio
async def test_list_projects_uses_bearer_auth_and_expected_endpoint(monkeypatch):
    response = FakeResponse([{"id": "project-1"}])
    fake_client = FakeAsyncClient(response)
    patch_client(monkeypatch, fake_client)

    client = SentryClient(
        base_url="https://sentry.test/",
        auth_token="secret-token",
        timeout=7.5,
    )

    result = await client.list_projects("my-org")

    assert result == [{"id": "project-1"}]
    assert fake_client.calls == [
        (
            "GET",
            "https://sentry.test/api/0/organizations/my-org/projects/",
            {
                "Accept": "application/json",
                "Authorization": "Bearer secret-token",
            },
            None,
            None,
        )
    ]


@pytest.mark.asyncio
async def test_list_issues_uses_expected_endpoint(monkeypatch):
    fake_client = FakeAsyncClient(FakeResponse([{"id": "issue-1"}]))
    patch_client(monkeypatch, fake_client)

    client = SentryClient(base_url="https://sentry.test", timeout=5.0)
    result = await client.list_issues("my-org")

    assert result == [{"id": "issue-1"}]
    assert fake_client.calls[0][0:2] == (
        "GET",
        "https://sentry.test/api/0/organizations/my-org/issues/",
    )


@pytest.mark.asyncio
async def test_client_omits_authorization_header_without_token(monkeypatch):
    fake_client = FakeAsyncClient(FakeResponse([]))
    patch_client(monkeypatch, fake_client)
    monkeypatch.setattr(settings, "sentry_auth_token", "")

    client = SentryClient(base_url="https://sentry.test", auth_token=None)
    await client.list_projects("my-org")

    assert fake_client.calls[0][2] == {"Accept": "application/json"}


@pytest.mark.asyncio
async def test_get_issue_uses_expected_endpoint(monkeypatch):
    fake_client = FakeAsyncClient(FakeResponse({"id": "123"}))
    patch_client(monkeypatch, fake_client)

    client = SentryClient(base_url="https://sentry.test", auth_token="token")
    result = await client.get_issue("123")

    assert result == {"id": "123"}
    assert fake_client.calls[0][1] == "https://sentry.test/api/0/issues/123/"


@pytest.mark.asyncio
async def test_resolve_issue_uses_put_and_payload(monkeypatch):
    fake_client = FakeAsyncClient(
        FakeResponse({"id": "123", "status": "resolved"})
    )
    patch_client(monkeypatch, fake_client)

    client = SentryClient(base_url="https://sentry.test", auth_token="token")
    result = await client.resolve_issue("123")

    assert result["status"] == "resolved"
    assert fake_client.calls[0][0] == "PUT"
    assert fake_client.calls[0][4] == {"status": "resolved"}


@pytest.mark.asyncio
async def test_401_is_permanent(monkeypatch):
    fake_client = FakeAsyncClient(FakeResponse({}, status_code=401))
    patch_client(monkeypatch, fake_client)

    with pytest.raises(SentryPermanentAPIError) as exc_info:
        await SentryClient(base_url="https://sentry.test").list_projects("org")

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [429, 500, 502, 503])
async def test_rate_limit_and_server_errors_are_retryable(monkeypatch, status_code):
    fake_client = FakeAsyncClient(
        FakeResponse(
            {},
            status_code=status_code,
            headers={"X-Sentry-Rate-Limit-Reset": "1234567890"},
        )
    )
    patch_client(monkeypatch, fake_client)

    with pytest.raises(SentryRetryableAPIError) as exc_info:
        await SentryClient(base_url="https://sentry.test").list_projects("org")

    assert exc_info.value.status_code == status_code


@pytest.mark.asyncio
async def test_timeout_is_retryable(monkeypatch):
    request = httpx.Request("GET", "https://sentry.test")
    fake_client = FakeAsyncClient(exception=httpx.ReadTimeout("timed out", request=request))
    patch_client(monkeypatch, fake_client)

    with pytest.raises(SentryRetryableAPIError):
        await SentryClient(base_url="https://sentry.test").list_projects("org")


@pytest.mark.asyncio
async def test_invalid_timeout_is_rejected():
    with pytest.raises(ValueError):
        SentryClient(base_url="https://sentry.test", timeout=0)
