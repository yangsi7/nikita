"""
Integration Tests for Boss Flow (T14)

Tests full boss encounter flow end-to-end:
- Threshold detection → Boss initiation → Judgment → Outcome processing
- Database state transitions (mocked)
- Agent integration verification

Acceptance Criteria:
- AC-T14-001: Full boss encounter flow tested end-to-end
- AC-T14-002: Agent integration verified with mock messages
- AC-T14-003: Database state transitions verified
"""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal


class TestFullBossEncounterFlow:
    """AC-T14-001: Full boss encounter flow tested end-to-end."""

    @pytest.mark.asyncio
    async def test_complete_boss_pass_flow(self):
        """Test: threshold trigger → initiate → judge PASS → advance chapter."""
        from nikita.engine.chapters.boss import BossStateMachine
        from nikita.engine.chapters.judgment import BossJudgment, JudgmentResult

        user_id = uuid4()
        sm = BossStateMachine()

        # Step 1: Check if boss should trigger
        trigger = sm.should_trigger_boss(
            relationship_score=Decimal("55"),
            chapter=1,
            game_status="active"
        )
        assert trigger is True, "Boss should trigger at 55% for chapter 1"

        # Step 2: Initiate boss encounter
        boss_prompt = await sm.initiate_boss(user_id, chapter=1)
        assert boss_prompt['chapter'] == 1
        assert 'challenge_context' in boss_prompt
        assert 'success_criteria' in boss_prompt

        # Step 3: Simulate user response and judgment (mocked)
        judgment = BossJudgment()
        with patch.object(judgment, '_call_llm') as mock_llm:
            mock_llm.return_value = JudgmentResult(
                outcome='PASS',
                reasoning='User demonstrated understanding'
            )
            result = await judgment.judge_boss_outcome(
                user_message="I really enjoy learning what you find interesting",
                conversation_history=[],
                chapter=1,
                boss_prompt=boss_prompt
            )
            assert result.outcome == 'PASS'

        # Step 4: Process the PASS outcome
        with patch.object(sm, '_get_user_repo') as mock_get_repo:
            mock_repo = AsyncMock()
            mock_get_repo.return_value = mock_repo

            mock_user = MagicMock()
            mock_user.chapter = 2  # Newly advanced
            mock_user.game_status = 'active'
            mock_user.boss_attempts = 0
            mock_repo.advance_chapter.return_value = mock_user

            outcome = await sm.process_outcome(user_id, passed=True)

            assert outcome['passed'] is True
            assert outcome['new_chapter'] == 2
            assert 'Chapter advanced' in outcome['message']
            mock_repo.advance_chapter.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_complete_boss_fail_retry_flow(self):
        """Test: threshold trigger → initiate → judge FAIL → retry allowed."""
        from nikita.engine.chapters.boss import BossStateMachine
        from nikita.engine.chapters.judgment import BossJudgment, JudgmentResult

        user_id = uuid4()
        sm = BossStateMachine()

        # Step 1: Initiate boss
        boss_prompt = await sm.initiate_boss(user_id, chapter=2)
        assert boss_prompt['chapter'] == 2

        # Step 2: Simulate FAIL judgment
        judgment = BossJudgment()
        with patch.object(judgment, '_call_llm') as mock_llm:
            mock_llm.return_value = JudgmentResult(
                outcome='FAIL',
                reasoning='User did not demonstrate required skill'
            )
            result = await judgment.judge_boss_outcome(
                user_message="I don't really care about that",
                conversation_history=[],
                chapter=2,
                boss_prompt=boss_prompt
            )
            assert result.outcome == 'FAIL'

        # Step 3: Process FAIL - first attempt
        with patch.object(sm, '_get_user_repo') as mock_get_repo:
            mock_repo = AsyncMock()
            mock_get_repo.return_value = mock_repo

            mock_user = MagicMock()
            mock_user.boss_attempts = 1
            mock_user.game_status = 'boss_fight'
            mock_repo.increment_boss_attempts.return_value = mock_user

            outcome = await sm.process_outcome(user_id, passed=False)

            assert outcome['passed'] is False
            assert outcome['attempts'] == 1
            assert outcome['game_over'] is False
            assert 'Try again' in outcome['message']

    @pytest.mark.asyncio
    async def test_complete_boss_fail_game_over_flow(self):
        """Test: third fail triggers game over."""
        from nikita.engine.chapters.boss import BossStateMachine

        user_id = uuid4()
        sm = BossStateMachine()

        # Process third failure
        with patch.object(sm, '_get_user_repo') as mock_get_repo:
            mock_repo = AsyncMock()
            mock_get_repo.return_value = mock_repo

            mock_user = MagicMock()
            mock_user.boss_attempts = 3
            mock_user.game_status = 'game_over'
            mock_repo.increment_boss_attempts.return_value = mock_user

            outcome = await sm.process_outcome(user_id, passed=False)

            assert outcome['passed'] is False
            assert outcome['attempts'] == 3
            assert outcome['game_over'] is True
            assert 'Game over' in outcome['message']

    @pytest.mark.asyncio
    async def test_complete_victory_flow(self):
        """Test: Chapter 5 pass triggers victory."""
        from nikita.engine.chapters.boss import BossStateMachine

        user_id = uuid4()
        sm = BossStateMachine()

        # Step 1: Check chapter 5 boss trigger
        trigger = sm.should_trigger_boss(
            relationship_score=Decimal("75"),
            chapter=5,
            game_status="active"
        )
        assert trigger is True, "Boss should trigger at 75% for chapter 5"

        # Step 2: Initiate chapter 5 boss
        boss_prompt = await sm.initiate_boss(user_id, chapter=5)
        assert boss_prompt['chapter'] == 5

        # Step 3: Process victory
        with patch.object(sm, '_get_user_repo') as mock_get_repo:
            mock_repo = AsyncMock()
            mock_get_repo.return_value = mock_repo

            mock_user = MagicMock()
            mock_user.chapter = 5  # Stays at 5
            mock_user.game_status = 'won'
            mock_user.boss_attempts = 0
            mock_repo.advance_chapter.return_value = mock_user

            outcome = await sm.process_outcome(user_id, passed=True)

            assert outcome['passed'] is True


