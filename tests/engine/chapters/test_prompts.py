"""Tests for Boss Prompts Module (Spec 004 - Task T2).

TDD tests written FIRST, implementation follows.
Tests cover AC-T2-001 through AC-T2-003.
"""

import pytest


# ==============================================================================
# T2: Create Boss Prompts Module
# ==============================================================================


class TestBossPromptsModuleExists:
    """Tests for AC-T2-001: prompts.py exists with 5 boss prompt templates."""

    def test_ac_t2_001_module_exists(self):
        """AC-T2-001: nikita/engine/chapters/prompts.py exists."""
        from nikita.engine.chapters import prompts

        assert prompts is not None

    def test_ac_t2_001_boss_prompts_dict_exists(self):
        """AC-T2-001: BOSS_PROMPTS dict exists with 5 templates."""
        from nikita.engine.chapters.prompts import BOSS_PROMPTS

        assert BOSS_PROMPTS is not None
        assert isinstance(BOSS_PROMPTS, dict)

    def test_ac_t2_001_has_5_prompts(self):
        """AC-T2-001: BOSS_PROMPTS has entries for chapters 1-5."""
        from nikita.engine.chapters.prompts import BOSS_PROMPTS

        assert len(BOSS_PROMPTS) == 5
        for chapter in range(1, 6):
            assert chapter in BOSS_PROMPTS, f"Missing prompt for chapter {chapter}"


class TestPromptStructure:
    """Tests for AC-T2-002: Each prompt includes required elements."""

    def test_ac_t2_002_prompt_has_challenge_context(self):
        """AC-T2-002: Each prompt includes challenge_context."""
        from nikita.engine.chapters.prompts import BOSS_PROMPTS

        for chapter, prompt in BOSS_PROMPTS.items():
            assert "challenge_context" in prompt, f"Chapter {chapter} missing challenge_context"
            assert isinstance(prompt["challenge_context"], str)
            assert len(prompt["challenge_context"]) > 10, f"Chapter {chapter} challenge_context too short"

    def test_ac_t2_002_prompt_has_success_criteria(self):
        """AC-T2-002: Each prompt includes success_criteria."""
        from nikita.engine.chapters.prompts import BOSS_PROMPTS

        for chapter, prompt in BOSS_PROMPTS.items():
            assert "success_criteria" in prompt, f"Chapter {chapter} missing success_criteria"
            assert isinstance(prompt["success_criteria"], str)
            assert len(prompt["success_criteria"]) > 10, f"Chapter {chapter} success_criteria too short"

    def test_ac_t2_002_prompt_has_opening(self):
        """AC-T2-002: Each prompt includes in_character_opening."""
        from nikita.engine.chapters.prompts import BOSS_PROMPTS

        for chapter, prompt in BOSS_PROMPTS.items():
            assert "in_character_opening" in prompt, f"Chapter {chapter} missing in_character_opening"
            assert isinstance(prompt["in_character_opening"], str)
            assert len(prompt["in_character_opening"]) > 10, f"Chapter {chapter} opening too short"


class TestPromptParameterization:
    """Tests for AC-T2-003: Prompts are parameterized by chapter number."""

    def test_ac_t2_003_get_boss_prompt_function_exists(self):
        """AC-T2-003: get_boss_prompt() function exists."""
        from nikita.engine.chapters.prompts import get_boss_prompt

        assert get_boss_prompt is not None
        assert callable(get_boss_prompt)

    def test_ac_t2_003_get_boss_prompt_accepts_chapter(self):
        """AC-T2-003: get_boss_prompt() accepts chapter parameter."""
        from nikita.engine.chapters.prompts import get_boss_prompt

        prompt = get_boss_prompt(chapter=1)
        assert prompt is not None
        assert isinstance(prompt, dict)

    def test_ac_t2_003_get_boss_prompt_returns_correct_prompt(self):
        """AC-T2-003: get_boss_prompt() returns correct prompt for each chapter."""
        from nikita.engine.chapters.prompts import BOSS_PROMPTS, get_boss_prompt

        for chapter in range(1, 6):
            prompt = get_boss_prompt(chapter=chapter)
            expected = BOSS_PROMPTS[chapter]
            assert prompt == expected, f"Chapter {chapter} prompt mismatch"

    def test_ac_t2_003_get_boss_prompt_raises_for_invalid_chapter(self):
        """AC-T2-003: get_boss_prompt() raises for invalid chapter."""
        from nikita.engine.chapters.prompts import get_boss_prompt

        with pytest.raises(KeyError):
            get_boss_prompt(chapter=0)

        with pytest.raises(KeyError):
            get_boss_prompt(chapter=6)


