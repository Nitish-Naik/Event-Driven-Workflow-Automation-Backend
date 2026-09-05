class WorkflowAlreadyExistsError(Exception):
    """Raised when a workflow version already exists."""

class WorkflowNotFoundError(Exception):
    """Raised when a workflow version does not exist."""

class ArchivedWorkflowError(Exception):
    """Raised when an archived workflow cannot be activated."""