class TestAgentIntegrationFlow:
    """AC-T14-002: Agent integration verified with mock messages."""

    @pytest.mark.asyncio
    async def test_message_handler_active_to_boss_fight(self):
        """Handler processes active user correctly."""
        from nikita.agents.text.handler import MessageHandler
        from nikita.agents.text.skip import SkipDecision

        # Create never-skip decision to ensure deterministic test
        mock_skip = MagicMock(spec=SkipDecision)
        mock_skip.should_skip.return_value = False

        handler = MessageHandler(skip_decision=mock_skip)
        user_id = uuid4()

        with patch('nikita.agents.text.handler.get_nikita_agent_for_user') as mock_get:
            with patch('nikita.agents.text.handler.generate_response') as mock_gen:
                mock_agent = MagicMock()
                mock_deps = MagicMock()
                mock_deps.user.game_status = 'active'
                mock_deps.user.chapter = 1
                mock_get.return_value = (mock_agent, mock_deps)
                mock_gen.return_value = "Normal response"

                decision = await handler.handle(user_id, "Hello!")

                assert decision.should_respond is True
                assert decision.response == "Normal response"
                mock_gen.assert_called_once()

    @pytest.mark.asyncio
    async def test_message_handler_boss_fight_no_skip(self):
        """Handler never skips during boss_fight."""
        from nikita.agents.text.handler import MessageHandler
        from nikita.agents.text.skip import SkipDecision

        # Create always-skip decision
        mock_skip = MagicMock(spec=SkipDecision)
        mock_skip.should_skip.return_value = True

        handler = MessageHandler(skip_decision=mock_skip)
        user_id = uuid4()

        with patch('nikita.agents.text.handler.get_nikita_agent_for_user') as mock_get:
            with patch('nikita.agents.text.handler.generate_response') as mock_gen:
                mock_agent = MagicMock()
                mock_deps = MagicMock()
                mock_deps.user.game_status = 'boss_fight'
                mock_deps.user.chapter = 2
                mock_deps.user.boss_attempts = 1
                mock_get.return_value = (mock_agent, mock_deps)
                mock_gen.return_value = "Challenge response"

                decision = await handler.handle(user_id, "My attempt")

                # Should NOT skip even with skip decision returning True
                assert decision.should_respond is True
                mock_skip.should_skip.assert_not_called()

    @pytest.mark.asyncio
    async def test_message_handler_game_over_blocked(self):
        """Handler blocks messages after game over."""
        from nikita.agents.text.handler import MessageHandler

        handler = MessageHandler()
        user_id = uuid4()

        with patch('nikita.agents.text.handler.get_nikita_agent_for_user') as mock_get:
            with patch('nikita.agents.text.handler.generate_response') as mock_gen:
                mock_agent = MagicMock()
                mock_deps = MagicMock()
                mock_deps.user.game_status = 'game_over'
                mock_deps.user.chapter = 2
                mock_get.return_value = (mock_agent, mock_deps)

                decision = await handler.handle(user_id, "Please!")

                assert decision.should_respond is True
                assert 'over' in decision.response.lower() or 'ended' in decision.response.lower()
                mock_gen.assert_not_called()


