import json
import uuid
from datetime import datetime, timezone

from pymongo.errors import DuplicateKeyError

from app.db.redis import get_redis
from app.db.repositories.event import EventRepository
from app.db.repositories.run import WorkflowRunRepository
from app.execution.async_executor import AsyncWorkflowNodeExecutor
from app.execution.async_registry import create_async_registry
from app.execution.contracts import ExecutionContext
from app.execution.defaults import create_default_registry
from app.execution.executor import WorkflowNodeExecutor
from app.queue.event_queue import QueuedEvent
from app.schemas.run import RunStatus, WorkflowRun
from app.services.workflow import WorkflowService
from app.queue.retry_queue import RetryQueue
from app.services.retry import calculate_retry_delay, is_retryable_error


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
        async_workflow_executor=None,
        retry_queue=None,
    ):
        self.redis = redis_client if redis_client is not None else get_redis()
        self.event_repository = event_repository if event_repository is not None else EventRepository()
        self.run_repository = run_repository if run_repository is not None else WorkflowRunRepository()
        self.workflow_service = workflow_service if workflow_service is not None else WorkflowService()
        self.workflow_executor = workflow_executor if workflow_executor is not None else WorkflowNodeExecutor(registry=create_default_registry())
        self.async_workflow_executor = async_workflow_executor if async_workflow_executor is not None else AsyncWorkflowNodeExecutor(registry=create_async_registry())
        self.retry_queue = retry_queue if retry_queue is not None else RetryQueue(self.redis)

    def _execute_run(self, run, workflow, event) -> bool:
        self.run_repository.update_status(run.run_id, RunStatus.PROCESSING)

        try:
            if isinstance(self.workflow_executor, WorkflowNodeExecutor):
                context = ExecutionContext(workflow=workflow, event=event)
                result = self.workflow_executor.execute(context)
            else:
                result = self.workflow_executor.execute(workflow, event)
        except Exception as exc:
            self.run_repository.update_status(run.run_id, RunStatus.FAILED)

            if not is_retryable_error(exc):
                return True

            if run.attempt >= self.MAX_ATTEMPTS:
                self.run_repository.update_status(run.run_id, RunStatus.DEAD_LETTER)
                return True

            next_attempt = run.attempt + 1
            delay = calculate_retry_delay(next_attempt)
            self.run_repository.update_retry_metadata(
                run_id=run.run_id,
                attempt=next_attempt,
                last_error=str(exc),
            )
            self.run_repository.update_status(run.run_id, RunStatus.RETRYING)
            self.retry_queue.schedule(
                event_id=event.event_id,
                run_id=run.run_id,
                attempt=next_attempt,
                delay=delay,
            )
            return True

        outputs = getattr(result, "outputs", {})
        update_outputs = getattr(self.run_repository, "update_outputs", None)
        if update_outputs is not None:
            update_outputs(run.run_id, outputs)

        self.run_repository.update_status(run.run_id, RunStatus.COMPLETED)
        return True

    async def _execute_run_async(self, run, workflow, event) -> bool:
        self.run_repository.update_status(run.run_id, RunStatus.PROCESSING)

        try:
            context = ExecutionContext(workflow=workflow, event=event)
            result = await self.async_workflow_executor.execute(context)
        except Exception as exc:
            self.run_repository.update_status(run.run_id, RunStatus.FAILED)

            if not is_retryable_error(exc):
                return True

            if run.attempt >= self.MAX_ATTEMPTS:
                self.run_repository.update_status(run.run_id, RunStatus.DEAD_LETTER)
                return True

            next_attempt = run.attempt + 1
            delay = calculate_retry_delay(next_attempt)
            self.run_repository.update_retry_metadata(
                run_id=run.run_id,
                attempt=next_attempt,
                last_error=str(exc),
            )
            self.run_repository.update_status(run.run_id, RunStatus.RETRYING)
            self.retry_queue.schedule(
                event_id=event.event_id,
                run_id=run.run_id,
                attempt=next_attempt,
                delay=delay,
            )
            return True

        outputs = getattr(result, "outputs", {})
        update_outputs = getattr(self.run_repository, "update_outputs", None)
        if update_outputs is not None:
            update_outputs(run.run_id, outputs)

        self.run_repository.update_status(run.run_id, RunStatus.COMPLETED)
        return True

    @staticmethod
    def _execution_key(workflow, event) -> str:
        return f"{event.event_id}:{workflow.workflow_id}:{workflow.version}"

    def _build_run(self, workflow, event) -> WorkflowRun:
        now = datetime.now(timezone.utc)
        return WorkflowRun(
            run_id=str(uuid.uuid4()),
            workflow_id=workflow.workflow_id,
            workflow_version=workflow.version,
            event_id=event.event_id,
            execution_key=self._execution_key(workflow, event),
            status=RunStatus.QUEUED,
            created_at=now,
            updated_at=now,
        )

    async def process_reserved_async(self, queued_event: QueuedEvent) -> bool:
        event = self.event_repository.get_by_id(queued_event.event_id)
        if event is None:
            return True

        workflow = self.workflow_service.get_active_workflow_by_trigger(event.source)
        if workflow is None:
            return True

        execution_key = self._execution_key(workflow, event)
        if self.run_repository.get_by_execution_key(execution_key) is not None:
            return True

        run = self._build_run(workflow, event)
        try:
            self.run_repository.create(run)
        except DuplicateKeyError:
            return True

        return await self._execute_run_async(run, workflow, event)

    def process_next(self) -> bool:
        item = self.redis.lpop(self.QUEUE_NAME)
        if item is None:
            return False

        try:
            message = json.loads(item)
        except (TypeError, json.JSONDecodeError):
            return False

        if not isinstance(message, dict):
            return False

        event_id = message.get("event_id")
        if not event_id:
            return False

        event = self.event_repository.get_by_id(event_id)
        if event is None:
            return False

        workflow = self.workflow_service.get_active_workflow_by_trigger(event.source)
        if workflow is None:
            return False

        run = self._build_run(workflow, event)
        self.run_repository.create(run)
        return self._execute_run(run, workflow, event)

    async def process_next_async(self) -> bool:
        item = self.redis.lpop(self.QUEUE_NAME)
        if item is None:
            return False

        try:
            message = json.loads(item)
        except (TypeError, json.JSONDecodeError):
            return False

        if not isinstance(message, dict):
            return False

        event_id = message.get("event_id")
        if not event_id:
            return False

        event = self.event_repository.get_by_id(event_id)
        if event is None:
            return False

        workflow = self.workflow_service.get_active_workflow_by_trigger(event.source)
        if workflow is None:
            return False

        run = self._build_run(workflow, event)
        self.run_repository.create(run)
        return await self._execute_run_async(run, workflow, event)

    def process_retry_next(self) -> bool:
        retry = self.retry_queue.pop_due()
        if retry is None:
            return False

        if not isinstance(retry, dict):
            return False

        event_id = retry.get("event_id")
        run_id = retry.get("run_id")
        attempt = retry.get("attempt")

        if not event_id or not run_id or not isinstance(attempt, int) or attempt < 1:
            return False

        event = self.event_repository.get_by_id(event_id)
        if event is None:
            return False

        run = self.run_repository.get_by_id(run_id)
        if run is None:
            return False

        workflow = self.workflow_service.get_workflow(run.workflow_id, run.workflow_version)
        if workflow is None:
            return False

        return self._execute_run(run, workflow, event)

    async def process_retry_next_async(self) -> bool:
        retry = self.retry_queue.pop_due()
        if retry is None:
            return False

        if not isinstance(retry, dict):
            return False

        event_id = retry.get("event_id")
        run_id = retry.get("run_id")
        attempt = retry.get("attempt")

        if not event_id or not run_id or not isinstance(attempt, int) or attempt < 1:
            return False

        event = self.event_repository.get_by_id(event_id)
        if event is None:
            return False

        run = self.run_repository.get_by_id(run_id)
        if run is None:
            return False

        workflow = self.workflow_service.get_workflow(run.workflow_id, run.workflow_version)
        if workflow is None:
            return False

        return await self._execute_run_async(run, workflow, event)
