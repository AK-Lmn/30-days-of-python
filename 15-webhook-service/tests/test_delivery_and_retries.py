from datetime import datetime, timedelta, timezone
import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from hookrelay.models.delivery import Delivery
from hookrelay.models.endpoint import Endpoint
from hookrelay.models.subscription import Subscription
from hookrelay.security.signer import compute_hmac_sha256
from hookrelay.services.delivery_service import DeliveryService
from hookrelay.services.event_service import EventService


@pytest.mark.asyncio
async def test_successful_delivery_attempt(
    db_session: AsyncSession,
    test_endpoint: Endpoint,
    test_subscription: Subscription,
):
    body = b'{"order_id": 1001}'
    sig = compute_hmac_sha256(body, test_endpoint.secret)
    headers = {"x-signature": sig, "x-event-type": "order.created"}

    def handler(request: httpx.Request) -> httpx.Response:
        assert "X-HookRelay-Signature" in request.headers
        assert "X-HookRelay-Event-Id" in request.headers
        assert "X-HookRelay-Delivery-Id" in request.headers
        return httpx.Response(200, json={"received": True})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as mock_client:
        event, count, _ = await EventService.ingest_event(
            db=db_session,
            endpoint=test_endpoint,
            raw_body=body,
            headers=headers,
            client=mock_client,
        )

    assert count == 1
    deliveries = await DeliveryService.list_all(db_session, event_id=event.id)
    assert len(deliveries) == 1
    d = await DeliveryService.get_by_id(db_session, deliveries[0].id)
    assert d.status == "success"
    assert d.attempts_count == 1
    assert len(d.attempts) == 1
    assert d.attempts[0].status_code == 200
    assert d.attempts[0].status == "success"


@pytest.mark.asyncio
async def test_client_error_delivery_not_retried(
    db_session: AsyncSession,
    test_endpoint: Endpoint,
    test_subscription: Subscription,
):
    body = b'{"order_id": 1002}'
    sig = compute_hmac_sha256(body, test_endpoint.secret)
    headers = {"x-signature": sig, "x-event-type": "order.created"}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "bad request"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as mock_client:
        event, _, _ = await EventService.ingest_event(
            db=db_session,
            endpoint=test_endpoint,
            raw_body=body,
            headers=headers,
            client=mock_client,
        )

    deliveries = await DeliveryService.list_all(db_session, event_id=event.id)
    d = await DeliveryService.get_by_id(db_session, deliveries[0].id)
    assert d.status == "failed"
    assert d.next_retry_at is None
    assert d.attempts[0].status_code == 400


@pytest.mark.asyncio
async def test_server_error_triggers_exponential_backoff_and_dlq(
    db_session: AsyncSession,
    test_endpoint: Endpoint,
    test_subscription: Subscription,
):
    test_subscription.max_retries = 2
    test_subscription.backoff_base_seconds = 5.0
    await db_session.flush()

    body = b'{"order_id": 1003}'
    sig = compute_hmac_sha256(body, test_endpoint.secret)
    headers = {"x-signature": sig, "x-event-type": "order.created"}

    def fail_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal server error")

    async with httpx.AsyncClient(transport=httpx.MockTransport(fail_handler)) as mock_client:
        event, _, _ = await EventService.ingest_event(
            db=db_session,
            endpoint=test_endpoint,
            raw_body=body,
            headers=headers,
            client=mock_client,
        )

        deliveries = await DeliveryService.list_all(db_session, event_id=event.id)
        d = await DeliveryService.get_by_id(db_session, deliveries[0].id)
        assert d.status == "pending"
        assert d.attempts_count == 1
        assert d.next_retry_at is not None

        d2 = await DeliveryService.execute_delivery(db_session, d, client=mock_client)
        assert d2.status == "pending"
        assert d2.attempts_count == 2
        assert d2.next_retry_at is not None

        d3 = await DeliveryService.execute_delivery(db_session, d2, client=mock_client)
        assert d3.status == "dlq"
        assert d3.attempts_count == 3
        assert d3.next_retry_at is None


@pytest.mark.asyncio
async def test_replay_delivery(
    db_session: AsyncSession,
    test_endpoint: Endpoint,
    test_subscription: Subscription,
):
    body = b'{"order_id": 1004}'
    sig = compute_hmac_sha256(body, test_endpoint.secret)
    headers = {"x-signature": sig, "x-event-type": "order.created"}

    def fail_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="Service Unavailable")

    async with httpx.AsyncClient(transport=httpx.MockTransport(fail_handler)) as mock_client:
        event, _, _ = await EventService.ingest_event(
            db=db_session,
            endpoint=test_endpoint,
            raw_body=body,
            headers=headers,
            client=mock_client,
        )

    deliveries = await DeliveryService.list_all(db_session, event_id=event.id)
    delivery_id = deliveries[0].id

    def ok_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"replayed": True})

    async with httpx.AsyncClient(transport=httpx.MockTransport(ok_handler)) as mock_client:
        replayed, attempt = await DeliveryService.replay_delivery(
            db_session, delivery_id, client=mock_client
        )

    assert replayed.status == "success"
    assert attempt.status_code == 200
    assert attempt.attempt_number == 2


@pytest.mark.asyncio
async def test_process_pending_retries(
    db_session: AsyncSession,
    test_endpoint: Endpoint,
    test_subscription: Subscription,
):
    body = b'{"order_id": 1005}'
    sig = compute_hmac_sha256(body, test_endpoint.secret)
    headers = {"x-signature": sig, "x-event-type": "order.created"}

    def fail_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, text="Bad Gateway")

    async with httpx.AsyncClient(transport=httpx.MockTransport(fail_handler)) as mock_client:
        event, _, _ = await EventService.ingest_event(
            db=db_session,
            endpoint=test_endpoint,
            raw_body=body,
            headers=headers,
            client=mock_client,
        )

    deliveries = await DeliveryService.list_all(db_session, event_id=event.id)
    d = await DeliveryService.get_by_id(db_session, deliveries[0].id)
    d.next_retry_at = datetime.now(timezone.utc) - timedelta(seconds=10)
    await db_session.flush()

    def ok_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True})

    async with httpx.AsyncClient(transport=httpx.MockTransport(ok_handler)) as mock_client:
        processed = await DeliveryService.process_pending_retries(
            db_session, client=mock_client
        )

    assert len(processed) >= 1
    d_after = await DeliveryService.get_by_id(db_session, d.id)
    assert d_after.status == "success"
