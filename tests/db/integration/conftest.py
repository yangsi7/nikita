"""Fixtures for database integration tests.

T14: Integration Tests
- AC-T14.1: Integration tests use test Supabase project
"""

import os

# Load environment variables from .env file
from dotenv import load_dotenv

load_dotenv()
from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Skip all integration tests if DATABASE_URL not set
pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set - skipping integration tests",
)


@pytest.fixture(scope="session")
def test_database_url() -> str:
    """Get test database URL.

    AC-T14.1: Uses test Supabase project via DATABASE_URL.
    """
    url = os.getenv("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL not set")
    return url


@pytest.fixture(scope="session")
def engine(test_database_url: str):
    """Create async engine for tests."""
    return create_async_engine(
        test_database_url,
        echo=False,
        pool_pre_ping=True,
    )


@pytest.fixture(scope="session")
def session_maker(engine) -> async_sessionmaker[AsyncSession]:
    """Create session maker for tests."""
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
    """
    async with session_maker() as session:
        async with session.begin():
            yield session
            # Rollback to undo all changes made during the test
            await session.rollback()


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
