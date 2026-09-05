from fastapi import APIRouter, Depends, status

from app.integrations.sentry import normalize_sentry_event
from app.services.event import EventService
from app.services.exceptions import EventAlreadyExistsError

router = APIRouter(
    prefix="/webhooks",
    tags=["webhooks"],
)


def get_event_service():
    return EventService()


@router.post(
    "/sentry",
    status_code=status.HTTP_202_ACCEPTED,
)
def receive_sentry_event(
    payload: dict,
    service: EventService = Depends(get_event_service),
):
    event = normalize_sentry_event(payload)

    try:
        event_id = service.create_event(event)
    except EventAlreadyExistsError:
        # Sentry may retry the same webhook.
        # Treat the duplicate as successfully received.
        return {
            "status": "duplicate",
            "event_id": event.event_id,
        }

    return {
        "status": "accepted",
        "event_id": event_id,
    }