class TestDatabaseStateTransitions:
    """AC-T14-003: Database state transitions verified."""

    @pytest.mark.asyncio
    async def test_process_pass_calls_advance_chapter(self):
        """process_pass calls repository.advance_chapter."""
        from nikita.engine.chapters.boss import BossStateMachine

        sm = BossStateMachine()
        user_id = uuid4()

        with patch.object(sm, '_get_user_repo') as mock_get_repo:
            mock_repo = AsyncMock()
            mock_get_repo.return_value = mock_repo

            mock_user = MagicMock()
            mock_user.chapter = 3
            mock_user.game_status = 'active'
            mock_user.boss_attempts = 0
            mock_repo.advance_chapter.return_value = mock_user

            await sm.process_pass(user_id)

            mock_repo.advance_chapter.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_process_fail_calls_increment_boss_attempts(self):
        """process_fail calls repository.increment_boss_attempts."""
        from nikita.engine.chapters.boss import BossStateMachine

        sm = BossStateMachine()
        user_id = uuid4()

        with patch.object(sm, '_get_user_repo') as mock_get_repo:
            mock_repo = AsyncMock()
            mock_get_repo.return_value = mock_repo

            mock_user = MagicMock()
            mock_user.boss_attempts = 2
            mock_user.game_status = 'boss_fight'
            mock_repo.increment_boss_attempts.return_value = mock_user

            await sm.process_fail(user_id)

            mock_repo.increment_boss_attempts.assert_called_once_with(user_id)

    def test_boss_threshold_uses_constants(self):
        """Boss thresholds use engine constants."""
        from nikita.engine.chapters.boss import BossStateMachine
        from nikita.engine.constants import BOSS_THRESHOLDS

        sm = BossStateMachine()

        # Verify all 5 chapters have thresholds
        for chapter in range(1, 6):
            assert chapter in BOSS_THRESHOLDS

            # Check threshold logic
            threshold = BOSS_THRESHOLDS[chapter]
            result_below = sm.should_trigger_boss(
                relationship_score=threshold - Decimal("1"),
                chapter=chapter,
                game_status="active"
            )
            result_at = sm.should_trigger_boss(
                relationship_score=threshold,
                chapter=chapter,
                game_status="active"
            )

            assert result_below is False, f"Chapter {chapter} triggered below threshold"
            assert result_at is True, f"Chapter {chapter} didn't trigger at threshold"


class TestBossPromptContent:
    """Test boss prompt content for all chapters."""

    @pytest.mark.asyncio
    async def test_all_chapters_have_boss_prompts(self):
        """All 5 chapters have boss prompts with required fields."""
        from nikita.engine.chapters.boss import BossStateMachine

        sm = BossStateMachine()
        user_id = uuid4()

        for chapter in range(1, 6):
            prompt = await sm.initiate_boss(user_id, chapter=chapter)

            assert prompt['chapter'] == chapter
            assert 'challenge_context' in prompt
            assert 'success_criteria' in prompt
            assert 'in_character_opening' in prompt
            assert len(prompt['challenge_context']) > 0
            assert len(prompt['success_criteria']) > 0
            assert len(prompt['in_character_opening']) > 0

    def test_boss_thresholds_progression(self):
        """Boss thresholds increase with chapter."""
        from nikita.engine.constants import BOSS_THRESHOLDS

        thresholds = [BOSS_THRESHOLDS[ch] for ch in range(1, 6)]

        # Verify thresholds increase
        for i in range(len(thresholds) - 1):
            assert thresholds[i] < thresholds[i + 1], \
                f"Threshold {i+1} ({thresholds[i]}) should be less than {i+2} ({thresholds[i+1]})"
