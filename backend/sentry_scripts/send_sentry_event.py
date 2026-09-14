import json
import uuid
from datetime import datetime, timezone

import httpx


DSN = (
    "https://8e5a14dee28c18bf35bbf0eddc572d4f"
    "@o4512062645862400.ingest.us.sentry.io/4512062696390656"
)

dsn_parts = DSN.split("://", 1)[1]
public_key, host_and_project = dsn_parts.split("@", 1)
host, project_id = host_and_project.rsplit("/", 1)

event_id = uuid.uuid4().hex
timestamp = datetime.now(timezone.utc)

event = {
    "event_id": event_id,
    "message": "VectorShift final demo Sentry event",
    "level": "error",
    "platform": "python",
    "environment": "development",
    "timestamp": timestamp.timestamp(),
    "exception": {
        "values": [
            {
                "type": "final",
                "value": "final"
            }
        ]
    },
    "tags": {
        "source": "vectorshift-test",
    },
}

event_json = json.dumps(event, separators=(",", ":"))
event_bytes = event_json.encode("utf-8")

envelope = "\n".join(
    [
        json.dumps(
            {
                "event_id": event_id,
                "sent_at": timestamp.isoformat(),
            },
            separators=(",", ":"),
        ),
        json.dumps(
            {
                "type": "event",
                "length": len(event_bytes),
            },
            separators=(",", ":"),
        ),
        event_json,
    ]
) + "\n"

endpoint = (
    f"https://{host}/api/{project_id}/envelope/"
    f"?sentry_version=7&sentry_key={public_key}"
)

response = httpx.post(
    endpoint,
    content=envelope.encode("utf-8"),
    headers={"Content-Type": "application/x-sentry-envelope"},
    timeout=15,
)

print("event_id:", event_id)
print("status:", response.status_code)
print("response:", response.text)