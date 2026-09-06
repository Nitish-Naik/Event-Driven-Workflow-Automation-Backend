from typing import Any

from app.execution.contracts import ExecutionContext


class InputResolutionError(Exception):
    """Raised when a workflow node input cannot be resolved."""


def resolve_node_input(
    context: ExecutionContext,
    node_id: str,
    field: str,
) -> Any:
    """Resolve a field from a previously executed node's output."""

    node_output = context.values.get(node_id)

    if node_output is None:
        raise InputResolutionError(
            f"No output available for node '{node_id}'"
        )

    if not isinstance(node_output, dict):
        raise InputResolutionError(
            f"Output from node '{node_id}' must be a dictionary"
        )

    if field not in node_output:
        raise InputResolutionError(
            f"Field '{field}' not found in output from node '{node_id}'"
        )

    return node_output[field]


def resolve_input_value(
    context: ExecutionContext,
    value: Any,
) -> Any:
    """Resolve literals and node-output references recursively."""

    if isinstance(value, dict):
        if "$ref" in value:
            reference = value["$ref"]

            if not isinstance(reference, str) or "." not in reference:
                raise InputResolutionError(
                    "Invalid node input reference"
                )

            node_id, field = reference.split(".", 1)

            if not node_id or not field:
                raise InputResolutionError(
                    "Invalid node input reference"
                )

            return resolve_node_input(context, node_id, field)

        return {
            key: resolve_input_value(context, item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [resolve_input_value(context, item) for item in value]

    return value
