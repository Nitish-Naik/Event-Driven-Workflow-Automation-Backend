import hashlib
import hmac

from app.security.sentry_webhook import verify_sentry_signature


def make_signature(secret: str, payload: bytes) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()


def test_valid_sentry_signature_is_accepted():
    secret = "webhook-secret"
    payload = b'{"event_id":"event-1"}'
    signature = make_signature(secret, payload)

    assert verify_sentry_signature(secret, payload, signature) is True


def test_invalid_sentry_signature_is_rejected():
    secret = "webhook-secret"
    payload = b'{"event_id":"event-1"}'

    assert verify_sentry_signature(secret, payload, "invalid") is False


def test_missing_sentry_signature_is_rejected():
    assert verify_sentry_signature(
        "webhook-secret",
        b'{"event_id":"event-1"}',
        None,
    ) is False


def test_signature_is_verified_against_exact_raw_body():
    secret = "webhook-secret"
    raw_payload = b'{"event_id":"event-1","message":"hello"}'
    formatted_payload = b'{"event_id": "event-1", "message": "hello"}'
    signature = make_signature(secret, raw_payload)

    assert verify_sentry_signature(secret, raw_payload, signature) is True
    assert verify_sentry_signature(secret, formatted_payload, signature) is False
