from app.execution.builtins import builtin_handlers
from app.execution.registry import NodeRegistry


def create_default_registry() -> NodeRegistry:
    """Create a registry containing the built-in workflow node handlers."""
    return NodeRegistry(builtin_handlers())
