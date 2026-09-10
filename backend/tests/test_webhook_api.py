import hashlib
import hmac
import json

from app.config import settings


TEST_WEBHOOK_SECRET = "webhook-secret"


def make_signature(secret: str, payload: bytes) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()


def make_sentry_payload(event_id: str) -> dict:
    return {
        "project": {
            "id": "4512062696390656",
            "slug": "python-fastapi",
        },
        "group": {
            "id": "123",
            "shortId": "PYTHON-FASTAPI-1",
            "title": "Database connection failed",
        },
        "event": {
            "id": event_id,
            "eventID": event_id,
            "projectID": "4512062696390656",
        },
    }


def signed_request(api_client, payload: dict):
    raw_body = json.dumps(payload, separators=(",", ":")).encode()
    return api_client.post(
        "/webhooks/sentry",
        content=raw_body,
        headers={
            "content-type": "application/json",
            "x-servicehook-signature": make_signature(
                TEST_WEBHOOK_SECRET,
                raw_body,
            ),
        },
    )


def test_receive_sentry_event(api_client, monkeypatch):
    monkeypatch.setattr(settings, "sentry_webhook_secret", TEST_WEBHOOK_SECRET)
    payload = make_sentry_payload("sentry-event-1")
    response = signed_request(api_client, payload)
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "accepted"
    assert body["event_id"] == "sentry-event-1"


def test_duplicate_sentry_event_is_accepted(api_client, monkeypatch):
    monkeypatch.setattr(settings, "sentry_webhook_secret", TEST_WEBHOOK_SECRET)
    payload = make_sentry_payload("duplicate-event")
    first_response = signed_request(api_client, payload)
    second_response = signed_request(api_client, payload)
    assert first_response.status_code == 202
    assert second_response.status_code == 202
    assert second_response.json()["status"] == "duplicate"


def test_receive_sentry_event_queues_event(
    api_client,
    fake_event_queue,
    monkeypatch,
):
    monkeypatch.setattr(settings, "sentry_webhook_secret", TEST_WEBHOOK_SECRET)
    payload = make_sentry_payload("queued-event-1")
    response = signed_request(api_client, payload)
    assert response.status_code == 202
    assert response.json()["status"] == "accepted"
    assert fake_event_queue.events == ["queued-event-1"]


def test_duplicate_sentry_event_is_not_queued(
    api_client,
    fake_event_queue,
    monkeypatch,
):
    monkeypatch.setattr(settings, "sentry_webhook_secret", TEST_WEBHOOK_SECRET)
    payload = make_sentry_payload("duplicate-queue-event")
    first_response = signed_request(api_client, payload)
    second_response = signed_request(api_client, payload)
    assert first_response.status_code == 202
    assert second_response.status_code == 202
    assert fake_event_queue.events == ["duplicate-queue-event"]


def test_sentry_webhook_accepts_valid_signature(api_client, monkeypatch):
    secret = TEST_WEBHOOK_SECRET
    payload = make_sentry_payload("signed-event")
    raw_body = json.dumps(payload, separators=(",", ":")).encode()
    monkeypatch.setattr(settings, "sentry_webhook_secret", secret)
    response = api_client.post(
        "/webhooks/sentry",
        content=raw_body,
        headers={
            "content-type": "application/json",
            "x-servicehook-signature": make_signature(secret, raw_body),
        },
    )
    assert response.status_code == 202
    assert response.json()["status"] == "accepted"


def test_sentry_webhook_rejects_invalid_signature(api_client, monkeypatch):
    monkeypatch.setattr(settings, "sentry_webhook_secret", TEST_WEBHOOK_SECRET)
    response = api_client.post(
        "/webhooks/sentry",
        json={"event_id": "invalid-signature", "event_type": "issue.created"},
        headers={"x-servicehook-signature": "invalid"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid Sentry webhook signature"
