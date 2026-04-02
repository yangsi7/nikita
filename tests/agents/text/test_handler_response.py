"""Tests for Handler Response Behavior — Spec 204: Always Respond.

Replaces skip-based tests (test_handler_skip.py) with 100% response rate tests.

Acceptance Criteria:
- AC-T3.1: Handler no longer calls should_skip()
- AC-T3.2: should_respond always True for active state
- AC-T3.3: Engagement state loaded from user model (with try/except)
- AC-T3.4: First message detected via last_interaction_at is None
- AC-T3.5: engagement_state + is_first_message passed to timer
- AC-T3.6: Boss fight: delay=0, no multiplier
- AC-T3.7: skip.py has deprecation docstring
- AC-T3.8: skip_rates_enabled default = False
- AC-T3.9: 9+ handler response tests pass
- AC-T3.10: 3 skip deprecation tests pass
- AC-T3.11: [TIMING] First message log emitted
"""

import pytest

pytestmark = pytest.mark.asyncio(loop_scope="function")

from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
import logging


def _make_mock_user(
    game_status="active",
    chapter=1,
    engagement_state_value="calibrating",
    last_interaction_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
):
    """Create a mock user with engagement state and last_interaction_at."""
    user = MagicMock()
    user.id = uuid4()
    user.game_status = game_status
    user.chapter = chapter
    user.last_interaction_at = last_interaction_at

    # Engagement state relationship
    if engagement_state_value is not None:
        eng = MagicMock()
        eng.state = engagement_state_value
        user.engagement_state = eng
    else:
        user.engagement_state = None

    return user


def _make_mock_deps(user):
    """Create mock deps with user."""
    deps = MagicMock()
    deps.user = user
    deps.conversation_messages = None
    deps.conversation_id = None
    deps.session = None
    deps.psyche_state = None
    return deps


class TestHandlerAlwaysResponds:
    """AC-T3.1, AC-T3.2: Handler never skips, always responds for active users."""

    async def test_ac_t3_1_no_should_skip_call(self):
        """AC-T3.1: Handler should NOT call should_skip()."""
        from nikita.agents.text.handler import MessageHandler
        from nikita.agents.text.skip import SkipDecision

        user = _make_mock_user(game_status="active", chapter=1)
        deps = _make_mock_deps(user)

        mock_skip = MagicMock(spec=SkipDecision)
        handler = MessageHandler(skip_decision=mock_skip)

        with (
            patch("nikita.agents.text.handler.get_nikita_agent_for_user", new_callable=AsyncMock) as mock_agent,
            patch("nikita.agents.text.handler.generate_response", new_callable=AsyncMock) as mock_gen,
            patch("nikita.agents.text.handler.store_pending_response", new_callable=AsyncMock),
            patch("nikita.agents.text.handler._get_processor_instance") as mock_proc,
        ):
            mock_agent.return_value = (MagicMock(), deps)
            mock_gen.return_value = "Hello!"
            mock_proc.return_value.process.return_value = "Hello!"

            result = await handler.handle(user.id, "Hey")

            # should_skip should NOT be called
            mock_skip.should_skip.assert_not_called()

    async def test_ac_t3_2_always_responds_active(self):
        """AC-T3.2: should_respond is always True for active game_status."""
        from nikita.agents.text.handler import MessageHandler

        user = _make_mock_user(game_status="active", chapter=3)
        deps = _make_mock_deps(user)

        handler = MessageHandler()

        with (
            patch("nikita.agents.text.handler.get_nikita_agent_for_user", new_callable=AsyncMock) as mock_agent,
            patch("nikita.agents.text.handler.generate_response", new_callable=AsyncMock) as mock_gen,
            patch("nikita.agents.text.handler.store_pending_response", new_callable=AsyncMock),
            patch("nikita.agents.text.handler._get_processor_instance") as mock_proc,
        ):
            mock_agent.return_value = (MagicMock(), deps)
            mock_gen.return_value = "Response text"
            mock_proc.return_value.process.return_value = "Response text"

            result = await handler.handle(user.id, "Hello")

            assert result.should_respond is True
            assert result.response == "Response text"

    async def test_always_responds_all_chapters(self):
        """Handler should respond for all chapters 1-5."""
        from nikita.agents.text.handler import MessageHandler

        for ch in [1, 2, 3, 4, 5]:
            user = _make_mock_user(game_status="active", chapter=ch)
            deps = _make_mock_deps(user)

            handler = MessageHandler()

            with (
                patch("nikita.agents.text.handler.get_nikita_agent_for_user", new_callable=AsyncMock) as mock_agent,
                patch("nikita.agents.text.handler.generate_response", new_callable=AsyncMock) as mock_gen,
                patch("nikita.agents.text.handler.store_pending_response", new_callable=AsyncMock),
                patch("nikita.agents.text.handler._get_processor_instance") as mock_proc,
            ):
                mock_agent.return_value = (MagicMock(), deps)
                mock_gen.return_value = f"Ch{ch} response"
                mock_proc.return_value.process.return_value = f"Ch{ch} response"

                result = await handler.handle(user.id, "Hi")
                assert result.should_respond is True, f"Ch{ch} should respond"


