import json

from app.queue.event_queue import EventQueue


class FakeRedis:
    def __init__(self):
        self.items = []

    def rpush(self, queue_name, value):
        self.items.append((queue_name, value))


def test_enqueue_event():
    redis = FakeRedis()
    queue = EventQueue(redis_client=redis)

    queue.enqueue("event-123")

    assert len(redis.items) == 1

    queue_name, value = redis.items[0]

    assert queue_name == "sentry:events"
    assert json.loads(value) == {
        "event_id": "event-123",
    }