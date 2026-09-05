import pytest
from pymongo import MongoClient
from fastapi.testclient import TestClient

from app.config import settings

from app.db.repositories.workflow import WorkflowRepository
from app.db.repositories.event import EventRepository

from app.main import app

from app.routers.workflows import get_workflow_service
from app.routers.webhooks import get_event_service

from app.services.workflow import WorkflowService
from app.services.event import EventService

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
def api_client():
    client = MongoClient(settings.mongodb_uri)
    database = client["sentry_workflow_api_test"]

    database.drop_collection("workflows")
    database.drop_collection("events")

    repository = WorkflowRepository(database=database)
    event_repository = EventRepository(database=database)

    repository.create_indexes()
    event_repository.create_indexes()

    workflow_service = WorkflowService(repository=repository)
    event_service = EventService(repository=event_repository)

    app.dependency_overrides[get_workflow_service] = lambda: workflow_service
    app.dependency_overrides[get_event_service] = lambda: event_service

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()

    database.drop_collection("workflows")
    database.drop_collection("events")
    client.close()