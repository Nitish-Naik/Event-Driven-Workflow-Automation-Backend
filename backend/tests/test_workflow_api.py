from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.routers.workflows import get_workflow_service
from app.schemas.workflow import Workflow


class FakeWorkflowService:
    def __init__(self):
        now = datetime.now(timezone.utc)
        self.workflows = [Workflow(
            workflow_id="wf-1", name="Incident Workflow", trigger="sentry",
            version=1, status="draft", nodes=[], edges=[],
            created_at=now, updated_at=now,
        )]

    def list_workflows(self): return self.workflows
    def create_workflow(self, workflow): self.workflows.append(workflow); return workflow.workflow_id
    def get_workflow(self, workflow_id, version):
        return next((w for w in self.workflows if w.workflow_id == workflow_id and w.version == version), None)
    def get_active_workflow(self, workflow_id):
        return next((w for w in self.workflows if w.workflow_id == workflow_id and w.status == "active"), None)
    def update_workflow(self, workflow):
        for i, existing in enumerate(self.workflows):
            if existing.workflow_id == workflow.workflow_id and existing.version == workflow.version:
                self.workflows[i] = workflow
                return workflow
        raise RuntimeError("not found")
    def activate_workflow(self, workflow_id, version):
        for workflow in self.workflows:
            if workflow.workflow_id == workflow_id:
                workflow.status = "active" if workflow.version == version else "archived"
    def deactivate_workflow(self, workflow_id, version):
        workflow = self.get_workflow(workflow_id, version)
        if workflow: workflow.status = "draft"


service = FakeWorkflowService()
app.dependency_overrides[get_workflow_service] = lambda: service
client = TestClient(app)


def workflow_payload(workflow_id="wf-2", version=1):
    now = datetime.now(timezone.utc).isoformat()
    return {"workflow_id": workflow_id, "name": "Test Workflow", "trigger": "sentry",
            "version": version, "status": "draft", "nodes": [], "edges": [],
            "created_at": now, "updated_at": now}


def test_list_workflows():
    response = client.get("/workflows")
    assert response.status_code == 200
    assert response.json()[0]["workflow_id"] == "wf-1"


def test_create_workflow():
    response = client.post("/workflows", json=workflow_payload())
    assert response.status_code == 201
    assert response.json() == {"workflow_id": "wf-2"}


def test_get_workflow_version():
    response = client.get("/workflows/wf-1/versions/1")
    assert response.status_code == 200
    assert response.json()["version"] == 1


def test_get_missing_workflow_returns_404():
    response = client.get("/workflows/missing/versions/1")
    assert response.status_code == 404


def test_activate_and_get_active_workflow():
    response = client.post("/workflows/wf-1/versions/1/activate")
    assert response.status_code == 204
    response = client.get("/workflows/wf-1/active")
    assert response.status_code == 200
    assert response.json()["status"] == "active"


def test_update_workflow_version():
    payload = workflow_payload("wf-1", 1)
    payload["name"] = "Updated Workflow"
    response = client.put("/workflows/wf-1/versions/1", json=payload)
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Workflow"


def test_update_rejects_path_body_mismatch():
    response = client.put("/workflows/wf-1/versions/1", json=workflow_payload("different", 1))
    assert response.status_code == 400


def test_deactivate_workflow():
    response = client.post("/workflows/wf-1/versions/1/deactivate")
    assert response.status_code == 204
    assert client.get("/workflows/wf-1/active").status_code == 404
