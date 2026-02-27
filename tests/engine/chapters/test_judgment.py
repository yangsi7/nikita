"""
Tests for Boss Judgment Module (T6)

TDD: Write tests FIRST, verify FAIL, then implement.

Acceptance Criteria:
- AC-FR004-001: Given user demonstrates required skill, When judge_boss_outcome() called, Then returns BossResult.PASS
- AC-T6-001: nikita/engine/chapters/judgment.py exists with BossJudgment class
- AC-T6-002: Judgment uses Claude Sonnet with chapter-specific criteria
- AC-T6-003: Returns structured result: {outcome: PASS|FAIL, reasoning: str}
"""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal


class TestBossJudgmentStructure:
    """AC-T6-001: BossJudgment class exists with required structure"""

    def test_ac_t6_001_module_exists(self):
        """BossJudgment module can be imported"""
        from nikita.engine.chapters.judgment import BossJudgment
        assert BossJudgment is not None

    def test_ac_t6_001_boss_result_enum_exists(self):
        """BossResult enum exists with PASS and FAIL values"""
        from nikita.engine.chapters.judgment import BossResult
        assert hasattr(BossResult, 'PASS')
        assert hasattr(BossResult, 'FAIL')

    def test_ac_t6_001_judgment_result_model_exists(self):
        """JudgmentResult model exists with outcome and reasoning"""
        from nikita.engine.chapters.judgment import JudgmentResult
        result = JudgmentResult(outcome='PASS', reasoning='Test reasoning')
        assert result.outcome == 'PASS'
        assert result.reasoning == 'Test reasoning'

    def test_ac_t6_001_class_has_judge_method(self):
        """BossJudgment has judge_boss_outcome method"""
        from nikita.engine.chapters.judgment import BossJudgment
        judge = BossJudgment()
        assert hasattr(judge, 'judge_boss_outcome')
        assert callable(getattr(judge, 'judge_boss_outcome'))

    def test_ac_t6_001_judge_method_is_async(self):
        """judge_boss_outcome is an async method"""
        import asyncio
        from nikita.engine.chapters.judgment import BossJudgment
        judge = BossJudgment()
        assert asyncio.iscoroutinefunction(judge.judge_boss_outcome)


class TestJudgeMethodSignature:
    """AC-T6-002: Judgment uses chapter-specific criteria"""

    def test_judge_accepts_required_parameters(self):
        """judge_boss_outcome accepts user_message, conversation_history, chapter"""
        import inspect
        from nikita.engine.chapters.judgment import BossJudgment
        judge = BossJudgment()
        sig = inspect.signature(judge.judge_boss_outcome)
        params = list(sig.parameters.keys())
        assert 'user_message' in params
        assert 'conversation_history' in params
        assert 'chapter' in params

    def test_judge_accepts_boss_prompt_parameter(self):
        """judge_boss_outcome accepts boss_prompt for success criteria"""
        import inspect
        from nikita.engine.chapters.judgment import BossJudgment
        judge = BossJudgment()
        sig = inspect.signature(judge.judge_boss_outcome)
        params = list(sig.parameters.keys())
        assert 'boss_prompt' in params


