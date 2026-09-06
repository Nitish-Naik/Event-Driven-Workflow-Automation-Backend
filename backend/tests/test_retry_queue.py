import json

from app.queue.retry_queue import RetryQueue


class FakeRedis:
    def __init__(self):
        self.items = {}

    def zadd(self, queue_name, mapping):
        if queue_name not in self.items:
            self.items[queue_name] = {}

        self.items[queue_name].update(mapping)

    def zrangebyscore(
        self,
        queue_name,
        minimum,
        maximum,
        start=0,
        num=None,
    ):
        if queue_name not in self.items:
            return []

        matching_items = [
            (message, score)
            for message, score in self.items[queue_name].items()
            if minimum <= score <= maximum
        ]

        matching_items.sort(key=lambda item: item[1])

        messages = [message for message, _ in matching_items]

        if num is None:
            return messages[start:]

        return messages[start:start + num]

    def zrem(self, queue_name, message):
        if queue_name not in self.items:
            return 0

        if message not in self.items[queue_name]:
            return 0

        del self.items[queue_name][message]
        return 1


def test_schedule_adds_retry_message_to_queue(monkeypatch):
    monkeypatch.setattr(
        "app.queue.retry_queue.time.time",
        lambda: 1000.0,
    )

    redis = FakeRedis()
    queue = RetryQueue(redis)

    queue.schedule(
        event_id="event-123",
        run_id="run-456",
        attempt=2,
        delay=4.5,
    )

    assert RetryQueue.QUEUE_NAME in redis.items

    mapping = redis.items[RetryQueue.QUEUE_NAME]

    assert len(mapping) == 1

    raw_message, execute_at = next(iter(mapping.items()))

    message = json.loads(raw_message)

    assert message == {
        "event_id": "event-123",
        "run_id": "run-456",
        "attempt": 2,
    }

    assert execute_at == 1004.5


def test_pop_due_returns_none_when_retry_is_not_due(monkeypatch):
    monkeypatch.setattr(
        "app.queue.retry_queue.time.time",
        lambda: 1000.0,
    )

    redis = FakeRedis()
    queue = RetryQueue(redis)

    queue.schedule(
        event_id="event-123",
        run_id="run-456",
        attempt=2,
        delay=5,
    )

    monkeypatch.setattr(
        "app.queue.retry_queue.time.time",
        lambda: 1004.0,
    )

    result = queue.pop_due()

    assert result is None


def test_pop_due_returns_due_retry(monkeypatch):
    monkeypatch.setattr(
        "app.queue.retry_queue.time.time",
        lambda: 1000.0,
    )

    redis = FakeRedis()
    queue = RetryQueue(redis)

    queue.schedule(
        event_id="event-123",
        run_id="run-456",
        attempt=2,
        delay=5,
    )

    monkeypatch.setattr(
        "app.queue.retry_queue.time.time",
        lambda: 1005.0,
    )

    result = queue.pop_due()

    assert result == {
        "event_id": "event-123",
        "run_id": "run-456",
        "attempt": 2,
    }


def test_pop_due_removes_retry_after_returning_it(monkeypatch):
    monkeypatch.setattr(
        "app.queue.retry_queue.time.time",
        lambda: 1000.0,
    )

    redis = FakeRedis()
    queue = RetryQueue(redis)

    queue.schedule(
        event_id="event-123",
        run_id="run-456",
        attempt=2,
        delay=5,
    )

    monkeypatch.setattr(
        "app.queue.retry_queue.time.time",
        lambda: 1005.0,
    )

    first_result = queue.pop_due()

    assert first_result is not None

    second_result = queue.pop_due()

    assert second_result is None