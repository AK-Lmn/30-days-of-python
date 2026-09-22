from typing import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool
from nexuspg.db.base import Base
from nexuspg.dependencies import get_db
from nexuspg.main import create_app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def test_engine() -> AsyncEngine:
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


@pytest.fixture(scope="session")
def test_session_factory(test_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


@pytest_asyncio.fixture(autouse=True)
async def setup_database(test_engine: AsyncEngine):
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(
    test_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    async with test_session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(
    test_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncClient, None]:
    app = create_app()

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with test_session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c
