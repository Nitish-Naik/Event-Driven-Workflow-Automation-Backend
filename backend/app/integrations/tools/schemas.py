from pydantic import BaseModel

class GetIssueInput(BaseModel):
    issue_id: str