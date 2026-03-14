"""Integration test configuration.

All tests in this directory use mocked external services and run in-process.
They are excluded from CI via --ignore=tests/integration and by pyproject.toml's
`-m 'not integration'` addopts. The pytestmark below and _SUPABASE_REACHABLE
guard in each test file are belt-and-suspenders.
"""

import pytest

pytestmark = pytest.mark.integration

# Mocked integration tests do not connect to a real database, so they
# are always "reachable". The variable exists for consistency with the
# tests/db/integration/ pattern so test files can use the same skipif idiom.
_SUPABASE_REACHABLE = True
_SKIP_REASON = "Supabase not reachable"
