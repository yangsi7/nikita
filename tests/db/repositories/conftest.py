"""Fixtures for repository tests.

Re-exports fixtures from integration conftest for repository tests that
need database access.
"""

# Import all fixtures from integration conftest
from tests.db.integration.conftest import (
    _SUPABASE_REACHABLE,
    can_reach_supabase,
    clean_session,
    engine,
    session,
    session_maker,
    test_database_url,
    test_telegram_id,
    test_user_id,
)

# Re-export for pytest discovery
__all__ = [
    "_SUPABASE_REACHABLE",
    "can_reach_supabase",
    "clean_session",
    "engine",
    "session",
    "session_maker",
    "test_database_url",
    "test_telegram_id",
    "test_user_id",
]