class TestEngagementStateLoading:
    """AC-T3.3: Engagement state loaded from user model."""

    async def test_ac_t3_3_engagement_state_passed_to_timer(self):
        """AC-T3.3/T3.5: Engagement state passed to calculate_delay."""
        from nikita.agents.text.handler import MessageHandler
        from nikita.agents.text.timing import ResponseTimer

        user = _make_mock_user(
            game_status="active", chapter=2,
            engagement_state_value="drifting",
        )
        deps = _make_mock_deps(user)

        mock_timer = MagicMock(spec=ResponseTimer)
        mock_timer.calculate_delay.return_value = 10

        handler = MessageHandler(timer=mock_timer)

        with (
            patch("nikita.agents.text.handler.get_nikita_agent_for_user", new_callable=AsyncMock) as mock_agent,
            patch("nikita.agents.text.handler.generate_response", new_callable=AsyncMock) as mock_gen,
            patch("nikita.agents.text.handler.store_pending_response", new_callable=AsyncMock),
            patch("nikita.agents.text.handler._get_processor_instance") as mock_proc,
        ):
            mock_agent.return_value = (MagicMock(), deps)
            mock_gen.return_value = "Quick response"
            mock_proc.return_value.process.return_value = "Quick response"

            await handler.handle(user.id, "Hello")

            # Timer should receive engagement_state
            mock_timer.calculate_delay.assert_called_once()
            call_kwargs = mock_timer.calculate_delay.call_args
            assert call_kwargs[1].get("engagement_state") == "drifting" or \
                   (len(call_kwargs[0]) > 1 and call_kwargs[0][1] == "drifting") or \
                   call_kwargs.kwargs.get("engagement_state") == "drifting"

    async def test_ac_t3_3_no_engagement_state_defaults_calibrating(self):
        """AC-T3.3: No engagement_state defaults to 'calibrating'."""
        from nikita.agents.text.handler import MessageHandler
        from nikita.agents.text.timing import ResponseTimer

        user = _make_mock_user(
            game_status="active", chapter=1,
            engagement_state_value=None,  # No engagement state
        )
        deps = _make_mock_deps(user)

        mock_timer = MagicMock(spec=ResponseTimer)
        mock_timer.calculate_delay.return_value = 5

        handler = MessageHandler(timer=mock_timer)

        with (
            patch("nikita.agents.text.handler.get_nikita_agent_for_user", new_callable=AsyncMock) as mock_agent,
            patch("nikita.agents.text.handler.generate_response", new_callable=AsyncMock) as mock_gen,
            patch("nikita.agents.text.handler.store_pending_response", new_callable=AsyncMock),
            patch("nikita.agents.text.handler._get_processor_instance") as mock_proc,
        ):
            mock_agent.return_value = (MagicMock(), deps)
            mock_gen.return_value = "Response"
            mock_proc.return_value.process.return_value = "Response"

            await handler.handle(user.id, "Hello")

            call_kwargs = mock_timer.calculate_delay.call_args
            assert call_kwargs.kwargs.get("engagement_state") == "calibrating"


