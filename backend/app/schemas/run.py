from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class RunStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD_LETTER = "dead_letter"


class WorkflowRun(BaseModel):
    run_id: str
    workflow_id: str
    workflow_version: int
    event_id: str
    status: RunStatus
    created_at: datetime
    updated_at: datetime