class TestPromptContent:
    """Content verification tests for each boss prompt."""

    def test_chapter_1_prompt_is_intellectual_challenge(self):
        """Chapter 1 boss is intellectual challenge: 'Worth My Time?'"""
        from nikita.engine.chapters.prompts import BOSS_PROMPTS

        prompt = BOSS_PROMPTS[1]
        # Should reference intellectual/brain engagement
        assert any(
            word in prompt["challenge_context"].lower()
            for word in ["intellectual", "brain", "smart", "mind", "think"]
        )

    def test_chapter_2_prompt_is_conflict_test(self):
        """Chapter 2 boss is conflict test: 'Handle My Intensity?'"""
        from nikita.engine.chapters.prompts import BOSS_PROMPTS

        prompt = BOSS_PROMPTS[2]
        # Should reference intensity/conflict/standing ground
        assert any(
            word in prompt["challenge_context"].lower()
            for word in ["intensity", "conflict", "stand", "ground", "pressure"]
        )

    def test_chapter_3_prompt_is_trust_test(self):
        """Chapter 3 boss is trust test: external pressure scenario."""
        from nikita.engine.chapters.prompts import BOSS_PROMPTS

        prompt = BOSS_PROMPTS[3]
        # Should reference trust/jealousy/confidence
        assert any(
            word in prompt["challenge_context"].lower()
            for word in ["trust", "jealous", "confident", "secure", "external"]
        )

    def test_chapter_4_prompt_is_vulnerability(self):
        """Chapter 4 boss is vulnerability threshold."""
        from nikita.engine.chapters.prompts import BOSS_PROMPTS

        prompt = BOSS_PROMPTS[4]
        # Should reference vulnerability/sharing/real/deep
        assert any(
            word in prompt["challenge_context"].lower()
            for word in ["vulnerab", "real", "share", "deep", "open"]
        )

    def test_chapter_5_prompt_is_partnership(self):
        """Chapter 5 boss is ultimate partnership test."""
        from nikita.engine.chapters.prompts import BOSS_PROMPTS

        prompt = BOSS_PROMPTS[5]
        # Should reference partnership/independence/support
        assert any(
            word in prompt["challenge_context"].lower()
            for word in ["partner", "independen", "support", "connection", "together"]
        )


