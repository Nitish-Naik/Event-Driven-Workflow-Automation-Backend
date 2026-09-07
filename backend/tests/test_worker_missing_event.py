import json

from app.worker.event_worker import EventWorker


class FakeRedis:
    def __init__(self, items=None):
        self.items = items or []

    def lpop(self, queue_name):
        if not self.items:
            return None
        return self.items.pop(0)


class FakeEventRepository:
    def get_by_id(self, event_id):
        return None


class FakeRunRepository:
    def __init__(self):
        self.runs = []

    def create(self, run):
        self.runs.append(run)
        return run.run_id


def test_process_next_ignores_missing_event_without_creating_run():
    event_id = "missing-event"
    redis = FakeRedis([json.dumps({"event_id": event_id})])
    run_repository = FakeRunRepository()

    worker = EventWorker(
        redis_client=redis,
        event_repository=FakeEventRepository(),
        run_repository=run_repository,
    )

    assert worker.process_next() is False
    assert run_repository.runs == []
    assert redis.items == []
