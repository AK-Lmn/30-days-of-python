from typing import AsyncGenerator
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from nexuspg.core.config import settings
from nexuspg.db.base import Base


def build_engine(database_url: str) -> AsyncEngine:
    if "sqlite" in database_url:
        engine = create_async_engine(
            database_url,
            echo=settings.echo_sql,
            connect_args={"check_same_thread": False},
        )

        @event.listens_for(engine.sync_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        return engine

    return create_async_engine(
        database_url,
        echo=settings.echo_sql,
        pool_size=settings.pool_size,
        max_overflow=settings.max_overflow,
        pool_pre_ping=True,
    )


engine: AsyncEngine = build_engine(settings.database_url)

async_session_maker: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


def reset_engine(database_url: str) -> None:
    global engine, async_session_maker
    engine = build_engine(database_url)
    async_session_maker = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
