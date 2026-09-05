from pymongo.errors import DuplicateKeyError

from app.db.repositories.event import EventRepository
from app.schemas.event import Event
from app.services.exceptions import EventAlreadyExistsError


class EventService:
    def __init__(self, repository=None):
        self.repository = (
            repository
            if repository is not None
            else EventRepository()
        )

    def create_event(self, event: Event) -> str:
        try:
            return self.repository.create(event)
        except DuplicateKeyError as exc:
            raise EventAlreadyExistsError(
                f"Event already exists: {event.event_id}"
            ) from exc

    def get_event(
        self,
        event_id: str,
    ) -> Event | None:
        return self.repository.get_by_id(event_id)