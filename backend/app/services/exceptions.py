class WorkflowAlreadyExistsError(Exception):
    """Raised when a workflow version already exists."""

class WorkflowNotFoundError(Exception):
    """Raised when a workflow version does not exist."""

class ArchivedWorkflowError(Exception):
    """Raised when an archived workflow cannot be activated."""

class EventAlreadyExistsError(Exception):
    """Raised when an event has already been received."""