import json
from dataclasses import dataclass
from datetime import datetime, timezone

from app.db.redis import get_redis


@dataclass(frozen=True)
class QueuedEvent:
    event_id: str
    message_id: str


class EventQueue:
    QUEUE_NAME = "sentry:events"
    PROCESSING_QUEUE_NAME = "sentry:events:processing"

    def __init__(self, redis_client=None):
        self.redis = redis_client if redis_client is not None else get_redis()

    def enqueue(self, event_id: str) -> None:
        payload = json.dumps(
            {
                "event_id": event_id,
                "enqueued_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        self.redis.rpush(self.QUEUE_NAME, payload)

    def reserve(self) -> QueuedEvent | None:
        payload = self.redis.rpoplpush(
            self.QUEUE_NAME,
            self.PROCESSING_QUEUE_NAME,
        )
        if payload is None:
            return None

        try:
            message = json.loads(payload)
        except (TypeError, json.JSONDecodeError):
            self.redis.lrem(self.PROCESSING_QUEUE_NAME, 1, payload)
            return None

        if not isinstance(message, dict) or not message.get("event_id"):
            self.redis.lrem(self.PROCESSING_QUEUE_NAME, 1, payload)
            return None

        return QueuedEvent(
            event_id=message["event_id"],
            message_id=payload,
        )

    def acknowledge(self, message_id: str) -> bool:
        return self.redis.lrem(self.PROCESSING_QUEUE_NAME, 1, message_id) == 1

    def recover_all(self) -> int:
        recovered = 0
        while True:
            payload = self.redis.rpoplpush(
                self.PROCESSING_QUEUE_NAME,
                self.QUEUE_NAME,
            )
            if payload is None:
                return recovered
            recovered += 1
