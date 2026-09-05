import json

from app.db.redis import get_redis
from app.db.repositories.event import EventRepository


class EventWorker:
    QUEUE_NAME = "sentry:events"

    def __init__(
        self,
        redis_client=None,
        event_repository=None,
    ):
        self.redis = redis_client if redis_client is not None else get_redis()
        self.event_repository = (
            event_repository
            if event_repository is not None
            else EventRepository()
        )

    def process_next(self) -> bool:
        item = self.redis.lpop(self.QUEUE_NAME)

        if item is None:
            return False

        message = json.loads(item)
        event_id = message["event_id"]

        event = self.event_repository.get_by_id(event_id)

        if event is None:
            return False

        # Workflow execution will be added later.
        return True