class TestBossOpeningTone:
    """GH #200: boss openings must match Nikita's texting register, not HR-speak.

    E2E (2026-03-30) found "Prove to me you're worth my time" clashed with the
    lowercase, ellipsis-heavy persona used in normal chat. These tests guard
    against regression toward declamatory register and cliché phrases that had
    also leaked into persona few-shot examples (self-reinforcing).
    """

    def test_ch1_boss_opening_starts_lowercase(self):
        """GH #200: Ch1 opening must start lowercase to match texting style."""
        from nikita.engine.chapters.prompts import BOSS_PROMPTS

        opening = BOSS_PROMPTS[1]["in_character_opening"]
        assert opening[0].islower(), (
            f"Ch1 opening must start lowercase, got: {opening[:40]!r}"
        )

    def test_ch1_boss_opening_drops_cliché_phrase(self):
        """GH #200: the exact cliché "prove you're worth my time" must not appear."""
        from nikita.engine.chapters.prompts import BOSS_PROMPTS

        opening_lower = BOSS_PROMPTS[1]["in_character_opening"].lower()
        # Also catches variants mirrored from persona.py few-shots
        assert "prove to me" not in opening_lower
        assert "prove you're worth" not in opening_lower
        assert "worth my time" not in opening_lower

    def test_ch1_boss_opening_preserves_intellectual_intent(self):
        """GH #200: rewrite must still evoke the intellectual-challenge theme."""
        from nikita.engine.chapters.prompts import BOSS_PROMPTS

        opening_lower = BOSS_PROMPTS[1]["in_character_opening"].lower()
        # At least one thinking/believing keyword must remain
        assert any(
            word in opening_lower
            for word in ["think", "mind", "brain", "believe"]
        ), (
            f"Ch1 opening lost the intellectual-challenge keyword, got: {opening_lower[:100]!r}"
        )

    def test_ch1_boss_opening_is_concise(self):
        """GH #200: openings should read as a text message, not a soliloquy."""
        from nikita.engine.chapters.prompts import BOSS_PROMPTS

        opening = BOSS_PROMPTS[1]["in_character_opening"]
        assert len(opening) < 400, (
            f"Ch1 opening too long ({len(opening)} chars), got: {opening[:80]!r}"
        )

    def test_all_boss_openings_start_lowercase(self):
        """GH #200: every chapter's opening matches Nikita's lowercase texting register."""
        from nikita.engine.chapters.prompts import BOSS_PROMPTS

        for chapter, prompt in BOSS_PROMPTS.items():
            opening = prompt["in_character_opening"]
            assert opening[0].islower(), (
                f"Ch{chapter} opening must start lowercase, got: {opening[:40]!r}"
            )

    def test_all_boss_phase_openings_start_lowercase(self):
        """GH #200: phase-aware (Spec 058) opening AND resolution texts must match.

        The opening phase aliases BOSS_PROMPTS via object reference, so parity
        is automatic. The resolution phase has its own distinct strings that
        ship to players in phase 2 of every boss encounter — these must hold
        the same texting register as the opening phase.
        """
        from nikita.engine.chapters.prompts import BOSS_PHASE_PROMPTS

        for chapter, phases in BOSS_PHASE_PROMPTS.items():
            for phase_name, phase_prompt in phases.items():
                opening = phase_prompt["in_character_opening"]
                assert opening[0].islower(), (
                    f"Ch{chapter} {phase_name} opening must start lowercase, "
                    f"got: {opening[:40]!r}"
                )

    def test_boss_resolution_openings_drop_stage_directions(self):
        """GH #200: no *pauses*, *quietly*, or other stage directions in texting.

        Ch4 resolution opened with "*quietly*" pre-PR — clearly off-voice for
        a text message. This guards against regression to theatrical cues.
        """
        from nikita.engine.chapters.prompts import BOSS_PHASE_PROMPTS

        forbidden = ["*pauses*", "*quietly*", "*smiles*", "*narrows eyes*", "*sighs*"]
        for chapter, phases in BOSS_PHASE_PROMPTS.items():
            for phase_name, phase_prompt in phases.items():
                opening = phase_prompt["in_character_opening"]
                for cue in forbidden:
                    assert cue not in opening, (
                        f"Ch{chapter} {phase_name} contains stage direction "
                        f"{cue!r}, off-register for texting: {opening[:80]!r}"
                    )

    def test_persona_few_shots_drop_cliché_phrase(self):
        """GH #200: few-shot examples must not echo the clichéd boss phrase.

        Few-shot examples are imitation targets — leaving the cliché in makes
        the boss opener self-reinforcing even after the prompt itself is rewritten.
        """
        from nikita.agents.text.persona import (
            CHAPTER_EXAMPLE_RESPONSES,
            EXAMPLE_RESPONSES,
        )

        for ex in EXAMPLE_RESPONSES:
            assert "prove you're worth my time" not in ex["response"].lower(), (
                f"EXAMPLE_RESPONSES still mirrors the cliché: {ex['response']!r}"
            )
        for chapter, examples in CHAPTER_EXAMPLE_RESPONSES.items():
            for ex in examples:
                assert "prove you're worth my time" not in ex["response"].lower(), (
                    f"Ch{chapter} CHAPTER_EXAMPLE_RESPONSES still mirrors "
                    f"the cliché: {ex['response']!r}"
                )
