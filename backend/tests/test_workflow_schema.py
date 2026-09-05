from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.workflow import Workflow


def make_workflow(**overrides):
    data = {
        "workflow_id": "workflow-1",
        "name": "Sentry Incident Triage",
        "nodes": [
            {
                "id": "sentry",
                "type": "sentry_trigger",
            },
            {
                "id": "ai",
                "type": "ai_analysis",
            },
        ],
        "edges": [
            {
                "source": "sentry",
                "target": "ai",
            }
        ],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    data.update(overrides)
    return data


def test_valid_workflow():
    workflow = Workflow(**make_workflow())

    assert workflow.workflow_id == "workflow-1"
    assert workflow.version == 1
    assert workflow.status == "draft"


def test_duplicate_node_ids_are_rejected():
    data = make_workflow(
        nodes=[
            {"id": "sentry", "type": "sentry_trigger"},
            {"id": "sentry", "type": "ai_analysis"},
        ]
    )

    with pytest.raises(ValidationError):
        Workflow(**data)


def test_edge_with_unknown_source_is_rejected():
    data = make_workflow(
        edges=[
            {
                "source": "unknown",
                "target": "ai",
            }
        ]
    )

    with pytest.raises(ValidationError):
        Workflow(**data)


def test_edge_with_unknown_target_is_rejected():
    data = make_workflow(
        edges=[
            {
                "source": "sentry",
                "target": "unknown",
            }
        ]
    )

    with pytest.raises(ValidationError):
        Workflow(**data)