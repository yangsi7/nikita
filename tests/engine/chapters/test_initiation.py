"""Tests for Boss Initiation (Spec 004 - Task T4).

TDD tests for boss encounter initiation.
Tests cover AC-FR002-001, AC-FR002-002, AC-T4-001.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


# ==============================================================================
# T4: Implement Boss Initiation
# ==============================================================================


class TestInitiateBossMethod:
    """Tests for initiate_boss method structure."""

    def test_ac_fr002_001_method_exists(self):
        """BossStateMachine has initiate_boss method."""
        from nikita.engine.chapters.boss import BossStateMachine

        sm = BossStateMachine()
        assert hasattr(sm, "initiate_boss")
        assert callable(sm.initiate_boss)

    @pytest.mark.asyncio
    async def test_initiate_boss_is_async(self):
        """initiate_boss is an async method."""
        import inspect

        from nikita.engine.chapters.boss import BossStateMachine

        sm = BossStateMachine()
        assert inspect.iscoroutinefunction(sm.initiate_boss)


class TestInitiateBossReturnsPrompt:
    """Tests for AC-FR002-002: Boss challenge prompt returned."""

    @pytest.mark.asyncio
    async def test_ac_fr002_002_returns_challenge_context(self):
        """initiate_boss returns dict with challenge_context."""
        from nikita.engine.chapters.boss import BossStateMachine

        sm = BossStateMachine()
        user_id = uuid4()
        chapter = 1

        result = await sm.initiate_boss(user_id, chapter=chapter)

        assert "challenge_context" in result
        assert isinstance(result["challenge_context"], str)
        assert len(result["challenge_context"]) > 10

    @pytest.mark.asyncio
    async def test_ac_fr002_002_returns_opening_line(self):
        """initiate_boss returns dict with in_character_opening."""
        from nikita.engine.chapters.boss import BossStateMachine

        sm = BossStateMachine()
        user_id = uuid4()
        chapter = 1

        result = await sm.initiate_boss(user_id, chapter=chapter)

        assert "in_character_opening" in result
        assert isinstance(result["in_character_opening"], str)
        assert len(result["in_character_opening"]) > 10

    @pytest.mark.asyncio
    async def test_ac_fr002_002_returns_success_criteria(self):
        """initiate_boss returns dict with success_criteria."""
        from nikita.engine.chapters.boss import BossStateMachine

        sm = BossStateMachine()
        user_id = uuid4()
        chapter = 1

        result = await sm.initiate_boss(user_id, chapter=chapter)

        assert "success_criteria" in result
        assert isinstance(result["success_criteria"], str)

    @pytest.mark.asyncio
    async def test_ac_fr002_002_returns_chapter_info(self):
        """initiate_boss returns dict with chapter number."""
        from nikita.engine.chapters.boss import BossStateMachine

        sm = BossStateMachine()
        user_id = uuid4()
        chapter = 3

        result = await sm.initiate_boss(user_id, chapter=chapter)

        assert "chapter" in result
        assert result["chapter"] == 3


class TestInitiateBossChapters:
    """Test initiate_boss returns correct prompt for each chapter."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("chapter", [1, 2, 3, 4, 5])
    async def test_returns_correct_prompt_per_chapter(self, chapter: int):
        """initiate_boss returns chapter-specific prompt."""
        from nikita.engine.chapters.boss import BossStateMachine
        from nikita.engine.chapters.prompts import BOSS_PROMPTS

        sm = BossStateMachine()
        user_id = uuid4()

        result = await sm.initiate_boss(user_id, chapter=chapter)

        expected = BOSS_PROMPTS[chapter]
        assert result["challenge_context"] == expected["challenge_context"]
        assert result["in_character_opening"] == expected["in_character_opening"]
        assert result["success_criteria"] == expected["success_criteria"]


