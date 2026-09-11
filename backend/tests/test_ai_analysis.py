import pytest

from app.ai.provider import AIAnalysis, FakeAIProvider
from app.execution.ai_analysis import AIAnalysisNode
from app.execution.contracts import ExecutionContext
from app.schemas.event import Event
from app.schemas.workflow import Workflow


def make_context() -> ExecutionContext:
    workflow = Workflow(
        workflow_id="wf-1",
        name="AI analysis",
        trigger="sentry.issue",
        nodes=[],
        edges=[],
    )
    event = Event(
        event_id="event-1",
        source="sentry",
        event_type="issue",
        payload={"message": "PostgreSQL connection timeout", "level": "error"},
        received_at=None,
    )
    return ExecutionContext(workflow=workflow, event=event)


@pytest.mark.asyncio
async def test_fake_ai_provider_returns_structured_analysis():
    result = await FakeAIProvider().analyze(
        event={"message": "PostgreSQL connection timeout", "level": "error"}
    )

    assert isinstance(result, AIAnalysis)
    assert result.summary == "PostgreSQL connection timeout"
    assert result.severity == "high"
    assert result.category == "database"
    assert result.confidence == 0.95


@pytest.mark.asyncio
async def test_ai_analysis_node_delegates_to_provider():
    node = AIAnalysisNode(FakeAIProvider())

    result = await node.execute(
        make_context(),
        {"prompt": "Classify this Sentry event"},
        {
            "event": {
                "message": "Payment API failed",
                "level": "error",
            }
        },
    )

    assert result["summary"] == "Payment API failed"
    assert result["severity"] == "high"
    assert result["category"] == "application"
    assert 0.0 <= result["confidence"] <= 1.0


@pytest.mark.asyncio
async def test_ai_analysis_node_requires_event_object():
    node = AIAnalysisNode(FakeAIProvider())

    with pytest.raises(ValueError, match="requires an 'event' object"):
        await node.execute(make_context(), {}, {})
