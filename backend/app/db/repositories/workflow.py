from pymongo import ASCENDING

from app.db.mongodb import get_database
from app.schemas.workflow import Workflow


class WorkflowRepository:
    def __init__(self, database=None):
        self.database = database if database is not None else get_database()
        self.collection = self.database["workflows"]

    def create(self, workflow: Workflow) -> str:
        document = workflow.model_dump(mode="json")

        result = self.collection.insert_one(document)

        return str(result.inserted_id)

    def get_by_id(self, workflow_id: str, version: int) -> Workflow | None:
        document = self.collection.find_one(
            {
                "workflow_id": workflow_id,
                "version": version,
            }
        )

        if document is None:
            return None

        document.pop("_id", None)

        return Workflow(**document)

    def get_active(self, workflow_id: str) -> Workflow | None:
        document = self.collection.find_one(
            {
                "workflow_id": workflow_id,
                "status": "active",
            },
            sort=[("version", -1)],
        )

        if document is None:
            return None

        document.pop("_id", None)

        return Workflow(**document)

    def get_active_by_trigger(self, trigger: str) -> Workflow | None:
        document = self.collection.find_one(
            {
                "trigger": trigger,
                "status": "active",
            },
            sort=[("version", -1)],
        )

        if document is None:
            return None

        document.pop("_id", None)

        return Workflow(**document)

    def create_indexes(self):
        self.collection.create_index(
            [
                ("workflow_id", ASCENDING),
                ("version", ASCENDING),
            ],
            unique=True,
            name="workflow_version_unique",
        )

        self.collection.create_index(
            [
                ("workflow_id", ASCENDING),
                ("status", ASCENDING),
                ("version", ASCENDING),
            ],
            name="workflow_status_version",
        )

        self.collection.create_index(
            [("workflow_id", 1)],
            unique=True,
            partialFilterExpression={"status": "active"},
            name="workflow_active_unique",
        )

        self.collection.create_index(
            [("trigger", ASCENDING), ("status", ASCENDING)],
            name="workflow_trigger_status",
        )

    def update_status(
        self,
        workflow_id: str,
        version: int,
        status: str,
    ) -> bool:
        result = self.collection.update_one(
            {
                "workflow_id": workflow_id,
                "version": version,
            },
            {
                "$set": {"status": status},
            },
        )

        return result.modified_count == 1
