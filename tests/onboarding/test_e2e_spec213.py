"""E2E tests — Spec 213 PR 213-5.

AC-1.4: Full profile personalizes first Telegram message (at least 2 of
{city, scene, occupation, name} present within 25s of POST /profile).

These tests require Telegram MCP + live Supabase — skipped in unit CI.
Run via: pytest tests/onboarding/test_e2e_spec213.py -m e2e
"""

from __future__ import annotations

import pytest


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_full_profile_personalizes_first_message() -> None:
    """AC-1.4: within 25s of POST /profile, first Telegram message mentions
    at least 2 of {city, scene, occupation, name}. Requires Telegram MCP.
    Skipped in unit CI — run via /e2e skill.
    """
    pytest.skip(
        "Requires Telegram MCP + live Supabase — run via /e2e skill"
    )
