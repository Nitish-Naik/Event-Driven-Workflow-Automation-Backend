import hashlib
import hmac
import json

from app.config import settings


def make_signature(secret: str, payload: bytes) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()


def test_receive_sentry_event(api_client):
    payload = {
        "event_id": "sentry-event-1",
        "event_type": "issue.created",
        "issue_id": "123",
        "message": "Database connection failed",
    }

    response = api_client.post(
        "/webhooks/sentry",
        json=payload,
    )

    assert response.status_code == 202

    body = response.json()

    assert body["status"] == "accepted"
    assert body["event_id"]


def test_duplicate_sentry_event_is_accepted(
    api_client,
):
    payload = {
        "event_id": "duplicate-event",
        "event_type": "issue.created",
        "issue_id": "123",
    }

    first_response = api_client.post(
        "/webhooks/sentry",
        json=payload,
    )

    second_response = api_client.post(
        "/webhooks/sentry",
        json=payload,
    )

    assert first_response.status_code == 202
    assert second_response.status_code == 202

    assert second_response.json()["status"] == "duplicate"


def test_receive_sentry_event_queues_event(api_client, fake_event_queue):
    payload = {
        "event_id": "queued-event-1",
        "event_type": "issue.created",
        "issue_id": "123",
    }

    response = api_client.post("/webhooks/sentry", json=payload)

    assert response.status_code == 202
    assert response.json()["status"] == "accepted"

    assert fake_event_queue.events == ["queued-event-1"]


def test_duplicate_sentry_event_is_not_queued(
    api_client,
    fake_event_queue,
):
    payload = {
        "event_id": "duplicate-queue-event",
        "event_type": "issue.created",
    }

    first_response = api_client.post("/webhooks/sentry", json=payload)
    second_response = api_client.post("/webhooks/sentry", json=payload)

    assert first_response.status_code == 202
    assert second_response.status_code == 202

    assert fake_event_queue.events == [
        "duplicate-queue-event"
    ]


def test_sentry_webhook_accepts_valid_signature(api_client, monkeypatch):
    secret = "webhook-secret"
    payload = {"event_id": "signed-event", "event_type": "issue.created"}
    raw_body = json.dumps(payload, separators=(",", ":")).encode()

    monkeypatch.setattr(settings, "sentry_webhook_secret", secret)

    response = api_client.post(
        "/webhooks/sentry",
        content=raw_body,
        headers={
            "content-type": "application/json",
            "sentry-hook-signature": make_signature(secret, raw_body),
        },
    )

    assert response.status_code == 202
    assert response.json()["status"] == "accepted"


def test_sentry_webhook_rejects_invalid_signature(api_client, monkeypatch):
    monkeypatch.setattr(settings, "sentry_webhook_secret", "webhook-secret")

    response = api_client.post(
        "/webhooks/sentry",
        json={"event_id": "invalid-signature", "event_type": "issue.created"},
        headers={"sentry-hook-signature": "invalid"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid Sentry webhook signature"
