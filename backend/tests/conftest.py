import pytest
from pymongo import MongoClient

from app.config import settings
from app.db.repositories.workflow import WorkflowRepository


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