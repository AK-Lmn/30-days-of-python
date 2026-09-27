from collections.abc import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from hookrelay.api.app import create_app
from hookrelay.api.deps import get_db
from hookrelay.database import Base
from hookrelay.models.endpoint import Endpoint
from hookrelay.models.subscription import Subscription
from hookrelay.schemas.endpoint import EndpointCreate
from hookrelay.schemas.subscription import SubscriptionCreate
from hookrelay.services.endpoint_service import EndpointService
from hookrelay.services.subscription_service import SubscriptionService

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def test_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session_factory(test_engine):
    return async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


@pytest_asyncio.fixture
async def db_session(test_session_factory) -> AsyncGenerator[AsyncSession, None]:
    async with test_session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def test_endpoint(db_session: AsyncSession) -> Endpoint:
    data = EndpointCreate(
        slug="test-webhook",
        name="Test Ingest Endpoint",
        secret="test_secret_key_123",
        verification_strategy="hmac_sha256",
        description="Endpoint for testing",
    )
    endpoint = await EndpointService.create(db_session, data)
    await db_session.commit()
    return endpoint


@pytest_asyncio.fixture
async def test_subscription(db_session: AsyncSession) -> Subscription:
    data = SubscriptionCreate(
        name="Test Destination",
        target_url="https://example.com/webhook",
        secret_token="sub_secret_token_abc",
        event_patterns=["order.*", "payment.*"],
        max_retries=3,
        backoff_base_seconds=1.0,
        timeout_seconds=5.0,
    )
    sub = await SubscriptionService.create(db_session, data)
    await db_session.commit()
    return sub


@pytest_asyncio.fixture
async def app_instance(test_session_factory):
    app = create_app()

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with test_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    yield app
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def api_client(app_instance) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app_instance)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
