from datetime import datetime, timezone

import pytest

from app.execution.async_executor import AsyncWorkflowNodeExecutor
from app.execution.async_registry import create_async_registry
from app.execution.contracts import ExecutionContext
from app.integrations.registry import IntegrationRegistry
from app.schemas.event import Event
from app.schemas.workflow import Workflow, WorkflowEdge, WorkflowNode


class FakeTool:
    name = "get_issue"

    async def execute(self, inputs):
        return {"issue_id": inputs["issue_id"], "status": "resolved"}


class FakeIntegration:
    name = "sentry"

    def get_tools(self):
        return [FakeTool()]


def make_context():
    now = datetime.now(timezone.utc)
    workflow = Workflow(
        workflow_id="wf-tool",
        name="tool-workflow",
        trigger="sentry.issue",
        nodes=[
            WorkflowNode(id="trigger", type="sentry_trigger"),
            WorkflowNode(
                id="tool",
                type="tool",
                config={
                    "integration": "sentry",
                    "tool": "get_issue",
                    "inputs": {"issue_id": "ISSUE-1"},
                },
            ),
        ],
        edges=[WorkflowEdge(source="trigger", target="tool")],
        created_at=now,
        updated_at=now,
    )
    event = Event(
        event_id="event-tool",
        source="sentry",
        event_type="sentry.issue",
        payload={"message": "failure"},
        received_at=now,
    )
    return ExecutionContext(workflow=workflow, event=event)


@pytest.mark.asyncio
async def test_async_executor_runs_integration_tool_node():
    integrations = IntegrationRegistry()
    integration = FakeIntegration()
    integrations._integrations["sentry"] = integration

    executor = AsyncWorkflowNodeExecutor(create_async_registry(integrations))

    result = await executor.execute(make_context())

    assert result.outputs["trigger"]["event_id"] == "event-tool"
    assert result.outputs["tool"] == {
        "issue_id": "ISSUE-1",
        "status": "resolved",
    }


@pytest.mark.asyncio
async def test_async_executor_passes_upstream_output_to_tool_node():
    class InputTool:
        name = "get_issue"

        async def execute(self, inputs):
            return {"received": inputs["issue"]}

    class InputIntegration:
        name = "sentry"

        def get_tools(self):
            return [InputTool()]

    integrations = IntegrationRegistry()
    integrations._integrations["sentry"] = InputIntegration()
    executor = AsyncWorkflowNodeExecutor(create_async_registry(integrations))
    context = make_context()
    context.workflow.nodes[1].config["inputs"] = {"issue": "$trigger"}

    result = await executor.execute(context)

    assert result.outputs["tool"]["received"]["event_id"] == "event-tool"
