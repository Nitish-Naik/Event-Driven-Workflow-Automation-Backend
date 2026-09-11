from pydantic import BaseModel, Field


class SendSlackMessageInput(BaseModel):
    channel: str = Field(min_length=1)
    text: str = Field(min_length=1)
