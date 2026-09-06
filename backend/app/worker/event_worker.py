import json
import uuid
from datetime import datetime, timezone

from app.db.redis import get_redis
from app.db.repositories.event import EventRepository
from app.db.repositories.run import WorkflowRunRepository
from app.schemas.run import RunStatus, WorkflowRun
from app.services.workflow import WorkflowService


class EventWorker:
    QUEUE_NAME = "sentry:events"

    def __init__(
        self,
        redis_client=None,
        event_repository=None,
        run_repository=None,
        workflow_service=None,
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
        self.workflow_service = (
            workflow_service
            if workflow_service is not None
            else WorkflowService()
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

        workflow = self.workflow_service.get_active_workflow_by_trigger(
            event.source
        )

        if workflow is None:
            return False

        now = datetime.now(timezone.utc)

        run = WorkflowRun(
            run_id=str(uuid.uuid4()),
            workflow_id=workflow.workflow_id,
            workflow_version=workflow.version,
            event_id=event.event_id,
            status=RunStatus.QUEUED,
            created_at=now,
            updated_at=now,
        )

        self.run_repository.create(run)
        self.run_repository.update_status(run.run_id, RunStatus.PROCESSING)

        return True
