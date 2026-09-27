from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from hookrelay.api.deps import get_db
from hookrelay.schemas.event import EventIngestResponse
from hookrelay.security.verifier import WebhookVerificationError
from hookrelay.services.endpoint_service import EndpointService
from hookrelay.services.event_service import EventService

router = APIRouter(prefix="/api/v1/ingest", tags=["Ingestion"])


@router.post(
    "/{slug}",
    response_model=EventIngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def ingest_webhook(
    slug: str,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> EventIngestResponse:
    endpoint = await EndpointService.get_by_slug(db, slug)
    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Endpoint with slug '{slug}' not found",
        )

    if not endpoint.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Endpoint is inactive",
        )

    raw_body = await request.body()
    headers = dict(request.headers)

    try:
        event, scheduled_count, is_duplicate = await EventService.ingest_event(
            db=db,
            endpoint=endpoint,
            raw_body=raw_body,
            headers=headers,
        )
    except WebhookVerificationError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.message,
        )

    if is_duplicate:
        response.status_code = status.HTTP_200_OK
        return EventIngestResponse(
            event_id=event.id,
            status=event.status,
            event_type=event.event_type,
            deliveries_scheduled=scheduled_count,
            is_duplicate=True,
            message="Event with this idempotency key was already received and processed",
        )

    return EventIngestResponse(
        event_id=event.id,
        status=event.status,
        event_type=event.event_type,
        deliveries_scheduled=scheduled_count,
        is_duplicate=False,
        message="Event accepted and deliveries scheduled",
    )
