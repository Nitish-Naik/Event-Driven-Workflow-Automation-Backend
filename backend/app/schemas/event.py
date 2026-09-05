from datetime import datetime

from pydantic import BaseModel, Field

class Event(BaseModel):
    event_id: str
    source: str
    event_type: str

    payload: dict = Field(default_factory=dict)

    received_at: datetime