import json
from typing import Any, Sequence
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from hookrelay.models.endpoint import Endpoint
from hookrelay.models.event import WebhookEvent
from hookrelay.security.verifier import verify_endpoint_signature
from hookrelay.services.delivery_service import DeliveryService


class EventService:
    @classmethod
    async def ingest_event(
        cls,
        db: AsyncSession,
        endpoint: Endpoint,
        raw_body: bytes,
        headers: dict[str, Any],
        client: httpx.AsyncClient | None = None,
    ) -> tuple[WebhookEvent, int, bool]:
        verify_endpoint_signature(
            strategy=endpoint.verification_strategy,
            secret=endpoint.secret,
            raw_body=raw_body,
            headers=headers,
        )

        raw_text = raw_body.decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw_text) if raw_text else {}
        except Exception:
            payload = {"raw": raw_text}

        idempotency_key = cls._extract_idempotency_key(headers, payload)
        if idempotency_key:
            existing = await cls.find_by_idempotency(db, endpoint.id, idempotency_key)
            if existing:
                deliveries = await DeliveryService.list_all(db, event_id=existing.id)
                return existing, len(deliveries), True

        event_type = cls._extract_event_type(headers, payload)

        event = WebhookEvent(
            endpoint_id=endpoint.id,
            event_type=event_type,
            idempotency_key=idempotency_key,
            payload=payload if isinstance(payload, dict) else {"data": payload},
            raw_body=raw_text,
            headers={str(k): str(v) for k, v in headers.items()},
            status="received",
        )
        db.add(event)
        await db.flush()
        await db.refresh(event)

        deliveries = await DeliveryService.create_deliveries_for_event(db, event)
        for delivery in deliveries:
            await DeliveryService.execute_delivery(db, delivery, client=client)

        event.status = "processed"
        await db.flush()
        await db.refresh(event)

        return event, len(deliveries), False

    @staticmethod
    def _extract_idempotency_key(
        headers: dict[str, Any],
        payload: Any,
    ) -> str | None:
        normalized = {k.lower(): str(v) for k, v in headers.items()}
        for key in ["idempotency-key", "x-idempotency-key", "x-github-delivery"]:
            if key in normalized and normalized[key].strip():
                return normalized[key].strip()

        if isinstance(payload, dict):
            if "idempotency_key" in payload and payload["idempotency_key"]:
                return str(payload["idempotency_key"]).strip()
            if "id" in payload and payload["id"] and isinstance(payload["id"], (str, int)):
                return str(payload["id"]).strip()

        return None

    @staticmethod
    def _extract_event_type(
        headers: dict[str, Any],
        payload: Any,
    ) -> str:
        normalized = {k.lower(): str(v) for k, v in headers.items()}
        for header_key in ["x-github-event", "x-event-type", "x-event"]:
            if header_key in normalized and normalized[header_key].strip():
                return normalized[header_key].strip()

        if isinstance(payload, dict):
            for payload_key in ["event_type", "event", "type", "action"]:
                if payload_key in payload and payload[payload_key]:
                    return str(payload[payload_key]).strip()

        return "default"

    @staticmethod
    async def find_by_idempotency(
        db: AsyncSession,
        endpoint_id: str,
        idempotency_key: str,
    ) -> WebhookEvent | None:
        result = await db.execute(
            select(WebhookEvent).where(
                WebhookEvent.endpoint_id == endpoint_id,
                WebhookEvent.idempotency_key == idempotency_key,
            )
        )
        return result.scalars().first()

    @staticmethod
    async def get_by_id(db: AsyncSession, event_id: str) -> WebhookEvent | None:
        result = await db.execute(
            select(WebhookEvent)
            .options(selectinload(WebhookEvent.deliveries))
            .where(WebhookEvent.id == event_id)
        )
        return result.scalars().first()

    @staticmethod
    async def list_all(
        db: AsyncSession,
        endpoint_id: str | None = None,
        event_type: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[WebhookEvent]:
        stmt = select(WebhookEvent)
        if endpoint_id:
            stmt = stmt.where(WebhookEvent.endpoint_id == endpoint_id)
        if event_type:
            stmt = stmt.where(WebhookEvent.event_type == event_type)
        if status:
            stmt = stmt.where(WebhookEvent.status == status)
        stmt = stmt.order_by(WebhookEvent.created_at.desc()).limit(limit).offset(offset)
        result = await db.execute(stmt)
        return result.scalars().all()
