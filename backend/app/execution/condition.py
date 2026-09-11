from typing import Any


class ConditionNode:
    """Evaluate a simple comparison between two resolved workflow inputs."""

    SUPPORTED_OPERATORS = {
        "eq",
        "neq",
        "contains",
        "in",
        "not_in",
        "gt",
        "gte",
        "lt",
        "lte",
    }

    def execute(
        self,
        context: Any,
        config: dict[str, Any],
        inputs: dict[str, Any],
    ) -> dict[str, Any]:
        operator = config.get("operator", "eq")
        if operator not in self.SUPPORTED_OPERATORS:
            raise ValueError(f"Unsupported condition operator: {operator}")

        if "left" not in inputs or "right" not in inputs:
            raise ValueError("Condition node requires 'left' and 'right' inputs")

        left = inputs["left"]
        right = inputs["right"]
        matched = self._compare(operator, left, right)

        return {
            "matched": matched,
            "left": left,
            "right": right,
            "operator": operator,
        }

    @staticmethod
    def _compare(operator: str, left: Any, right: Any) -> bool:
        if operator == "eq":
            return left == right
        if operator == "neq":
            return left != right
        if operator == "contains":
            return right in left
        if operator == "in":
            return left in right
        if operator == "not_in":
            return left not in right
        if operator == "gt":
            return left > right
        if operator == "gte":
            return left >= right
        if operator == "lt":
            return left < right
        if operator == "lte":
            return left <= right
        raise ValueError(f"Unsupported condition operator: {operator}")
