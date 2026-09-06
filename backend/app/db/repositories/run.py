from datetime import datetime, timezone

from pymongo import ASCENDING

from app.db.mongodb import get_database
from app.schemas.run import RunStatus, WorkflowRun


class WorkflowRunRepository:
    def __init__(self, database=None):
        self.database = (
            database
            if database is not None
            else get_database()
        )
        self.collection = self.database["workflow_runs"]

    def create(self, run: WorkflowRun) -> str:
        document = run.model_dump(mode="json")
        result = self.collection.insert_one(document)
        return str(result.inserted_id)

    def get_by_id(self, run_id: str) -> WorkflowRun | None:
        document = self.collection.find_one(
            {"run_id": run_id}
        )

        if document is None:
            return None

        document.pop("_id", None)

        return WorkflowRun(**document)

    def update_status(
        self,
        run_id: str,
        status: RunStatus,
    ) -> bool:
        result = self.collection.update_one(
            {"run_id": run_id},
            {
                "$set": {
                    "status": status,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )

        return result.modified_count == 1

    def create_indexes(self):
        self.collection.create_index(
            [("run_id", ASCENDING)],
            unique=True,
            name="run_id_unique",
        )