from pymongo import ASCENDING

from app.db.mongodb import get_database
from app.schemas.event import Event


class EventRepository:
    def __init__(self, database=None):
        self.database = (
            database
            if database is not None
            else get_database()
        )
        self.collection = self.database["events"]

    def create(self, event: Event) -> str:
        document = event.model_dump(mode="json")

        self.collection.insert_one(document)

        return event.event_id

    def get_by_id(self, event_id: str) -> Event | None:
        document = self.collection.find_one(
            {"event_id": event_id}
        )

        if document is None:
            return None

        document.pop("_id", None)

        return Event(**document)

    def create_indexes(self):
        self.collection.create_index(
            [("event_id", ASCENDING)],
            unique=True,
            name="event_id_unique",
        )
