"""Database connection utilities with optimized pooling.

T11: Connection Pooling Configuration
- pool_size=5, max_overflow=10 (total max 15)
- pool_timeout=30 seconds
- pool_recycle=300 seconds (5 min — BKD-002: reduced from 1800 to minimise stale
  connections after Cloud Run scale-to-zero cold starts; slight overhead tradeoff
  for correctness on serverless)
- pool_pre_ping=True (validate connections)
"""

import logging
from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import AsyncAdaptedQueuePool
from supabase import AsyncClient, create_async_client

from nikita.config.settings import get_settings

logger = logging.getLogger(__name__)


def _build_connect_args(settings) -> dict:
    """Build asyncpg connect_args dict (factored for testability — GH #359).

    Returns:
        dict suitable for `connect_args=` kwarg of create_async_engine.
        Includes statement_cache disabling (Supavisor-required) plus
        server_settings.statement_timeout (replaces the greenlet-unsafe
        @event.listens_for sync cursor.execute("SET statement_timeout") block
        that was removed for GH #359).
    """
    return {
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
        "server_settings": {
            "statement_timeout": f"{settings.db_statement_timeout_ms}",
        },
    }


@lru_cache
def get_async_engine():
    """Create async SQLAlchemy engine with optimized pooling.

    Pool configuration (AC-T11.1 through AC-T11.4):
    - pool_size: 5 base connections
    - max_overflow: 10 additional connections (total max 15)
    - pool_timeout: 30 seconds to wait for connection
    - pool_recycle: 300 seconds (5 min) connection lifetime
    - pool_pre_ping: True to validate connections before use

    Returns:
        Configured AsyncEngine instance.
    """
    settings = get_settings()
    engine = create_async_engine(
        settings.database_url,
        echo=settings.debug,
        # AC-T11.1: pool_size=5, max_overflow=15 (total max 20)
        pool_size=5,
        max_overflow=10,
        # AC-T11.2: pool_timeout=30 seconds
        pool_timeout=30,
        # BKD-002: pool_recycle=300s (was 1800s); reduced to 5 min for scale-to-zero.
        # Cloud Run instances recycle after idle; 30-min connections would be stale.
        pool_recycle=300,
        # AC-T11.4: pool_pre_ping=True (validate connections)
        pool_pre_ping=True,
        # GH #49: Ensure connections returned to pool are clean
        pool_reset_on_return="rollback",
        # Use async-adapted queue pool
        poolclass=AsyncAdaptedQueuePool,
        # GH #359 fix: replaces sync cursor.execute() in @event.listens_for blocks
        # with asyncpg-native server_settings. Sync cursor calls inside async
        # connect/checkout listeners triggered `greenlet_spawn has not been called;
        # can't call await_only() here` during background-task DB writes (Walk M
        # 2026-04-19 09:48 UTC reproduction). pool_reset_on_return='rollback'
        # above already handles connection cleanup; the manual ROLLBACK was
        # redundant. statement_timeout via server_settings is set once at
        # asyncpg connection time (works under Supavisor session pooling).
        connect_args=_build_connect_args(settings),
    )

    return engine


@lru_cache
def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """Get async session maker.

    Returns:
        Configured async_sessionmaker instance.
    """
    engine = get_async_engine()
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database session.

    Yields:
        AsyncSession for database operations.
    """
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@lru_cache
def _get_supabase_sync_client():
    """Get cached Supabase sync client (for module-level use)."""
    settings = get_settings()
    return settings.supabase_url, settings.supabase_service_key


async def get_supabase_client() -> AsyncClient:
    """Get Supabase async client."""
    url, key = _get_supabase_sync_client()
    return await create_async_client(url, key)


def get_pool_status() -> dict:
    """Get connection pool status metrics (AC-T11.5).

    Returns:
        Dict with pool metrics (size, checked_in, checked_out, overflow).
    """
    engine = get_async_engine()
    pool = engine.pool
    return {
        "pool_size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "invalid": pool.invalidatedcount(),
    }
