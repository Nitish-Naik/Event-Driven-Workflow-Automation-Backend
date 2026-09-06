import json

from app.db.redis import get_redis
from app.db.repositories.event import EventRepository
from app.db.repositories.run import WorkflowRunRepository
from app.schemas.run import RunStatus, WorkflowRun

import uuid
from datetime import datetime, timezone

class EventWorker:
    QUEUE_NAME = "sentry:events"

    def __init__(
        self,
        redis_client=None,
        event_repository=None,
        run_repository=None,
    ):
        self.redis = redis_client if redis_client is not None else get_redis()
        self.event_repository = (
            event_repository
            if event_repository is not None
            else EventRepository()
        )
        self.run_repository = (
        run_repository
        if run_repository is not None
        else WorkflowRunRepository()
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
        
        now = datetime.now(timezone.utc)

        run = WorkflowRun(
            run_id=str(uuid.uuid4()),
            workflow_id="default",
            workflow_version=1,
            event_id=event.event_id,
            status=RunStatus.PROCESSING,
            created_at=now,
            updated_at=now,
        )

        self.run_repository.create(run)

        return True