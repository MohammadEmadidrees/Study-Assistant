from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from app.core.config import settings
from app.core.logging import logger

class Base(DeclarativeBase):
    pass

primary_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.SQL_ECHO,
    future=True,
    pool_pre_ping=True,
)

fallback_engine = create_async_engine(
    "sqlite+aiosqlite:///./study_assistant.db",
    echo=settings.SQL_ECHO,
    future=True,
)

# Export default engine reference
engine = primary_engine
_active_engine = None
_session_factory = None


def get_engine():
    global _active_engine
    if _active_engine is not None:
        return _active_engine
    return fallback_engine if "sqlite" in settings.DATABASE_URL else primary_engine


def get_session_factory():
    global _session_factory
    if _session_factory is not None:
        return _session_factory
    _session_factory = async_sessionmaker(
        bind=get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    return _session_factory


class _AsyncSessionLocalProxy:
    """Proxy object so `AsyncSessionLocal()` always uses the active engine."""
    def __call__(self, *args, **kwargs) -> AsyncSession:
        factory = get_session_factory()
        return factory(*args, **kwargs)


AsyncSessionLocal = _AsyncSessionLocalProxy()


async def init_db() -> None:
    """Create database tables if they do not exist, falling back to SQLite if Postgres is unavailable."""
    global _active_engine, _session_factory
    try:
        async with primary_engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
            await conn.run_sync(Base.metadata.create_all)
        _active_engine = primary_engine
        logger.info(f"Database initialized successfully with primary engine: {settings.DATABASE_URL}")
    except Exception as exc:
        logger.warning(
            f"Could not connect to primary database ({exc}). "
            "Falling back to local SQLite (aiosqlite) for development."
        )
        _active_engine = fallback_engine
        async with fallback_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized successfully with fallback SQLite.")

    # Reset session factory to active engine
    _session_factory = async_sessionmaker(
        bind=_active_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI Dependency for obtaining an async database session."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
