import pytest
from pymongo import MongoClient
from fastapi.testclient import TestClient

from app.config import settings

from app.db.repositories.workflow import WorkflowRepository
from app.db.repositories.event import EventRepository
from app.db.repositories.run import WorkflowRunRepository

from app.main import app

from app.routers.workflow_api import get_workflow_service
from app.routers.webhooks import get_event_service, get_event_queue
from app.routers.observability import (
    get_event_repository,
    get_run_repository,
)

from app.services.workflow import WorkflowService
from app.services.event import EventService


class FakeEventQueue:
    def __init__(self):
        self.events = []

    def enqueue(self, event_id: str):
        self.events.append(event_id)


@pytest.fixture
def repository():
    client = MongoClient(settings.mongodb_uri)
    database = client["sentry_workflow_test"]

    database.drop_collection("workflows")

    repository = WorkflowRepository(database=database)
    repository.create_indexes()

    yield repository

    database.drop_collection("workflows")
    client.close()


@pytest.fixture
def api_client(fake_event_queue):
    client = MongoClient(settings.mongodb_uri)
    database = client["sentry_workflow_api_test"]

    database.drop_collection("workflows")
    database.drop_collection("events")
    database.drop_collection("workflow_runs")

    workflow_repository = WorkflowRepository(database=database)
    event_repository = EventRepository(database=database)
    run_repository = WorkflowRunRepository(database=database)

    workflow_repository.create_indexes()
    event_repository.create_indexes()
    run_repository.create_indexes()

    workflow_service = WorkflowService(
        repository=workflow_repository
    )

    event_service = EventService(
        repository=event_repository
    )

    app.dependency_overrides[get_workflow_service] = (
        lambda: workflow_service
    )

    app.dependency_overrides[get_event_service] = (
        lambda: event_service
    )

    app.dependency_overrides[get_event_queue] = (
        lambda: fake_event_queue
    )

    app.dependency_overrides[get_event_repository] = (
        lambda: event_repository
    )

    app.dependency_overrides[get_run_repository] = (
        lambda: run_repository
    )

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()

    database.drop_collection("workflows")
    database.drop_collection("events")
    database.drop_collection("workflow_runs")

    client.close()


@pytest.fixture
def fake_event_queue():
    class FakeEventQueue:
        def __init__(self):
            self.events = []

        def enqueue(self, event_id: str):
            self.events.append(event_id)

    return FakeEventQueue()
