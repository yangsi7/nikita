"""Root conftest.py for all tests.

Provides autouse fixtures that ensure test isolation by clearing
singleton caches between tests.

This prevents event loop contamination where:
1. Test 1 creates async engine with connections bound to event loop A
2. LRU cache stores the engine
3. Event loop A closes after Test 1
4. Test 2 runs on event loop B
5. Cached engine has stale connections bound to closed loop A
6. Test 2 fails with "Future attached to a different loop"

Solution: Clear all LRU-cached singletons after each test.
"""

import pytest


@pytest.fixture(autouse=True)
def clear_singleton_caches():
    """Clear LRU-cached singletons between tests.

    This is an autouse fixture that runs after EVERY test to ensure
    the next test gets fresh instances bound to its event loop.

    Clears:
    - get_async_engine() - SQLAlchemy async engine with connection pool
    - get_session_maker() - SQLAlchemy async session factory
    - get_settings() - Pydantic settings singleton
    - _shared_cache - Rate limiter InMemoryCache with asyncio.Lock()
    """
    # Let the test run first
    yield

    # Clear database singletons AFTER test completes
    from nikita.db.database import get_async_engine, get_session_maker

    get_async_engine.cache_clear()
    get_session_maker.cache_clear()

    # Clear settings cache
    from nikita.config.settings import get_settings

    get_settings.cache_clear()

    # Clear rate limiter shared cache (contains asyncio.Lock bound to event loop)
    import nikita.platforms.telegram.rate_limiter as rl

    rl._shared_cache = None
