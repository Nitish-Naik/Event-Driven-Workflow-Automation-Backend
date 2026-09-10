from __future__ import annotations

import hashlib
import hmac


SENTRY_SIGNATURE_HEADER = "x-servicehook-signature"


def verify_sentry_signature(
    secret: str,
    payload: bytes,
    signature: str | None,
) -> bool:
    """Verify Sentry's HMAC-SHA256 signature over the raw request body."""
    if not secret or not signature:
        return False

    expected = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)
