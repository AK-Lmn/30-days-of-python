import json
import time
from datetime import datetime, timedelta, timezone
from typing import Sequence
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from hookrelay.models.delivery import Delivery, DeliveryAttempt
from hookrelay.models.event import WebhookEvent
from hookrelay.models.subscription import Subscription
from hookrelay.security.signer import sign_payload
from hookrelay.services.subscription_service import SubscriptionService


class DeliveryService:
    @staticmethod
    async def create_deliveries_for_event(
        db: AsyncSession,
        event: WebhookEvent,
    ) -> list[Delivery]:
        matched_subs = await SubscriptionService.get_matching_subscriptions(
            db, event.event_type
        )
        deliveries: list[Delivery] = []
        for sub in matched_subs:
            delivery = Delivery(
                event_id=event.id,
                subscription_id=sub.id,
                status="pending",
                max_retries=sub.max_retries,
            )
            db.add(delivery)
            deliveries.append(delivery)
        await db.flush()
        return deliveries

    @classmethod
    async def execute_delivery(
        cls,
        db: AsyncSession,
        delivery: Delivery,
        client: httpx.AsyncClient | None = None,
    ) -> Delivery:
        await db.refresh(delivery, ["event", "subscription"])
        sub = delivery.subscription
        event = delivery.event

        delivery.status = "delivering"
        delivery.attempts_count += 1
        now_utc = datetime.now(timezone.utc)
        delivery.last_attempt_at = now_utc
        await db.flush()

        raw_payload = event.raw_body.encode("utf-8")
        headers = sign_payload(
            raw_body=raw_payload,
            secret=sub.secret_token,
            event_id=event.id,
            delivery_id=delivery.id,
        )

        should_close_client = False
        if client is None:
            client = httpx.AsyncClient(timeout=sub.timeout_seconds)
            should_close_client = True

        status_code: int | None = None
        resp_headers: dict[str, str] | None = None
        resp_body: str | None = None
        error_message: str | None = None
        attempt_status = "failed"
        start_time = time.perf_counter()

        try:
            response = await client.post(
                sub.target_url,
                content=raw_payload,
                headers=headers,
            )
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            status_code = response.status_code
            resp_headers = dict(response.headers)
            resp_body = response.text[:2048]

            if 200 <= status_code < 300:
                attempt_status = "success"
                delivery.status = "success"
                delivery.next_retry_at = None
            elif 400 <= status_code < 500:
                attempt_status = "failed"
                delivery.status = "failed"
                delivery.next_retry_at = None
                error_message = f"Client error response: HTTP {status_code}"
            else:
                attempt_status = "failed"
                error_message = f"Server error response: HTTP {status_code}"
                cls._handle_retry(delivery, sub, now_utc)

        except (httpx.TimeoutException, httpx.ConnectTimeout):
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            attempt_status = "timeout"
            error_message = "Delivery timed out"
            cls._handle_retry(delivery, sub, now_utc)
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            attempt_status = "failed"
            error_message = str(exc)
            cls._handle_retry(delivery, sub, now_utc)
        finally:
            if should_close_client:
                await client.aclose()

        attempt = DeliveryAttempt(
            delivery_id=delivery.id,
            attempt_number=delivery.attempts_count,
            status_code=status_code,
            request_headers=headers,
            request_body=event.raw_body,
            response_headers=resp_headers,
            response_body=resp_body,
            duration_ms=duration_ms,
            status=attempt_status,
            error_message=error_message,
        )
        db.add(attempt)
        delivery.updated_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(delivery)
        return delivery

    @staticmethod
    def _handle_retry(
        delivery: Delivery,
        subscription: Subscription,
        reference_time: datetime,
    ) -> None:
        if delivery.attempts_count <= delivery.max_retries:
            backoff = subscription.backoff_base_seconds * (
                2 ** (delivery.attempts_count - 1)
            )
            delivery.next_retry_at = reference_time + timedelta(seconds=backoff)
            delivery.status = "pending"
        else:
            delivery.next_retry_at = None
            delivery.status = "dlq"

    @classmethod
    async def replay_delivery(
        cls,
        db: AsyncSession,
        delivery_id: str,
        client: httpx.AsyncClient | None = None,
    ) -> tuple[Delivery, DeliveryAttempt]:
        delivery = await cls.get_by_id(db, delivery_id)
        if not delivery:
            raise ValueError(f"Delivery {delivery_id} not found")

        delivery.status = "pending"
        delivery.next_retry_at = None
        await db.flush()

        updated_delivery = await cls.execute_delivery(db, delivery, client=client)
        latest_attempt_result = await db.execute(
            select(DeliveryAttempt)
            .where(DeliveryAttempt.delivery_id == delivery.id)
            .order_by(DeliveryAttempt.attempt_number.desc())
        )
        latest_attempt = latest_attempt_result.scalars().first()
        return updated_delivery, latest_attempt

    @staticmethod
    async def get_by_id(db: AsyncSession, delivery_id: str) -> Delivery | None:
        result = await db.execute(
            select(Delivery)
            .options(selectinload(Delivery.attempts), selectinload(Delivery.subscription), selectinload(Delivery.event))
            .where(Delivery.id == delivery_id)
        )
        return result.scalars().first()

    @staticmethod
    async def list_all(
        db: AsyncSession,
        status: str | None = None,
        event_id: str | None = None,
        subscription_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Delivery]:
        stmt = select(Delivery)
        if status:
            stmt = stmt.where(Delivery.status == status)
        if event_id:
            stmt = stmt.where(Delivery.event_id == event_id)
        if subscription_id:
            stmt = stmt.where(Delivery.subscription_id == subscription_id)
        stmt = stmt.order_by(Delivery.created_at.desc()).limit(limit).offset(offset)
        result = await db.execute(stmt)
        return result.scalars().all()

    @classmethod
    async def process_pending_retries(
        cls,
        db: AsyncSession,
        now: datetime | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> list[Delivery]:
        current_time = now or datetime.now(timezone.utc)
        stmt = (
            select(Delivery)
            .where(
                Delivery.status == "pending",
                Delivery.next_retry_at.is_not(None),
                Delivery.next_retry_at <= current_time,
            )
            .order_by(Delivery.next_retry_at.asc())
        )
        result = await db.execute(stmt)
        pending_deliveries = list(result.scalars().all())

        processed: list[Delivery] = []
        for delivery in pending_deliveries:
            executed = await cls.execute_delivery(db, delivery, client=client)
            processed.append(executed)
        return processed
