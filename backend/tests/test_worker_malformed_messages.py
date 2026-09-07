import json

from app.worker.event_worker import EventWorker


class FakeRedis:
    def __init__(self, item):
        self.item = item

    def lpop(self, queue_name):
        item = self.item
        self.item = None
        return item


def test_process_next_ignores_malformed_json():
    worker = EventWorker.__new__(EventWorker)
    worker.redis = FakeRedis("not-json")

    assert worker.process_next() is False


def test_process_next_ignores_non_object_message():
    worker = EventWorker.__new__(EventWorker)
    worker.redis = FakeRedis(json.dumps(["event-1"]))

    assert worker.process_next() is False


def test_process_next_ignores_message_without_event_id():
    worker = EventWorker.__new__(EventWorker)
    worker.redis = FakeRedis(json.dumps({"unexpected": "value"}))

    assert worker.process_next() is False
