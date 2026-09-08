import pytest
from pydantic import BaseModel

from app.integrations.tools.validation import (
    ToolInputValidationError,
    validate_tool_inputs,
)


class GetIssueInput(BaseModel):
    issue_id: str


def test_validate_tool_inputs_returns_validated_data():
    result = validate_tool_inputs(
        GetIssueInput,
        {"issue_id": "123"},
    )

    assert result == {
        "issue_id": "123",
    }


def test_validate_tool_inputs_rejects_missing_required_field():
    with pytest.raises(ToolInputValidationError):
        validate_tool_inputs(
            GetIssueInput,
            {},
        )


def test_validate_tool_inputs_rejects_invalid_input():
    with pytest.raises(ToolInputValidationError):
        validate_tool_inputs(
            GetIssueInput,
            {"issue_id": None},
        )


def test_validate_tool_inputs_preserves_validation_error_as_cause():
    with pytest.raises(ToolInputValidationError) as exc_info:
        validate_tool_inputs(
            GetIssueInput,
            {},
        )

    assert exc_info.value.__cause__ is not None