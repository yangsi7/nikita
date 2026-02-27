"""Database connection utilities with optimized pooling.

T11: Connection Pooling Configuration
- pool_size=5, max_overflow=15 (total max 20)
- pool_timeout=30 seconds
- pool_recycle=1800 seconds
- pool_pre_ping=True (validate connections)
"""

import logging
from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import AsyncAdaptedQueuePool
from supabase import AsyncClient, create_async_client

from nikita.config.settings import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def get_async_engine():
    """Create async SQLAlchemy engine with optimized pooling.

    Pool configuration (AC-T11.1 through AC-T11.4):
    - pool_size: 5 base connections
    - max_overflow: 15 additional connections (total max 20)
    - pool_timeout: 30 seconds to wait for connection
    - pool_recycle: 1800 seconds (30 min) connection lifetime
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
        # AC-T11.3: pool_recycle=1800 seconds
        pool_recycle=1800,
        # AC-T11.4: pool_pre_ping=True (validate connections)
        pool_pre_ping=True,
        # GH #49: Ensure connections returned to pool are clean
        pool_reset_on_return="rollback",
        # Use async-adapted queue pool
        poolclass=AsyncAdaptedQueuePool,
        # Fix: Disable asyncpg prepared statement cache for Supavisor compatibility
        connect_args={
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
        },
    )

    # Fix: Send ROLLBACK on every connection checkout to clean dirty Supavisor
    # backend connections. Supavisor (Supabase's connection pooler) may hand out
    # backend PostgreSQL connections with aborted transactions from prior clients.
    @event.listens_for(engine.sync_engine, "connect")
    def _on_connect(dbapi_connection, connection_record):
        """Send ROLLBACK when a new raw connection is established."""
        # asyncpg connections need special handling - we use the cursor
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("ROLLBACK")
            cursor.execute(f"SET statement_timeout = '{settings.db_statement_timeout_ms}ms'")
            cursor.close()
        except Exception as e:
            logger.warning("[DB] Connection init ROLLBACK failed (ok if clean): %s", e)

    @event.listens_for(engine.sync_engine, "checkout")
    def _on_checkout(dbapi_connection, connection_record, connection_proxy):
        """Send ROLLBACK and set statement_timeout when a connection is checked out."""
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("ROLLBACK")
            cursor.execute(f"SET statement_timeout = '{settings.db_statement_timeout_ms}ms'")
            cursor.close()
        except Exception as e:
            logger.warning("[DB] Checkout ROLLBACK failed: %s", e)

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
