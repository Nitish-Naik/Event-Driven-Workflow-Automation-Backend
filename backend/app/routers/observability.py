from fastapi import APIRouter, Depends, HTTPException

from app.db.repositories.event import EventRepository
from app.db.repositories.run import WorkflowRunRepository
from app.queue.retry_queue import RetryQueue
from app.db.redis import get_redis
from app.schemas.run import RunStatus

router = APIRouter(tags=["observability"])


def get_event_repository():
    return EventRepository()


def get_run_repository():
    return WorkflowRunRepository()


@router.get("/events")
def list_events(repository: EventRepository = Depends(get_event_repository)):
    return {"events": repository.list_all()}


@router.get("/events/{event_id}")
def get_event(event_id: str, repository: EventRepository = Depends(get_event_repository)):
    event = repository.get_by_id(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.get("/runs")
def list_runs(repository: WorkflowRunRepository = Depends(get_run_repository)):
    return {"runs": repository.list_all()}


@router.get("/runs/{run_id}")
def get_run(run_id: str, repository: WorkflowRunRepository = Depends(get_run_repository)):
    run = repository.get_by_id(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    return run


@router.get("/failures")
def list_failures(repository: WorkflowRunRepository = Depends(get_run_repository)):
    return {"failures": repository.list_failures()}


@router.post("/failures/{run_id}/retry")
def retry_failure(
    run_id: str,
    repository: WorkflowRunRepository = Depends(get_run_repository),
):
    run = repository.get_by_id(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    if run.status not in {RunStatus.FAILED, RunStatus.DEAD_LETTER}:
        raise HTTPException(status_code=409, detail="Only failed runs can be retried")

    next_attempt = run.attempt + 1
    repository.update_retry_metadata(run_id, next_attempt, "manual retry")
    repository.update_status(run_id, RunStatus.RETRYING)
    RetryQueue(get_redis()).schedule(run.event_id, run.run_id, next_attempt, 0)
    return {"run_id": run_id, "status": RunStatus.RETRYING, "attempt": next_attempt}
