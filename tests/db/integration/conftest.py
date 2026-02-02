"""Fixtures for database integration tests.

T14: Integration Tests
- AC-T14.1: Integration tests use test Supabase project

CONNECTION OPTIONS:
1. DATABASE_URL_POOLER: Session Pooler (for local IPv4 development)
   - Enable in Supabase Dashboard > Database > Connection Pooler
   - Get connection string from Dashboard > Settings > Database
   - Format: postgresql+asyncpg://postgres.PROJECT_REF:PASSWORD@aws-0-REGION.pooler.supabase.com:5432/postgres

2. DATABASE_URL: Direct connection (for Cloud Run/CI with IPv6)
   - Format: postgresql+asyncpg://postgres:PASSWORD@db.PROJECT_REF.supabase.co:5432/postgres
"""

import logging
import os
import socket
import time
from urllib.parse import urlparse

# Load environment variables from .env file
from dotenv import load_dotenv

load_dotenv()
from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Configure logging for test discovery
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _get_database_url() -> str | None:
    """Get the best available database URL.

    Priority:
    1. DATABASE_URL_LOCAL (local Supabase via `supabase start`)
    2. DATABASE_URL_POOLER (Session Pooler for remote without IPv6)
    3. DATABASE_URL (direct connection for Cloud Run/CI with IPv6)
    """
    local_url = os.getenv("DATABASE_URL_LOCAL")
    if local_url:
        logger.info("Using DATABASE_URL_LOCAL (local Supabase)")
        return local_url

    pooler_url = os.getenv("DATABASE_URL_POOLER")
    if pooler_url:
        logger.info("Using DATABASE_URL_POOLER (Session Pooler)")
        return pooler_url

    direct_url = os.getenv("DATABASE_URL")
    if direct_url:
        logger.info("Using DATABASE_URL (direct connection)")
        return direct_url

    return None


def can_reach_database(max_retries: int = 2) -> tuple[bool, str]:
    """Check if database is reachable via socket with retry logic.

    Returns:
        Tuple of (is_reachable, skip_reason)
    """
    database_url = _get_database_url()
    if not database_url:
        return False, (
            "DATABASE_URL not set. For local development, enable Session Pooler:\n"
            "  1. Go to Supabase Dashboard > Database > Connection Pooler\n"
            "  2. Enable 'Session Mode' pooler\n"
            "  3. Copy the connection string to DATABASE_URL_POOLER in .env\n"
            "  Format: postgresql+asyncpg://postgres.PROJECT:PASS@aws-0-REGION.pooler.supabase.com:5432/postgres"
        )

    try:
        # Parse hostname from DATABASE_URL (handle +asyncpg suffix)
        parsed = urlparse(database_url.replace("+asyncpg", ""))
        host = parsed.hostname
        port = parsed.port or 5432

        if not host:
            return False, "Could not parse hostname from DATABASE_URL"

        logger.info(f"Testing connectivity to {host}:{port}")

    except Exception as e:
        return False, f"Failed to parse DATABASE_URL: {e}"

    for attempt in range(max_retries):
        try:
            # Use getaddrinfo to support both IPv4 and IPv6
            addr_info_list = socket.getaddrinfo(
                host, port, socket.AF_UNSPEC, socket.SOCK_STREAM
            )

            # Try each address until one works
            for family, socktype, proto, canonname, sockaddr in addr_info_list:
                try:
                    sock = socket.socket(family, socktype, proto)
                    sock.settimeout(3.0)
                    result = sock.connect_ex(sockaddr)
                    sock.close()

                    if result == 0:
                        logger.info(
                            f"Connected to {host}:{port} via {sockaddr[0]} (attempt {attempt + 1})"
                        )
                        return True, ""
                except Exception as inner_e:
                    logger.debug(f"Failed to connect via {sockaddr}: {inner_e}")
                    continue

            # None of the addresses worked, wait before retry
            if attempt < max_retries - 1:
                wait_time = 2**attempt
                logger.info(f"Retry in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)

        except socket.gaierror as e:
            logger.warning(f"DNS resolution failed (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2**attempt)
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2**attempt)

    # All attempts failed - provide helpful message
    is_direct_url = "db." in host if host else False
    if is_direct_url:
        skip_reason = (
            f"Cannot reach {host}:{port} (direct connection requires IPv6).\n"
            "For local development, enable Session Pooler:\n"
            "  1. Go to Supabase Dashboard > Database > Connection Pooler\n"
            "  2. Enable 'Session Mode' pooler\n"
            "  3. Set DATABASE_URL_POOLER in .env\n"
            "  Format: postgresql+asyncpg://postgres.PROJECT:PASS@aws-0-REGION.pooler.supabase.com:5432/postgres"
        )
    else:
        skip_reason = (
            f"Cannot reach {host}:{port}.\n"
            "Check that Session Pooler is enabled in Supabase Dashboard."
        )

    return False, skip_reason


# Check connectivity at module load time
_DB_REACHABLE, _SKIP_REASON = can_reach_database()

# Skip all integration tests if database unreachable
pytestmark = pytest.mark.skipif(
    not _DB_REACHABLE,
    reason=_SKIP_REASON,
)


@pytest.fixture(scope="session")
def test_database_url() -> str:
    """Get test database URL.

    AC-T14.1: Uses test Supabase project via DATABASE_URL.
    """
    url = _get_database_url()
    if not url:
        pytest.skip("DATABASE_URL not set")
    return url


@pytest_asyncio.fixture
async def engine(test_database_url: str):
    """Create async engine for tests with proper lifecycle.

    Uses function scope to ensure each test gets a fresh engine in its own
    event loop, avoiding cross-loop issues with asyncpg.

    Uses NullPool to avoid connection reuse issues with asyncpg transactions.
    """
    from sqlalchemy.pool import NullPool

    eng = create_async_engine(
        test_database_url,
        echo=False,
        poolclass=NullPool,  # Disable pooling - each session gets fresh connection
    )
    yield eng
    # Properly dispose of the engine to avoid connection leaks
    await eng.dispose()


@pytest_asyncio.fixture
async def session_maker(engine) -> async_sessionmaker[AsyncSession]:
    """Create session maker for tests.

    Function-scoped to match the engine fixture.
    """
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest_asyncio.fixture
async def session(session_maker) -> AsyncGenerator[AsyncSession, None]:
    """Create a test session with transaction rollback.

    Each test runs in a transaction that is rolled back after the test.
    This ensures test isolation without polluting the database.

    With NullPool, each session gets a fresh connection, avoiding
    the asyncpg nested transaction issues.
    """
    session = session_maker()
    try:
        yield session
    finally:
        # Close session cleanly - rollback only if in transaction
        try:
            if session.in_transaction():
                await session.rollback()
        except Exception:
            # Ignore errors during cleanup
            pass
        finally:
            await session.close()


@pytest_asyncio.fixture
async def clean_session(session_maker) -> AsyncGenerator[AsyncSession, None]:
    """Create a clean session that commits (for migration tests).

    Use sparingly - this actually modifies the database.
    """
    async with session_maker() as session:
        yield session
        await session.commit()


@pytest.fixture
def test_user_id() -> str:
    """Generate a unique test user ID."""
    return str(uuid4())


@pytest.fixture
def test_telegram_id() -> int:
    """Generate a unique test Telegram ID."""
    import random
    return random.randint(100000000, 999999999)


# Export for other test files
def can_reach_supabase() -> bool:
    """Legacy compatibility - check if database is reachable."""
    return _DB_REACHABLE


# Backward compatibility for test files that import _SUPABASE_REACHABLE
_SUPABASE_REACHABLE = _DB_REACHABLE
