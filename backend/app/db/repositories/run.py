from datetime import datetime, timezone
from typing import Any

from pymongo import ASCENDING
from pymongo.errors import DuplicateKeyError

from app.db.mongodb import get_database
from app.schemas.run import RunStatus, WorkflowRun


class WorkflowRunRepository:
    ALLOWED_TRANSITIONS = {
        RunStatus.QUEUED: {RunStatus.PROCESSING},
        RunStatus.PROCESSING: {RunStatus.COMPLETED, RunStatus.FAILED},
        RunStatus.FAILED: {RunStatus.RETRYING, RunStatus.DEAD_LETTER},
        RunStatus.RETRYING: {RunStatus.PROCESSING},
        RunStatus.COMPLETED: set(),
        RunStatus.DEAD_LETTER: set(),
    }

    def __init__(self, database=None):
        self.database = database if database is not None else get_database()
        self.collection = self.database["workflow_runs"]

    def create(self, run: WorkflowRun) -> str:
        document = run.model_dump(mode="json")
        result = self.collection.insert_one(document)
        return run.run_id if result.inserted_id is not None else run.run_id

    def get_by_id(self, run_id: str) -> WorkflowRun | None:
        document = self.collection.find_one({"run_id": run_id})
        if document is None:
            return None
        document.pop("_id", None)
        return WorkflowRun(**document)

    def get_by_execution_key(self, execution_key: str) -> WorkflowRun | None:
        document = self.collection.find_one({"execution_key": execution_key})
        if document is None:
            return None
        document.pop("_id", None)
        return WorkflowRun(**document)

    def update_status(self, run_id: str, status: RunStatus) -> bool:
        current = self.get_by_id(run_id)
        if current is None:
            return False

        allowed = self.ALLOWED_TRANSITIONS[current.status]
        if status not in allowed:
            raise ValueError(
                f"Invalid workflow run transition: "
                f"{current.status} -> {status}"
            )

        result = self.collection.update_one(
            {"run_id": run_id, "status": current.status},
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
        self.collection.create_index(
            [("execution_key", ASCENDING)],
            unique=True,
            partialFilterExpression={"execution_key": {"$type": "string"}},
            name="execution_key_unique",
        )

    def update_retry_metadata(
        self,
        run_id: str,
        attempt: int,
        last_error: str,
    ) -> bool:
        result = self.collection.update_one(
            {"run_id": run_id},
            {
                "$set": {
                    "attempt": attempt,
                    "last_error": last_error,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        return result.modified_count == 1

    def update_outputs(self, run_id: str, outputs: dict[str, Any]) -> bool:
        result = self.collection.update_one(
            {"run_id": run_id},
            {
                "$set": {
                    "outputs": outputs,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        return result.modified_count == 1
