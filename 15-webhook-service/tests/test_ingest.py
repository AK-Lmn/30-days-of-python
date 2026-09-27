import json
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from hookrelay.models.endpoint import Endpoint
from hookrelay.security.signer import compute_hmac_sha256
from hookrelay.security.verifier import WebhookVerificationError
from hookrelay.services.event_service import EventService


@pytest.mark.asyncio
async def test_ingest_event_success(
    db_session: AsyncSession,
    test_endpoint: Endpoint,
):
    body = b'{"order_id": 999, "amount": 49.99}'
    hex_sig = compute_hmac_sha256(body, test_endpoint.secret)

    headers = {
        "x-signature": hex_sig,
        "x-event-type": "order.created",
        "idempotency-key": "idemp-001",
    }

    event, count, is_dup = await EventService.ingest_event(
        db=db_session,
        endpoint=test_endpoint,
        raw_body=body,
        headers=headers,
    )

    assert is_dup is False
    assert event.id.startswith("evt_")
    assert event.event_type == "order.created"
    assert event.idempotency_key == "idemp-001"
    assert event.payload["order_id"] == 999
    assert event.status == "processed"


@pytest.mark.asyncio
async def test_ingest_event_invalid_signature_raises(
    db_session: AsyncSession,
    test_endpoint: Endpoint,
):
    body = b'{"order_id": 999}'
    headers = {
        "x-signature": "invalid_hex_string",
        "x-event-type": "order.created",
    }

    with pytest.raises(WebhookVerificationError):
        await EventService.ingest_event(
            db=db_session,
            endpoint=test_endpoint,
            raw_body=body,
            headers=headers,
        )


@pytest.mark.asyncio
async def test_ingest_event_duplicate_idempotency(
    db_session: AsyncSession,
    test_endpoint: Endpoint,
):
    body = b'{"order_id": 888}'
    hex_sig = compute_hmac_sha256(body, test_endpoint.secret)
    headers = {
        "x-signature": hex_sig,
        "x-event-type": "order.completed",
        "idempotency-key": "dup-key-123",
    }

    event1, _, is_dup1 = await EventService.ingest_event(
        db=db_session,
        endpoint=test_endpoint,
        raw_body=body,
        headers=headers,
    )
    assert is_dup1 is False

    event2, _, is_dup2 = await EventService.ingest_event(
        db=db_session,
        endpoint=test_endpoint,
        raw_body=body,
        headers=headers,
    )
    assert is_dup2 is True
    assert event2.id == event1.id


@pytest.mark.asyncio
async def test_extract_event_type_fallback(
    db_session: AsyncSession,
    test_endpoint: Endpoint,
):
    test_endpoint.verification_strategy = "none"
    await db_session.flush()

    body = b'{"type": "user.signup", "id": "user_42"}'
    headers = {}

    event, _, _ = await EventService.ingest_event(
        db=db_session,
        endpoint=test_endpoint,
        raw_body=body,
        headers=headers,
    )

    assert event.event_type == "user.signup"
    assert event.idempotency_key == "user_42"
