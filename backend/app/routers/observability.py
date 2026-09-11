from fastapi import APIRouter, Depends, HTTPException

from app.db.repositories.event import EventRepository
from app.db.repositories.run import WorkflowRunRepository

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