class TestFirstMessageDetection:
    """AC-T3.4, AC-T3.5, AC-T3.11: First-message detection."""

    async def test_ac_t3_4_first_message_detected(self):
        """AC-T3.4: First message detected via last_interaction_at is None."""
        from nikita.agents.text.handler import MessageHandler
        from nikita.agents.text.timing import ResponseTimer

        user = _make_mock_user(
            game_status="active", chapter=1,
            last_interaction_at=None,  # Brand new user
        )
        deps = _make_mock_deps(user)

        mock_timer = MagicMock(spec=ResponseTimer)
        mock_timer.calculate_delay.return_value = 10

        handler = MessageHandler(timer=mock_timer)

        with (
            patch("nikita.agents.text.handler.get_nikita_agent_for_user", new_callable=AsyncMock) as mock_agent,
            patch("nikita.agents.text.handler.generate_response", new_callable=AsyncMock) as mock_gen,
            patch("nikita.agents.text.handler.store_pending_response", new_callable=AsyncMock),
            patch("nikita.agents.text.handler._get_processor_instance") as mock_proc,
        ):
            mock_agent.return_value = (MagicMock(), deps)
            mock_gen.return_value = "Welcome!"
            mock_proc.return_value.process.return_value = "Welcome!"

            await handler.handle(user.id, "Hi!")

            call_kwargs = mock_timer.calculate_delay.call_args
            assert call_kwargs.kwargs.get("is_first_message") is True

    async def test_not_first_message_when_has_interaction(self):
        """Not first message when last_interaction_at has a value."""
        from nikita.agents.text.handler import MessageHandler
        from nikita.agents.text.timing import ResponseTimer

        user = _make_mock_user(
            game_status="active", chapter=2,
            last_interaction_at=datetime(2026, 3, 15, tzinfo=timezone.utc),
        )
        deps = _make_mock_deps(user)

        mock_timer = MagicMock(spec=ResponseTimer)
        mock_timer.calculate_delay.return_value = 60

        handler = MessageHandler(timer=mock_timer)

        with (
            patch("nikita.agents.text.handler.get_nikita_agent_for_user", new_callable=AsyncMock) as mock_agent,
            patch("nikita.agents.text.handler.generate_response", new_callable=AsyncMock) as mock_gen,
            patch("nikita.agents.text.handler.store_pending_response", new_callable=AsyncMock),
            patch("nikita.agents.text.handler._get_processor_instance") as mock_proc,
        ):
            mock_agent.return_value = (MagicMock(), deps)
            mock_gen.return_value = "Hey again"
            mock_proc.return_value.process.return_value = "Hey again"

            await handler.handle(user.id, "Hey")

            call_kwargs = mock_timer.calculate_delay.call_args
            assert call_kwargs.kwargs.get("is_first_message") is False


class TestBossFightTiming:
    """AC-T3.6: Boss fight: delay=0, no engagement multiplier."""

    async def test_ac_t3_6_boss_fight_delay_zero(self):
        """AC-T3.6: Boss fight always has delay=0."""
        from nikita.agents.text.handler import MessageHandler

        user = _make_mock_user(game_status="boss_fight", chapter=3)
        deps = _make_mock_deps(user)

        handler = MessageHandler()

        with (
            patch("nikita.agents.text.handler.get_nikita_agent_for_user", new_callable=AsyncMock) as mock_agent,
            patch("nikita.agents.text.handler.generate_response", new_callable=AsyncMock) as mock_gen,
            patch("nikita.agents.text.handler._get_processor_instance") as mock_proc,
        ):
            mock_agent.return_value = (MagicMock(), deps)
            mock_gen.return_value = "Challenge accepted"
            mock_proc.return_value.process.return_value = "Challenge accepted"

            result = await handler.handle(user.id, "I think...")

            assert result.delay_seconds == 0
            assert result.should_respond is True


class TestSkipDeprecation:
    """AC-T3.7, AC-T3.8, AC-T3.10: Skip module deprecation."""

    def test_ac_t3_7_skip_module_has_deprecation_docstring(self):
        """AC-T3.7: skip.py has deprecation docstring at module level."""
        import nikita.agents.text.skip as skip_module

        docstring = skip_module.__doc__
        assert docstring is not None
        assert "deprecated" in docstring.lower() or "DEPRECATED" in docstring

    def test_ac_t3_8_skip_rates_enabled_default_false(self):
        """AC-T3.8: skip_rates_enabled defaults to False."""
        from nikita.config.settings import Settings

        s = Settings()
        assert s.skip_rates_enabled is False

    def test_skip_decision_class_still_exists(self):
        """Skip module should still be importable for backward compat."""
        from nikita.agents.text.skip import SkipDecision, SKIP_RATES

        assert SkipDecision is not None
        assert isinstance(SKIP_RATES, dict)
        assert len(SKIP_RATES) == 5