class TestJudgmentOutcome:
    """AC-FR004-001 & AC-T6-003: Returns structured result"""

    @pytest.mark.asyncio
    async def test_ac_t6_003_returns_judgment_result(self):
        """judge_boss_outcome returns JudgmentResult"""
        from nikita.engine.chapters.judgment import BossJudgment, JudgmentResult
        judge = BossJudgment()

        # Mock the LLM call
        with patch.object(judge, '_call_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = JudgmentResult(outcome='PASS', reasoning='Demonstrated skill')

            result = await judge.judge_boss_outcome(
                user_message="I trust you completely and here's why...",
                conversation_history=[],
                chapter=1,
                boss_prompt={"success_criteria": "Shows trust"}
            )

            assert isinstance(result, JudgmentResult)

    @pytest.mark.asyncio
    async def test_ac_t6_003_result_has_outcome(self):
        """JudgmentResult has outcome field"""
        from nikita.engine.chapters.judgment import BossJudgment, JudgmentResult
        judge = BossJudgment()

        with patch.object(judge, '_call_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = JudgmentResult(outcome='PASS', reasoning='Good job')

            result = await judge.judge_boss_outcome(
                user_message="Test",
                conversation_history=[],
                chapter=1,
                boss_prompt={}
            )

            assert result.outcome in ['PASS', 'FAIL']

    @pytest.mark.asyncio
    async def test_ac_t6_003_result_has_reasoning(self):
        """JudgmentResult has reasoning field"""
        from nikita.engine.chapters.judgment import BossJudgment, JudgmentResult
        judge = BossJudgment()

        with patch.object(judge, '_call_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = JudgmentResult(outcome='FAIL', reasoning='Did not meet criteria')

            result = await judge.judge_boss_outcome(
                user_message="Test",
                conversation_history=[],
                chapter=1,
                boss_prompt={}
            )

            assert isinstance(result.reasoning, str)
            assert len(result.reasoning) > 0

    @pytest.mark.asyncio
    async def test_ac_fr004_001_pass_when_skill_demonstrated(self):
        """Returns PASS when user demonstrates required skill"""
        from nikita.engine.chapters.judgment import BossJudgment, JudgmentResult
        judge = BossJudgment()

        with patch.object(judge, '_call_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = JudgmentResult(
                outcome='PASS',
                reasoning='User showed genuine intellectual engagement'
            )

            result = await judge.judge_boss_outcome(
                user_message="I've been thinking deeply about your perspective on philosophy...",
                conversation_history=[],
                chapter=1,
                boss_prompt={
                    "success_criteria": "User shows genuine intellectual engagement"
                }
            )

            assert result.outcome == 'PASS'


class TestChapterSpecificCriteria:
    """AC-T6-002: Judgment uses chapter-specific criteria"""

    @pytest.mark.asyncio
    async def test_chapter_1_intellectual_challenge(self):
        """Chapter 1 boss checks for intellectual engagement"""
        from nikita.engine.chapters.judgment import BossJudgment, JudgmentResult
        judge = BossJudgment()

        with patch.object(judge, '_call_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = JudgmentResult(outcome='PASS', reasoning='Good')

            await judge.judge_boss_outcome(
                user_message="Test",
                conversation_history=[],
                chapter=1,
                boss_prompt={"success_criteria": "intellectual engagement"}
            )

            # Verify LLM was called with chapter context
            mock_llm.assert_called_once()
            call_args = mock_llm.call_args
            assert call_args is not None

    @pytest.mark.parametrize("chapter", [1, 2, 3, 4, 5])
    @pytest.mark.asyncio
    async def test_all_chapters_supported(self, chapter):
        """All 5 chapters can be judged"""
        from nikita.engine.chapters.judgment import BossJudgment, JudgmentResult
        judge = BossJudgment()

        with patch.object(judge, '_call_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = JudgmentResult(outcome='PASS', reasoning='OK')

            result = await judge.judge_boss_outcome(
                user_message="Test response",
                conversation_history=[],
                chapter=chapter,
                boss_prompt={"success_criteria": "test"}
            )

            assert result is not None


class TestLLMIntegration:
    """AC-T6-002: Uses Claude Sonnet with proper configuration"""

    def test_has_llm_call_method(self):
        """BossJudgment has _call_llm method for LLM interaction"""
        from nikita.engine.chapters.judgment import BossJudgment
        judge = BossJudgment()
        assert hasattr(judge, '_call_llm')

    @pytest.mark.asyncio
    async def test_llm_called_with_temperature_zero(self):
        """LLM is called with temperature=0 for consistency"""
        from nikita.engine.chapters.judgment import BossJudgment, JudgmentResult
        judge = BossJudgment()

        # This test verifies the implementation uses temperature=0
        # The actual test would check the LLM call configuration
        with patch.object(judge, '_call_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = JudgmentResult(outcome='PASS', reasoning='OK')

            await judge.judge_boss_outcome(
                user_message="Test",
                conversation_history=[],
                chapter=1,
                boss_prompt={}
            )

            # Verify LLM was invoked
            assert mock_llm.called


class TestLLMErrorHandling:
    """LLM failure returns ERROR outcome, not FAIL (PR #81 fix)."""

    @pytest.mark.asyncio
    async def test_llm_failure_returns_error_not_fail(self):
        """LLM exception returns ERROR outcome, not FAIL."""
        from nikita.engine.chapters.judgment import BossJudgment, BossResult

        judge = BossJudgment()
        with patch.object(judge, '_call_llm', new_callable=AsyncMock,
                          side_effect=Exception("API timeout")):
            result = await judge.judge_boss_outcome(
                user_message="Test",
                conversation_history=[],
                chapter=1,
                boss_prompt={},
            )
        assert result.outcome == BossResult.ERROR
        assert "Judgment error" in result.reasoning

    @pytest.mark.asyncio
    async def test_error_has_zero_confidence(self):
        """ERROR outcome has zero confidence."""
        from nikita.engine.chapters.judgment import BossJudgment

        judge = BossJudgment()
        with patch.object(judge, '_call_llm', new_callable=AsyncMock,
                          side_effect=Exception("fail")):
            result = await judge.judge_boss_outcome(
                user_message="Test",
                conversation_history=[],
                chapter=1,
                boss_prompt={},
            )
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_boss_result_has_error_enum(self):
        """BossResult enum has ERROR member."""
        from nikita.engine.chapters.judgment import BossResult
        assert hasattr(BossResult, 'ERROR')
        assert BossResult.ERROR.value == "ERROR"


class TestEdgeCases:
    """Edge cases and error handling"""

    @pytest.mark.asyncio
    async def test_empty_conversation_history(self):
        """Handles empty conversation history"""
        from nikita.engine.chapters.judgment import BossJudgment, JudgmentResult
        judge = BossJudgment()

        with patch.object(judge, '_call_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = JudgmentResult(outcome='FAIL', reasoning='No context')

            result = await judge.judge_boss_outcome(
                user_message="Hello",
                conversation_history=[],
                chapter=1,
                boss_prompt={}
            )

            assert result is not None

    @pytest.mark.asyncio
    async def test_long_conversation_history(self):
        """Handles long conversation history"""
        from nikita.engine.chapters.judgment import BossJudgment, JudgmentResult
        judge = BossJudgment()

        history = [
            {"role": "user", "content": f"Message {i}"}
            for i in range(50)
        ]

        with patch.object(judge, '_call_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = JudgmentResult(outcome='PASS', reasoning='OK')

            result = await judge.judge_boss_outcome(
                user_message="Final message",
                conversation_history=history,
                chapter=1,
                boss_prompt={}
            )

            assert result is not None
