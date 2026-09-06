def test_create_workflow(api_client):
    payload = {
        "workflow_id": "api-workflow",
        "name": "API Test Workflow",
        "trigger": "sentry",
        "version": 1,
        "status": "draft",
        "nodes": [],
        "edges": [],
        "created_at": "2026-09-05T10:00:00Z",
        "updated_at": "2026-09-05T10:00:00Z",
    }

    api_client.post(
        "/workflows",
        json=payload,
    )

    response = api_client.get(
        "/workflows/api-workflow/versions/1"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["workflow_id"] == "api-workflow"
    assert body["version"] == 1
    assert body["status"] == "draft"

def test_get_missing_workflow(api_client):
    response = api_client.get(
        "/workflows/does-not-exist/versions/1"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Workflow not found"


def test_get_active_workflow(api_client):
    payload = {
        "workflow_id": "active-workflow",
        "name": "Active Workflow",
        "trigger": "sentry",
        "version": 1,
        "status": "active",
        "nodes": [],
        "edges": [],
        "created_at": "2026-09-05T10:00:00Z",
        "updated_at": "2026-09-05T10:00:00Z",
    }

    api_client.post(
        "/workflows",
        json=payload,
    )

    response = api_client.get(
        "/workflows/active-workflow/active"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["workflow_id"] == "active-workflow"
    assert body["version"] == 1
    assert body["status"] == "active"


def test_get_active_workflow_not_found(api_client):
    response = api_client.get(
        "/workflows/no-active-workflow/active"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Active workflow not found"


def test_activate_workflow(api_client):
    payload = {
        "workflow_id": "activate-workflow",
        "name": "Activation Test",
        "trigger": "sentry",
        "version": 1,
        "status": "draft",
        "nodes": [],
        "edges": [],
        "created_at": "2026-09-05T10:00:00Z",
        "updated_at": "2026-09-05T10:00:00Z",
    }

    api_client.post(
        "/workflows",
        json=payload,
    )

    response = api_client.post(
        "/workflows/activate-workflow/versions/1/activate"
    )

    assert response.status_code == 204

    response = api_client.get(
        "/workflows/activate-workflow/active"
    )

    assert response.status_code == 200
    assert response.json()["version"] == 1
    assert response.json()["status"] == "active"


def test_activate_missing_workflow(api_client):
    response = api_client.post(
        "/workflows/missing-workflow/versions/1/activate"
    )

    assert response.status_code == 404

def test_activate_new_version_archives_previous_version(api_client):
    v1 = {
        "workflow_id": "versioned-workflow",
        "name": "Versioned Workflow",
        "trigger": "sentry",
        "version": 1,
        "status": "active",
        "nodes": [],
        "edges": [],
        "created_at": "2026-09-05T10:00:00Z",
        "updated_at": "2026-09-05T10:00:00Z",
    }

    v2 = {
        **v1,
        "version": 2,
        "status": "draft",
    }

    api_client.post("/workflows", json=v1)
    api_client.post("/workflows", json=v2)

    response = api_client.post(
        "/workflows/versioned-workflow/versions/2/activate"
    )

    assert response.status_code == 204

    v1_response = api_client.get(
        "/workflows/versioned-workflow/versions/1"
    )

    v2_response = api_client.get(
        "/workflows/versioned-workflow/versions/2"
    )

    assert v1_response.json()["status"] == "archived"
    assert v2_response.json()["status"] == "active"
