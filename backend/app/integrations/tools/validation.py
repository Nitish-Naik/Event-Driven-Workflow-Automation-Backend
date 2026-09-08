from typing import Any

from pydantic import BaseModel, ValidationError

class ToolInputValidationError(ValueError):
    """Raised when tool inputs do not satisfy the tool's input contract."""

def validate_tool_inputs(
        input_model: type[BaseModel],
        inputs: dict[str, Any],
) -> dict[str, Any]:
    try:
        validated = input_model.model_validate(inputs)
    except ValidationError as e:
        raise ToolInputValidationError(str(e)) from e
    
    return validated.model_dump()