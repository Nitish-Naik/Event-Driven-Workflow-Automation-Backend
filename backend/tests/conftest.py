import pytest
from pymongo import MongoClient
from fastapi.testclient import TestClient

from app.config import settings
from app.db.repositories.workflow import WorkflowRepository
from app.main import app
from app.routers.workflows import get_workflow_service
from app.services.workflow import WorkflowService

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

    repository = WorkflowRepository(database=database)
    repository.create_indexes()

    service = WorkflowService(repository=repository)

    app.dependency_overrides[get_workflow_service] = lambda: service

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()

    database.drop_collection("workflows")
    client.close()