"""Tests for touchpoint context loading — PR 76 Review R4.

Tests _load_top_vices() real implementation and _load_open_threads() stub.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


def _make_engine():
    """Create TouchpointEngine with mocked generator."""
    from nikita.touchpoints.engine import TouchpointEngine

    with patch("nikita.touchpoints.engine.MessageGenerator"):
        engine = TouchpointEngine(AsyncMock())
    engine.generator = AsyncMock()
    return engine


def _make_vice_pref(category: str, engagement: float):
    """Create a mock UserVicePreference."""
    pref = MagicMock()
    pref.category = category
    pref.engagement_score = engagement
    return pref


class TestLoadTopVices:
    """Tests for _load_top_vices() real implementation."""

    @pytest.mark.asyncio
    async def test_returns_category_names(self):
        """R4: Returns list of category name strings from VicePreferenceRepository."""
        engine = _make_engine()
        user_id = uuid4()

        mock_prefs = [
            _make_vice_pref("dark_humor", 0.8),
            _make_vice_pref("vulnerability", 0.6),
        ]

        with patch("nikita.db.repositories.vice_repository.VicePreferenceRepository") as MockRepo:
            MockRepo.return_value.get_active = AsyncMock(return_value=mock_prefs)
            result = await engine._load_top_vices(user_id)

        assert result == ["dark_humor", "vulnerability"]

    @pytest.mark.asyncio
    async def test_returns_max_3(self):
        """R4: Returns at most 3 vice categories even if more exist."""
        engine = _make_engine()
        user_id = uuid4()

        mock_prefs = [_make_vice_pref(f"cat_{i}", 0.9 - i * 0.1) for i in range(5)]

        with patch("nikita.db.repositories.vice_repository.VicePreferenceRepository") as MockRepo:
            MockRepo.return_value.get_active = AsyncMock(return_value=mock_prefs)
            result = await engine._load_top_vices(user_id)

        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_returns_empty_on_exception(self):
        """R4: Returns [] gracefully on repository error."""
        engine = _make_engine()
        user_id = uuid4()

        with patch(
            "nikita.db.repositories.vice_repository.VicePreferenceRepository",
            side_effect=Exception("DB error"),
        ):
            result = await engine._load_top_vices(user_id)

        assert result == []

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_vices(self):
        """R4: Returns [] when user has no discovered vices."""
        engine = _make_engine()
        user_id = uuid4()

        with patch("nikita.db.repositories.vice_repository.VicePreferenceRepository") as MockRepo:
            MockRepo.return_value.get_active = AsyncMock(return_value=[])
            result = await engine._load_top_vices(user_id)

        assert result == []


class TestLoadOpenThreads:
    """Tests for _load_open_threads() — returns [] until table exists."""

    @pytest.mark.asyncio
    async def test_returns_empty_list(self):
        """R4: Returns [] (conversation_threads table not yet created)."""
        engine = _make_engine()
        result = await engine._load_open_threads(uuid4())
        assert result == []
