"""Tests for FastAPI lifespan startup guards (nikita/api/main.py).

Covers the fail-fast RuntimeError checks that run at deploy time to
prevent misconfigured revisions from going healthy.

- task_auth_secret guard (BKD-003, PR #118) — pre-existing
- supabase_url guard (GH #184) — added in this PR
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI

from nikita.api.main import lifespan


@pytest.mark.asyncio
async def test_lifespan_raises_when_supabase_url_missing():
    """GH #184: lifespan fails fast when SUPABASE_URL env var is missing.

    Before this guard, the Supabase client init block at lines 102-108
    caught the SupabaseException silently and set app.state.supabase=None,
    leaving the app "healthy" but broken. Now the process dies at startup.
    """
    app = FastAPI()

    with patch("nikita.api.main.settings") as mock_settings:
        mock_settings.debug = True  # irrelevant for SUPABASE_URL guard
        mock_settings.task_auth_secret = "dummy"
        mock_settings.supabase_url = None  # <-- the condition under test
        mock_settings.anthropic_api_key = None
        mock_settings.llm_warmup_enabled = False

        with pytest.raises(RuntimeError, match="supabase_url must be set"):
            async with lifespan(app):
                pass


@pytest.mark.asyncio
async def test_lifespan_raises_when_supabase_url_empty_string():
    """Empty string must be treated as missing (falsy check)."""
    app = FastAPI()

    with patch("nikita.api.main.settings") as mock_settings:
        mock_settings.debug = True
        mock_settings.task_auth_secret = "dummy"
        mock_settings.supabase_url = ""  # falsy — still missing
        mock_settings.anthropic_api_key = None
        mock_settings.llm_warmup_enabled = False

        with pytest.raises(RuntimeError, match="supabase_url must be set"):
            async with lifespan(app):
                pass


@pytest.mark.asyncio
async def test_lifespan_guards_run_in_order_task_auth_secret_first():
    """BKD-003 guard fires before the #184 guard — preserves existing behavior."""
    app = FastAPI()

    with patch("nikita.api.main.settings") as mock_settings:
        mock_settings.debug = False  # triggers BKD-003 path
        mock_settings.task_auth_secret = None
        mock_settings.supabase_url = None  # also missing

        # Should raise the BKD-003 message, not the SUPABASE_URL one —
        # proves ordering: task_auth_secret guard runs first.
        with pytest.raises(RuntimeError, match="task_auth_secret must be set"):
            async with lifespan(app):
                pass
