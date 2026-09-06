from collections.abc import Callable
from typing import Any

from app.execution.contracts import ExecutionContext


NodeHandler = Callable[
    [ExecutionContext, Any, dict[str, Any]],
    dict[str, Any],
]


class WorkflowExecutionError(Exception):
    """Raised when a workflow node cannot be executed."""
