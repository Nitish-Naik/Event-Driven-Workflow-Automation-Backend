from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.config import settings
from app.integrations.sentry import normalize_sentry_event
from app.security.sentry_webhook import (
    SENTRY_SIGNATURE_HEADER,
    verify_sentry_signature,
)
from app.services.event import EventService
from app.services.exceptions import EventAlreadyExistsError

from app.queue.event_queue import EventQueue

router = APIRouter(
    prefix="/webhooks",
    tags=["webhooks"],
)


def get_event_service():
    return EventService()


def get_event_queue():
    return EventQueue()


@router.post(
    "/sentry",
    status_code=status.HTTP_202_ACCEPTED,
)
async def receive_sentry_event(
    request: Request,
    service: EventService = Depends(get_event_service),
    queue: EventQueue = Depends(get_event_queue),
):
    raw_body = await request.body()

    if settings.sentry_webhook_secret:
        signature = request.headers.get(SENTRY_SIGNATURE_HEADER)
        if not verify_sentry_signature(
            settings.sentry_webhook_secret,
            raw_body,
            signature,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid Sentry webhook signature",
            )

    try:
        payload = await request.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        ) from exc

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sentry webhook payload must be an object",
        )

    event = normalize_sentry_event(payload)

    try:
        event_id = service.create_event(event)
    except EventAlreadyExistsError:
        return {
            "status": "duplicate",
            "event_id": event.event_id,
        }

    queue.enqueue(event.event_id)

    return {
        "status": "accepted",
        "event_id": event_id,
    }
