from dataclasses import dataclass, field
from typing import Any

from app.schemas.event import Event
from app.schemas.workflow import Workflow


@dataclass
class ExecutionContext:
    workflow: Workflow
    event: Event
    values: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionResult:
    outputs: dict[str, Any] = field(default_factory=dict)


class WorkflowExecutor:
    def execute(
        self,
        workflow: Workflow,
        event: Event,
    ) -> ExecutionResult:
        raise NotImplementedError
