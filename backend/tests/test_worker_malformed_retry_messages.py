import pytest

from app.worker.event_worker import EventWorker


class FakeRetryQueue:
    def __init__(self, item):
        self.item = item

    def pop_due(self):
        item = self.item
        self.item = None
        return item


@pytest.mark.parametrize(
    "message",
    [
        "not-a-dict",
        [],
        {},
        {"event_id": "event-1"},
        {"run_id": "run-1"},
        {"event_id": "event-1", "run_id": "run-1"},
    ],
)
def test_process_retry_next_ignores_malformed_retry_message(message):
    worker = EventWorker.__new__(EventWorker)
    worker.retry_queue = FakeRetryQueue(message)

    assert worker.process_retry_next() is False
