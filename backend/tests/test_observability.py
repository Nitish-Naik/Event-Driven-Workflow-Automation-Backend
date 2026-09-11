import hashlib
import hmac
import json

from app.config import settings

from datetime import datetime, timezone

from pymongo import MongoClient

from app.config import settings
from app.db.repositories.run import WorkflowRunRepository
from app.schemas.run import RunStatus, WorkflowRun



def test_list_events(api_client):
    response = api_client.get("/events")

    assert response.status_code == 200

    body = response.json()

    assert "events" in body

def test_get_missing_event(api_client):
    response = api_client.get("/events/does-not-exist")

    assert response.status_code == 404
    assert response.json()["detail"] == "Event not found"

def test_get_event(api_client):
    payload = {
        "event": {
            "eventID": "event-api-test",
        },
        "message": "Test Sentry event",
    }

    raw_body = json.dumps(payload).encode("utf-8")

    signature = hmac.new(
        settings.sentry_webhook_secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    response = api_client.post(
        "/webhooks/sentry",
        content=raw_body,
        headers={
            "x-servicehook-signature": signature,
            "content-type": "application/json",
        },
    )

    assert response.status_code == 202

    response = api_client.get(
        "/events/event-api-test"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["event_id"] == "event-api-test"
    assert body["source"] == "sentry"

def test_list_runs(api_client):
    response = api_client.get("/runs")

    assert response.status_code == 200

    body = response.json()

    assert "runs" in body

def test_get_missing_run(api_client):
    response = api_client.get("/runs/does-not-exist")

    assert response.status_code == 404
    assert response.json()["detail"] == "Workflow run not found"



def test_get_run(api_client):
    client = MongoClient(settings.mongodb_uri)
    database = client["sentry_workflow_api_test"]

    repository = WorkflowRunRepository(database=database)

    run = WorkflowRun(
        run_id="run-api-test",
        workflow_id="workflow-api-test",
        workflow_version=1,
        event_id="event-api-test",
        status=RunStatus.COMPLETED,
        attempt=1,
        outputs={
            "result": "success",
        },
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    repository.create(run)

    response = api_client.get("/runs/run-api-test")

    assert response.status_code == 200

    body = response.json()

    assert body["run_id"] == "run-api-test"
    assert body["workflow_id"] == "workflow-api-test"
    assert body["workflow_version"] == 1
    assert body["event_id"] == "event-api-test"
    assert body["status"] == "completed"
    assert body["attempt"] == 1
    assert body["outputs"]["result"] == "success"

    client.close()

def test_list_failures(api_client):
    response = api_client.get("/failures")

    assert response.status_code == 200

    body = response.json()

    assert "failures" in body

def test_list_failures_returns_failed_runs(api_client):
    client = MongoClient(settings.mongodb_uri)
    database = client["sentry_workflow_api_test"]

    repository = WorkflowRunRepository(database=database)

    run = WorkflowRun(
        run_id="failed-run-api-test",
        workflow_id="workflow-api-test",
        workflow_version=1,
        event_id="event-api-test",
        status=RunStatus.FAILED,
        attempt=2,
        outputs={},
        last_error="Sentry API unavailable",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    repository.create(run)

    response = api_client.get("/failures")

    assert response.status_code == 200

    body = response.json()

    assert len(body["failures"]) == 1

    failure = body["failures"][0]

    assert failure["run_id"] == "failed-run-api-test"
    assert failure["status"] == "failed"
    assert failure["attempt"] == 2
    assert failure["last_error"] == "Sentry API unavailable"

    client.close()


def test_retry_failed_run(api_client):
    client = MongoClient(settings.mongodb_uri)
    database = client["sentry_workflow_api_test"]

    repository = WorkflowRunRepository(database=database)

    run = WorkflowRun(
        run_id="retry-run-api-test",
        workflow_id="workflow-api-test",
        workflow_version=1,
        event_id="event-api-test",
        status=RunStatus.FAILED,
        attempt=1,
        outputs={},
        last_error="Temporary Sentry failure",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    repository.create(run)

    response = api_client.post(
        "/failures/retry-run-api-test/retry"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["run_id"] == "retry-run-api-test"
    assert body["status"] == "retrying"
    assert body["attempt"] == 2

    updated_run = repository.get_by_id("retry-run-api-test")

    assert updated_run.status == RunStatus.RETRYING
    assert updated_run.attempt == 2
    assert updated_run.last_error == "manual retry"

    client.close()

def test_retry_completed_run_returns_conflict(api_client):
    client = MongoClient(settings.mongodb_uri)
    database = client["sentry_workflow_api_test"]

    repository = WorkflowRunRepository(database=database)

    run = WorkflowRun(
        run_id="completed-run-api-test",
        workflow_id="workflow-api-test",
        workflow_version=1,
        event_id="event-api-test",
        status=RunStatus.COMPLETED,
        attempt=1,
        outputs={"result": "success"},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    repository.create(run)

    response = api_client.post(
        "/failures/completed-run-api-test/retry"
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Only failed runs can be retried"

    client.close()

def test_retry_missing_run(api_client):
    response = api_client.post(
        "/failures/does-not-exist/retry"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Workflow run not found"