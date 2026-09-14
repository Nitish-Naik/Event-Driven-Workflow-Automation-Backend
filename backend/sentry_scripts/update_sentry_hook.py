import httpx

from app.config import settings

HOOK_ID = settings.sentry_hook_id
NEW_URL = settings.sentry_webhook_url

endpoint = (
    f"{settings.sentry_base_url.rstrip('/')}"
    f"/api/0/projects/{settings.sentry_org_slug}/python-fastapi/hooks/{HOOK_ID}/"
)

response = httpx.put(
    endpoint,
    headers={"Authorization": f"Bearer {settings.sentry_auth_token}"},
    json={"url": NEW_URL, "events": ["event.created"]},
    timeout=15,
)

print("status:", response.status_code)
print("response:", response.text)
response.raise_for_status()
