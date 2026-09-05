import json

from app.db.redis import get_redis


class EventQueue:
    QUEUE_NAME = "sentry:events"

    def __init__(self, redis_client=None):
        self.redis = redis_client if redis_client is not None else get_redis()

    def enqueue(self, event_id: str) -> None:
        self.redis.rpush(
            self.QUEUE_NAME,
            json.dumps({"event_id": event_id}),
        )