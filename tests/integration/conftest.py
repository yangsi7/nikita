"""Integration test configuration.

All tests in this directory require external services (Supabase, ElevenLabs, etc.)
and are excluded from CI via --ignore=tests/integration. The pytestmark below is
a belt-and-suspenders guard: even if the --ignore flag is missing, these tests
will be deselected by pyproject.toml's `-m 'not integration'` default.
"""

import pytest

pytestmark = pytest.mark.integration
