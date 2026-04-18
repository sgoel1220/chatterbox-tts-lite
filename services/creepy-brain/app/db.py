"""Database connection and session management."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

# Global engine and session maker
engine: AsyncEngine | None = None
async_session_maker: async_sessionmaker[AsyncSession] | None = None


async def init_db() -> None:
    """Initialize database engine and session maker."""
    global engine, async_session_maker

    engine = create_async_engine(
        settings.database_url,
        echo=settings.db_echo,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )

    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def close_db() -> None:
    """Close database connections."""
    global engine
    if engine:
        await engine.dispose()


async def get_session() -> AsyncIterator[AsyncSession]:
    """Get async database session. Use as FastAPI dependency."""
    if async_session_maker is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    async with async_session_maker() as session:
        yield session


# FastAPI dependency alias for clean route signatures
DbSession = Annotated[AsyncSession, Depends(get_session)]
