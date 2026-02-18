"""Tests for Spec 058 phase-aware boss prompts."""

from __future__ import annotations

import pytest

from nikita.engine.chapters.prompts import (
    BOSS_PHASE_PROMPTS,
    BOSS_PROMPTS,
    get_boss_phase_prompt,
)


REQUIRED_KEYS = {"challenge_context", "success_criteria", "in_character_opening", "phase_instruction"}


class TestBossPhasePromptsExist:
    """AC-4.1: 10 prompts total (2 phases x 5 chapters)."""

    @pytest.mark.parametrize("chapter", [1, 2, 3, 4, 5])
    def test_opening_prompt_exists(self, chapter: int):
        prompt = BOSS_PHASE_PROMPTS[chapter]["opening"]
        assert set(prompt.keys()) >= REQUIRED_KEYS

    @pytest.mark.parametrize("chapter", [1, 2, 3, 4, 5])
    def test_resolution_prompt_exists(self, chapter: int):
        prompt = BOSS_PHASE_PROMPTS[chapter]["resolution"]
        assert set(prompt.keys()) >= REQUIRED_KEYS


class TestGetBossPhasePrompt:
    """AC-4.4, AC-4.6: get_boss_phase_prompt lookup and validation."""

    @pytest.mark.parametrize(
        "chapter,phase",
        [(c, p) for c in range(1, 6) for p in ("opening", "resolution")],
    )
    def test_valid_lookups(self, chapter: int, phase: str):
        prompt = get_boss_phase_prompt(chapter, phase)
        assert "challenge_context" in prompt
        assert "success_criteria" in prompt
        assert "in_character_opening" in prompt
        assert "phase_instruction" in prompt

    def test_invalid_chapter_raises(self):
        with pytest.raises(KeyError, match="Invalid chapter"):
            get_boss_phase_prompt(0, "opening")

    def test_invalid_phase_raises(self):
        with pytest.raises(KeyError, match="Invalid phase"):
            get_boss_phase_prompt(1, "nonexistent")

    def test_ch1_opening_reuses_existing_content(self):
        """AC-4.6: Ch1 opening matches existing BOSS_PROMPTS[1] content."""
        phase_prompt = get_boss_phase_prompt(1, "opening")
        original = BOSS_PROMPTS[1]
        assert phase_prompt["challenge_context"] == original["challenge_context"]
        assert phase_prompt["success_criteria"] == original["success_criteria"]
        assert phase_prompt["in_character_opening"] == original["in_character_opening"]
