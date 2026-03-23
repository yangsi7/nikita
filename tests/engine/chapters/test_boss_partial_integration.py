"""Integration tests for boss PARTIAL/truce outcome (GH #146).

Tests the full confidence-based PARTIAL flow:
- judge_multi_phase_outcome confidence < 0.7 → PARTIAL override
- process_partial does NOT increment boss_attempts
- process_partial sets 24h cooldown
- process_outcome dispatches PARTIAL with appropriate message/feedback
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nikita.engine.chapters.boss import BossPhaseState, BossPhase, BossStateMachine
from nikita.engine.chapters.judgment import BossJudgment, BossResult, JudgmentResult


# ============================================================================
# Confidence-based PARTIAL override in judge_multi_phase_outcome
# ============================================================================


class TestConfidenceBasedPartialOverride:
    """AC-5.5: confidence < 0.7 overrides PASS/FAIL to PARTIAL."""

    @pytest.fixture
    def judgment(self):
        return BossJudgment()

    @pytest.fixture
    def phase_state(self):
        return BossPhaseState(
            phase=BossPhase.RESOLUTION,
            chapter=2,
            turn_count=3,
            conversation_history=[
                {"role": "nikita", "content": "Why do you always avoid the hard questions?"},
                {"role": "player", "content": "I... I guess I'm scared of being wrong."},
                {"role": "nikita", "content": "That's something. But can you go deeper?"},
            ],
        )

    @pytest.fixture
    def boss_prompt(self):
        return {
            "challenge_context": "Nikita challenges player on emotional avoidance",
            "success_criteria": "Player must demonstrate genuine vulnerability",
        }

    @pytest.mark.asyncio
    async def test_confidence_0_5_pass_overridden_to_partial(
        self, judgment, phase_state, boss_prompt
    ):
        """PASS with confidence=0.5 is overridden to PARTIAL."""
        low_confidence_pass = JudgmentResult(
            outcome=BossResult.PASS,
            reasoning="Player showed some vulnerability but inconsistently.",
            confidence=0.5,
        )
        with patch.object(
            judgment, "_call_multi_phase_llm", return_value=low_confidence_pass
        ):
            result = await judgment.judge_multi_phase_outcome(
                phase_state=phase_state,
                chapter=2,
                boss_prompt=boss_prompt,
            )
        assert result.outcome == BossResult.PARTIAL
        assert result.confidence == 0.5
        assert "Low confidence" in result.reasoning

    @pytest.mark.asyncio
    async def test_confidence_0_69_fail_overridden_to_partial(
        self, judgment, phase_state, boss_prompt
    ):
        """FAIL with confidence=0.69 is overridden to PARTIAL."""
        low_confidence_fail = JudgmentResult(
            outcome=BossResult.FAIL,
            reasoning="Player seemed dismissive but there were hints of effort.",
            confidence=0.69,
        )
        with patch.object(
            judgment, "_call_multi_phase_llm", return_value=low_confidence_fail
        ):
            result = await judgment.judge_multi_phase_outcome(
                phase_state=phase_state,
                chapter=2,
                boss_prompt=boss_prompt,
            )
        assert result.outcome == BossResult.PARTIAL
        assert result.confidence == 0.69
        assert "Low confidence" in result.reasoning

    @pytest.mark.asyncio
    async def test_confidence_0_7_pass_not_overridden(
        self, judgment, phase_state, boss_prompt
    ):
        """PASS with confidence=0.7 (exactly at threshold) is NOT overridden."""
        at_threshold_pass = JudgmentResult(
            outcome=BossResult.PASS,
            reasoning="Player demonstrated genuine vulnerability.",
            confidence=0.7,
        )
        with patch.object(
            judgment, "_call_multi_phase_llm", return_value=at_threshold_pass
        ):
            result = await judgment.judge_multi_phase_outcome(
                phase_state=phase_state,
                chapter=2,
                boss_prompt=boss_prompt,
            )
        assert result.outcome == BossResult.PASS
        assert result.confidence == 0.7

    @pytest.mark.asyncio
    async def test_confidence_0_85_fail_not_overridden(
        self, judgment, phase_state, boss_prompt
    ):
        """FAIL with confidence=0.85 is NOT overridden."""
        high_confidence_fail = JudgmentResult(
            outcome=BossResult.FAIL,
            reasoning="Player was clearly dismissive.",
            confidence=0.85,
        )
        with patch.object(
            judgment, "_call_multi_phase_llm", return_value=high_confidence_fail
        ):
            result = await judgment.judge_multi_phase_outcome(
                phase_state=phase_state,
                chapter=2,
                boss_prompt=boss_prompt,
            )
        assert result.outcome == BossResult.FAIL
        assert result.confidence == 0.85

    @pytest.mark.asyncio
    async def test_partial_outcome_not_affected_by_confidence(
        self, judgment, phase_state, boss_prompt
    ):
        """PARTIAL outcome is kept even with low confidence (no double-override)."""
        direct_partial = JudgmentResult(
            outcome=BossResult.PARTIAL,
            reasoning="Player acknowledged but didn't fully resolve.",
            confidence=0.55,
        )
        with patch.object(
            judgment, "_call_multi_phase_llm", return_value=direct_partial
        ):
            result = await judgment.judge_multi_phase_outcome(
                phase_state=phase_state,
                chapter=2,
                boss_prompt=boss_prompt,
            )
        assert result.outcome == BossResult.PARTIAL
        # Original reasoning preserved (not prefixed with "Low confidence")
        assert result.reasoning == "Player acknowledged but didn't fully resolve."

    @pytest.mark.asyncio
    async def test_llm_error_returns_error_not_partial(
        self, judgment, phase_state, boss_prompt
    ):
        """LLM error returns ERROR outcome, not PARTIAL."""
        with patch.object(
            judgment, "_call_multi_phase_llm", side_effect=RuntimeError("LLM down")
        ):
            result = await judgment.judge_multi_phase_outcome(
                phase_state=phase_state,
                chapter=2,
                boss_prompt=boss_prompt,
            )
        assert result.outcome == BossResult.ERROR
        assert result.confidence == 0.0


# ============================================================================
# process_partial integration — no attempts increment, 24h cooldown, feedback
# ============================================================================


class TestProcessPartialIntegration:
    """Full integration: PARTIAL outcome through process_outcome."""

    @pytest.fixture
    def boss(self):
        return BossStateMachine()

    @pytest.fixture
    def mock_user_repo(self):
        repo = AsyncMock()
        user = MagicMock()
        user.boss_attempts = 1
        user.chapter = 3
        repo.get = AsyncMock(return_value=user)
        repo.update_game_status = AsyncMock()
        repo.set_cool_down = AsyncMock()
        repo.advance_chapter = AsyncMock()
        repo.increment_boss_attempts = AsyncMock()
        return repo

    @pytest.mark.asyncio
    async def test_partial_outcome_does_not_increment_attempts(
        self, boss, mock_user_repo
    ):
        """PARTIAL via process_outcome does NOT increment boss_attempts."""
        result = await boss.process_outcome(
            user_id="u-partial-1",
            user_repository=mock_user_repo,
            outcome="PARTIAL",
        )
        mock_user_repo.increment_boss_attempts.assert_not_called()
        assert result["attempts"] == 1  # unchanged

    @pytest.mark.asyncio
    async def test_partial_outcome_does_not_advance_chapter(
        self, boss, mock_user_repo
    ):
        """PARTIAL via process_outcome does NOT advance chapter."""
        result = await boss.process_outcome(
            user_id="u-partial-2",
            user_repository=mock_user_repo,
            outcome="PARTIAL",
        )
        mock_user_repo.advance_chapter.assert_not_called()

    @pytest.mark.asyncio
    async def test_partial_outcome_sets_24h_cooldown(self, boss, mock_user_repo):
        """PARTIAL sets a 24h cooldown via set_cool_down."""
        before = datetime.now(UTC)
        result = await boss.process_outcome(
            user_id="u-partial-3",
            user_repository=mock_user_repo,
            outcome="PARTIAL",
        )
        # Verify set_cool_down was called
        mock_user_repo.set_cool_down.assert_awaited_once()
        call_args = mock_user_repo.set_cool_down.call_args
        cooldown_ts = call_args[0][1]
        delta_hours = (cooldown_ts - before).total_seconds() / 3600
        assert 23.9 < delta_hours < 24.1

    @pytest.mark.asyncio
    async def test_partial_outcome_returns_cooldown_in_response(
        self, boss, mock_user_repo
    ):
        """PARTIAL response includes cool_down_until ISO string."""
        result = await boss.process_outcome(
            user_id="u-partial-4",
            user_repository=mock_user_repo,
            outcome="PARTIAL",
        )
        assert "cool_down_until" in result
        # Verify it's a valid ISO datetime string
        parsed = datetime.fromisoformat(result["cool_down_until"])
        assert parsed > datetime.now(UTC)

    @pytest.mark.asyncio
    async def test_partial_outcome_sets_game_status_active(
        self, boss, mock_user_repo
    ):
        """PARTIAL sets game_status back to 'active'."""
        result = await boss.process_outcome(
            user_id="u-partial-5",
            user_repository=mock_user_repo,
            outcome="PARTIAL",
        )
        assert result["game_status"] == "active"
        mock_user_repo.update_game_status.assert_called_once_with(
            "u-partial-5", "active"
        )

    @pytest.mark.asyncio
    async def test_partial_outcome_includes_truce_message(
        self, boss, mock_user_repo
    ):
        """PARTIAL result includes appropriate truce feedback message."""
        result = await boss.process_outcome(
            user_id="u-partial-6",
            user_repository=mock_user_repo,
            outcome="PARTIAL",
        )
        assert result["outcome"] == "PARTIAL"
        assert result["passed"] is False
        assert "message" in result
        assert "truce" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_partial_keeps_attempts_after_prior_fail(self, boss):
        """After 1 FAIL + 1 PARTIAL, attempts should be 1 (not 2)."""
        repo = AsyncMock()
        user_after_fail = MagicMock()
        user_after_fail.boss_attempts = 1
        user_after_fail.chapter = 2
        repo.get = AsyncMock(return_value=user_after_fail)
        repo.increment_boss_attempts = AsyncMock(
            return_value=MagicMock(boss_attempts=1)
        )
        repo.update_game_status = AsyncMock()
        repo.set_cool_down = AsyncMock()

        # PARTIAL after a prior fail — attempts stay at 1
        result = await boss.process_partial(
            user_id="u-mixed", user_repository=repo
        )
        assert result["attempts"] == 1
        repo.increment_boss_attempts.assert_not_called()


# ============================================================================
# Confidence boundary values
# ============================================================================


class TestConfidenceBoundaryValues:
    """Edge cases around the 0.7 confidence threshold."""

    @pytest.fixture
    def judgment(self):
        return BossJudgment()

    @pytest.fixture
    def phase_state(self):
        return BossPhaseState(
            phase=BossPhase.RESOLUTION,
            chapter=1,
            turn_count=2,
            conversation_history=[
                {"role": "nikita", "content": "Tell me something real."},
                {"role": "player", "content": "I don't know what's real anymore."},
            ],
        )

    @pytest.fixture
    def boss_prompt(self):
        return {
            "challenge_context": "Trust challenge",
            "success_criteria": "Player must share something genuine",
        }

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "confidence,original_outcome,expected_outcome",
        [
            (0.50, BossResult.PASS, BossResult.PARTIAL),
            (0.60, BossResult.FAIL, BossResult.PARTIAL),
            (0.69, BossResult.PASS, BossResult.PARTIAL),
            (0.699, BossResult.FAIL, BossResult.PARTIAL),
            (0.70, BossResult.PASS, BossResult.PASS),     # threshold: not overridden
            (0.70, BossResult.FAIL, BossResult.FAIL),     # threshold: not overridden
            (0.71, BossResult.PASS, BossResult.PASS),
            (0.90, BossResult.FAIL, BossResult.FAIL),
        ],
    )
    async def test_confidence_threshold_boundary(
        self,
        judgment,
        phase_state,
        boss_prompt,
        confidence,
        original_outcome,
        expected_outcome,
    ):
        """Parametrized boundary test for confidence threshold."""
        llm_result = JudgmentResult(
            outcome=original_outcome,
            reasoning="Test reasoning",
            confidence=confidence,
        )
        with patch.object(
            judgment, "_call_multi_phase_llm", return_value=llm_result
        ):
            result = await judgment.judge_multi_phase_outcome(
                phase_state=phase_state,
                chapter=1,
                boss_prompt=boss_prompt,
            )
        assert result.outcome == expected_outcome
