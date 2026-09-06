import json
import uuid
from datetime import datetime, timezone

from app.db.redis import get_redis
from app.db.repositories.event import EventRepository
from app.db.repositories.run import WorkflowRunRepository
from app.schemas.run import RunStatus, WorkflowRun
from app.services.workflow import WorkflowService
from app.queue.retry_queue import RetryQueue

from app.services.retry import ( is_retryable_error, calculate_retry_delay )


class EventWorker:
    QUEUE_NAME = "sentry:events"
    MAX_ATTEMPTS = 3

    def __init__(
        self,
        redis_client=None,
        event_repository=None,
        run_repository=None,
        workflow_service=None,
        workflow_executor=None,
        retry_queue=None,
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
        self.workflow_executor = workflow_executor

        self.retry_queue = retry_queue if retry_queue is not None else RetryQueue(self.redis)

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

        if self.workflow_executor is None:
            return True

        try:
            self.workflow_executor.execute(workflow, event)
        except Exception as exc:
            self.run_repository.update_status(
                run.run_id,
                RunStatus.FAILED,
            )

            if not is_retryable_error(exc):
                return True

            if run.attempt >= self.MAX_ATTEMPTS:
                self.run_repository.update_status(
                    run.run_id,
                    RunStatus.DEAD_LETTER,
                )
                return True

            next_attempt = run.attempt + 1

            delay = calculate_retry_delay(
                next_attempt,
            )

            self.run_repository.update_retry_metadata(
                run_id=run.run_id,
                attempt=next_attempt,
                last_error=str(exc),
            )

            self.run_repository.update_status(
                run.run_id,
                RunStatus.RETRYING,
            )

            self.retry_queue.schedule(
                event_id=event.event_id,
                run_id=run.run_id,
                attempt=next_attempt,
                delay=delay,
            )

            return True

        self.run_repository.update_status(
            run.run_id,
            RunStatus.COMPLETED,
        )

        return True

    def process_retry_next(self) -> bool:
        retry = self.retry_queue.pop_due()

        if retry is None:
            return False

        event_id = retry["event_id"]
        run_id = retry["run_id"]

        event = self.event_repository.get_by_id(event_id)

        if event is None:
            return False

        run = self.run_repository.get_by_id(run_id)

        if run is None:
            return False

        workflow = self.workflow_service.get_workflow(
            run.workflow_id,
            run.workflow_version,
        )

        if workflow is None:
            return False

        self.run_repository.update_status(
            run.run_id,
            RunStatus.PROCESSING,
        )

        if self.workflow_executor is None:
            return True

        try:
            self.workflow_executor.execute(workflow, event)

        except Exception as exc:
            self.run_repository.update_status(
                run.run_id,
                RunStatus.FAILED,
            )

            if not is_retryable_error(exc):
                return True

            if run.attempt >= self.MAX_ATTEMPTS:
                self.run_repository.update_status(
                    run.run_id,
                    RunStatus.DEAD_LETTER,
                )
                return True

            next_attempt = run.attempt + 1

            delay = calculate_retry_delay(
                next_attempt,
            )

            self.run_repository.update_retry_metadata(
                run_id=run.run_id,
                attempt=next_attempt,
                last_error=str(exc),
            )

            self.run_repository.update_status(
                run.run_id,
                RunStatus.RETRYING,
            )

            self.retry_queue.schedule(
                event_id=event.event_id,
                run_id=run.run_id,
                attempt=next_attempt,
                delay=delay,
            )

            return True

        self.run_repository.update_status(
            run.run_id,
            RunStatus.COMPLETED,
        )

        return True


