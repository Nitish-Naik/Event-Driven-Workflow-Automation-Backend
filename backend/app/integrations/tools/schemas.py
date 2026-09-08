from pydantic import BaseModel

class GetIssueInput(BaseModel):
    issue_id: str

class GetIssueEventsInput(BaseModel):
    issue_id: str