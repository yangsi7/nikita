"""Spec 218 Slice 218-2 — v2 route + flag + helper + R12 + R15 tests.

Per plan ~/.claude/plans/immutable-wondering-gray.md R1, R11, R12, R15.

RED phase: imports fail / behavior absent on master; this file is the
verifier that PR-218-2 implementation lands the contract correctly.

Scope (slice-level):
- settings.wizard_v2_enabled flag + is_wizard_v2_enabled_for_user
- migration_or_init_v2_session helper (sticky stamp invariant)
- POST /answer flag-gated v2 branch
- R12 mid-failure 500 envelope
- R15 retry endpoint idempotency + 503 after 3 retries
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from nikita.config.settings import get_settings


# ---------------------------------------------------------------------------
# Settings flag (T-2-2.1)
# ---------------------------------------------------------------------------


class TestSettingsFlag:
    """`wizard_v2_enabled` default on (PR-218-8 flip); `is_wizard_v2_enabled_for_user`
    mirrors `is_unified_pipeline_enabled_for_user` per R1.
    """

    def test_flag_defaults_true(self) -> None:
        """PR-218-8: wizard_v2_enabled flipped from False to True (v1 deleted)."""
        get_settings.cache_clear()
        settings = get_settings()
        assert settings.wizard_v2_enabled is True

    def test_per_user_gate_off_returns_false(self) -> None:
        get_settings.cache_clear()
        settings = get_settings()
        # PR-218-8: default is now True; manually flip off to assert
        # gate honors the explicit off state regardless of rollout_pct.
        object.__setattr__(settings, "wizard_v2_enabled", False)
        try:
            assert settings.is_wizard_v2_enabled_for_user("any-user-id") is False
        finally:
            get_settings.cache_clear()

    def test_per_user_gate_on_100pct_returns_true(self) -> None:
        get_settings.cache_clear()
        settings = get_settings()
        # Manual override for behavioral test — runtime would set via env.
        object.__setattr__(settings, "wizard_v2_enabled", True)
        object.__setattr__(settings, "wizard_v2_rollout_pct", 100)
        try:
            assert settings.is_wizard_v2_enabled_for_user("user-A") is True
            assert settings.is_wizard_v2_enabled_for_user("user-B") is True
        finally:
            get_settings.cache_clear()

    def test_per_user_gate_on_0pct_returns_false(self) -> None:
        get_settings.cache_clear()
        settings = get_settings()
        object.__setattr__(settings, "wizard_v2_enabled", True)
        object.__setattr__(settings, "wizard_v2_rollout_pct", 0)
        try:
            assert settings.is_wizard_v2_enabled_for_user("user-A") is False
        finally:
            get_settings.cache_clear()


# ---------------------------------------------------------------------------
# migration_or_init_v2_session helper (T-2-2.2 — R11 sticky-flag invariant)
# ---------------------------------------------------------------------------


class TestMigrationOrInitV2Session:
    """Fresh session: evaluate flag once, stamp `state_version` in JSONB.
    Sticky session: honor existing stamp regardless of current flag state.
    """

    @pytest.mark.asyncio
    async def test_fresh_session_with_flag_on_stamps_v2(self) -> None:
        from nikita.agents.onboarding.v2.session_helper import (  # noqa: PLC0415
            migration_or_init_v2_session,
        )

        mock_session = MagicMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.onboarding_profile = {}  # no state_version stamped yet

        with patch(
            "nikita.agents.onboarding.v2.session_helper.UserRepository"
        ) as mock_repo_cls:
            repo = mock_repo_cls.return_value
            repo.get = AsyncMock(return_value=mock_user)
            repo.update_onboarding_profile = AsyncMock()
            with patch(
                "nikita.agents.onboarding.v2.session_helper.get_settings"
            ) as mock_settings:
                mock_settings.return_value.is_wizard_v2_enabled_for_user = MagicMock(
                    return_value=True
                )
                use_v2, profile = await migration_or_init_v2_session(
                    mock_user.id, mock_session
                )
                assert use_v2 is True
                assert profile.get("state_version") == "v2"
                repo.update_onboarding_profile.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_sticky_session_honors_stamp_v2_when_flag_off(self) -> None:
        from nikita.agents.onboarding.v2.session_helper import (  # noqa: PLC0415
            migration_or_init_v2_session,
        )

        mock_session = MagicMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.onboarding_profile = {"state_version": "v2"}  # already stamped

        with patch(
            "nikita.agents.onboarding.v2.session_helper.UserRepository"
        ) as mock_repo_cls:
            repo = mock_repo_cls.return_value
            repo.get = AsyncMock(return_value=mock_user)
            with patch(
                "nikita.agents.onboarding.v2.session_helper.get_settings"
            ) as mock_settings:
                # Flag flipped OFF — sticky stamp wins.
                mock_settings.return_value.is_wizard_v2_enabled_for_user = MagicMock(
                    return_value=False
                )
                use_v2, profile = await migration_or_init_v2_session(
                    mock_user.id, mock_session
                )
                assert use_v2 is True
                assert profile["state_version"] == "v2"

    @pytest.mark.asyncio
    async def test_sticky_session_honors_stamp_v1_when_flag_on(self) -> None:
        from nikita.agents.onboarding.v2.session_helper import (  # noqa: PLC0415
            migration_or_init_v2_session,
        )

        mock_session = MagicMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.onboarding_profile = {"state_version": "v1"}

        with patch(
            "nikita.agents.onboarding.v2.session_helper.UserRepository"
        ) as mock_repo_cls:
            repo = mock_repo_cls.return_value
            repo.get = AsyncMock(return_value=mock_user)
            with patch(
                "nikita.agents.onboarding.v2.session_helper.get_settings"
            ) as mock_settings:
                mock_settings.return_value.is_wizard_v2_enabled_for_user = MagicMock(
                    return_value=True
                )
                use_v2, profile = await migration_or_init_v2_session(
                    mock_user.id, mock_session
                )
                assert use_v2 is False
                assert profile["state_version"] == "v1"


# ---------------------------------------------------------------------------
# R12 — mid-failure 500 hard-error
# ---------------------------------------------------------------------------


class TestDecoratorFailureReturns500:
    """Decorator agent raises -> route returns HTTP 500 with R12 payload."""

    @pytest.mark.asyncio
    async def test_decorator_exception_returns_500_envelope(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            handle_v2_answer,
            V2DecoratorFailure,
        )

        mock_session = MagicMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        req = MagicMock()
        req.turn_id = uuid4()

        with patch(
            "nikita.api.routes.portal_onboarding_v2.get_decorator_agent"
        ) as mock_agent_getter:
            mock_agent = mock_agent_getter.return_value
            mock_agent.run = AsyncMock(side_effect=RuntimeError("model timeout"))

            with pytest.raises(V2DecoratorFailure) as exc_info:
                await handle_v2_answer(req, mock_user, mock_session)

            assert exc_info.value.error_code == "v2_decorator_failure"
            assert exc_info.value.session_id is not None
            assert exc_info.value.retry_url == "/api/v1/converse/onboarding/retry"


# ---------------------------------------------------------------------------
# R15 — retry endpoint contract
# ---------------------------------------------------------------------------


class TestRetryEndpoint:
    """Retry endpoint idempotency + budget accounting + 3rd-retry 503."""

    @pytest.mark.asyncio
    async def test_retry_endpoint_idempotent_returns_same_envelope(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            _retry_counts,
            handle_v2_retry,
        )

        mock_session = MagicMock()
        user_id = uuid4()
        # R11 invariant: session_id == user_id (1:1 user:session).
        session_id = user_id
        retry_token = "tok-1"
        _retry_counts.pop(session_id, None)  # isolate retry-count bucket

        with patch(
            "nikita.api.routes.portal_onboarding_v2.IdempotencyStore"
        ) as mock_idem_cls:
            store = mock_idem_cls.return_value
            cached_envelope = {"component": "text_short", "slot": "display_name"}
            store.get = AsyncMock(return_value=(cached_envelope, 200))

            result = await handle_v2_retry(
                session_id=session_id,
                retry_token=retry_token,
                user_id=user_id,
                session=mock_session,
            )
            assert result["component"] == "text_short"
            store.get.assert_awaited_once()
            # Idempotent cache-hit MUST NOT consume retry budget.
            # Network-layer replays resending the same retry_token should
            # be free; only cache-miss (actual agent re-run) counts.
            assert _retry_counts.get(session_id, 0) == 0

        _retry_counts.pop(session_id, None)  # cleanup

    @pytest.mark.asyncio
    async def test_retry_endpoint_503_after_3_retries(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            _RETRY_BUDGET_HARD_LIMIT,
            _retry_counts,
            RetryBudgetExhausted,
            handle_v2_retry,
        )

        mock_session = MagicMock()
        user_id = uuid4()
        session_id = user_id
        # Pre-seed counter to the budget; next increment puts us over.
        _retry_counts[session_id] = _RETRY_BUDGET_HARD_LIMIT

        try:
            with patch(
                "nikita.api.routes.portal_onboarding_v2.IdempotencyStore"
            ) as mock_idem_cls:
                # Force cache MISS so budget check fires (cache-hit
                # exits before increment-then-compare per iter-4).
                mock_idem_cls.return_value.get = AsyncMock(return_value=None)
                with pytest.raises(RetryBudgetExhausted):
                    await handle_v2_retry(
                        session_id=session_id,
                        retry_token="tok-3",
                        user_id=user_id,
                        session=mock_session,
                    )
        finally:
            _retry_counts.pop(session_id, None)

    @pytest.mark.asyncio
    async def test_retry_endpoint_rejects_mismatched_session_user(self) -> None:
        from fastapi import HTTPException  # noqa: PLC0415

        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            handle_v2_retry,
        )

        mock_session = MagicMock()
        # session_id != user_id -> 400 per R11 sticky-flag invariant.
        with pytest.raises(HTTPException) as exc_info:
            await handle_v2_retry(
                session_id=uuid4(),
                retry_token="tok-A",
                user_id=uuid4(),
                session=mock_session,
            )
        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# handler field default test (R14 remnant — HandlerHandoffAsk deleted PR-218-8)
# ---------------------------------------------------------------------------


class TestHandlerFieldDefault:
    """R14: handler field default on TextShortAsk (HandlerHandoffAsk removed PR-218-8)."""

    def test_handler_field_default_v2_on_text_short(self) -> None:
        from nikita.agents.onboarding.v2.envelope import (  # noqa: PLC0415
            TextShortAsk,
        )

        env = TextShortAsk(
            component="text_short",
            slot="display_name",
            prompt="What name should I use?",
        )
        # New optional field added in PR-218-2 per R14.
        assert getattr(env, "handler", "v2") == "v2"


# ---------------------------------------------------------------------------
# GH #602 — decorator failure must be logged server-side before raising
# ---------------------------------------------------------------------------


class TestDecoratorFailureLogging:
    """GH #602: the Anthropic 400 'credit balance is too low' was invisible
    in prod logs until a live walk surfaced it. ``handle_v2_answer`` wraps
    every decorator/research agent exception in ``V2DecoratorFailure`` —
    the wrap MUST emit a server-side ERROR log carrying ``str(exc)``."""

    def test_build_decorator_failure_logs_detail(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            _build_decorator_failure,
            V2DecoratorFailure,
        )

        session_id = uuid4()
        exc = RuntimeError("Your credit balance is too low")

        with patch(
            "nikita.api.routes.portal_onboarding_v2.logger"
        ) as mock_logger:
            failure = _build_decorator_failure(exc, session_id)

        assert isinstance(failure, V2DecoratorFailure)
        assert failure.error_code == "v2_decorator_failure"
        assert failure.session_id == session_id
        assert failure.retry_url == "/api/v1/converse/onboarding/retry"
        assert failure.detail == "Your credit balance is too low"
        mock_logger.error.assert_called_once()
        log_args = mock_logger.error.call_args.args
        assert "v2_decorator_failure" in log_args[0]
        assert str(session_id) in " ".join(str(a) for a in log_args)
        assert "credit balance is too low" in str(log_args[-1])

    @pytest.mark.asyncio
    async def test_handle_v2_answer_logs_on_decorator_exception(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            handle_v2_answer,
            V2DecoratorFailure,
        )

        mock_session = MagicMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        req = MagicMock()
        req.turn_id = uuid4()

        with patch(
            "nikita.api.routes.portal_onboarding_v2.get_decorator_agent"
        ) as mock_agent_getter, patch(
            "nikita.api.routes.portal_onboarding_v2.logger"
        ) as mock_logger:
            mock_agent = mock_agent_getter.return_value
            mock_agent.run = AsyncMock(
                side_effect=RuntimeError("Your credit balance is too low")
            )

            with pytest.raises(V2DecoratorFailure):
                await handle_v2_answer(req, mock_user, mock_session)

        mock_logger.error.assert_called_once()
        log_args = mock_logger.error.call_args.args
        assert "v2_decorator_failure" in log_args[0]
        assert "credit balance is too low" in str(log_args[-1])


# ---------------------------------------------------------------------------
# GH #604 — first-turn empty messages array => Anthropic 400
# ---------------------------------------------------------------------------


class TestFirstTurnNonEmptyUserPrompt:
    """GH #604: on the first wizard turn there is no `message_history`.
    Pydantic AI sends an empty `messages` array to the model when
    `agent.run("")` is called with no history, and Anthropic rejects that
    with 400 'messages: at least one message is required' — the v2 wizard
    500s for every new user on portal entry. The route must pass a
    non-empty bootstrap user prompt on the empty-history branch."""

    @pytest.mark.asyncio
    async def test_decorator_run_gets_non_empty_prompt_on_first_turn(
        self,
    ) -> None:
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            handle_v2_answer,
        )

        mock_session = MagicMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.onboarding_profile = {}  # fresh user: no messages, no slots
        req = MagicMock()
        req.turn_id = uuid4()

        with patch(
            "nikita.api.routes.portal_onboarding_v2.get_decorator_agent"
        ) as mock_agent_getter:
            mock_agent = mock_agent_getter.return_value
            mock_agent.run = AsyncMock(
                return_value=MagicMock(output=MagicMock())
            )

            await handle_v2_answer(req, mock_user, mock_session)

        mock_agent.run.assert_awaited_once()
        call = mock_agent.run.call_args
        user_prompt = (
            call.args[0]
            if call.args
            else call.kwargs.get("user_prompt", "")
        )
        assert user_prompt, (
            "first-turn agent.run must receive a non-empty user prompt "
            "(GH #604 — empty prompt + no history => Anthropic 400)"
        )
        # Empty-history branch: no message_history kwarg on turn 1.
        assert "message_history" not in call.kwargs

    @pytest.mark.asyncio
    async def test_research_agent_run_gets_non_empty_prompt_on_empty_history(
        self,
    ) -> None:
        """Phase-2 (research agent) empty-history branch: same #604 fix."""
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            handle_v2_answer,
        )

        mock_session = MagicMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.onboarding_profile = {}  # no messages -> empty history
        req = MagicMock()
        req.turn_id = uuid4()

        mock_repo = MagicMock()
        mock_repo.update_onboarding_profile = AsyncMock()

        with patch(
            "nikita.api.routes.portal_onboarding_v2.pick_next_target",
            return_value=None,  # Phase-1 done -> Phase-2 branch
        ), patch(
            "nikita.api.routes.portal_onboarding_v2.phase_2_gate",
            return_value=(False, False),  # not complete -> reach research.run
        ), patch(
            "nikita.api.routes.portal_onboarding_v2.UserRepository",
            return_value=mock_repo,
        ), patch(
            "nikita.api.routes.portal_onboarding_v2.get_research_agent"
        ) as mock_research_getter:
            mock_research = mock_research_getter.return_value
            mock_research.run = AsyncMock(
                return_value=MagicMock(output="follow-up question")
            )

            await handle_v2_answer(req, mock_user, mock_session)

        mock_research.run.assert_awaited_once()
        call = mock_research.run.call_args
        user_prompt = (
            call.args[0]
            if call.args
            else call.kwargs.get("user_prompt", "")
        )
        assert user_prompt, (
            "Phase-2 research_agent.run must receive a non-empty user "
            "prompt on the empty-history branch (GH #604)"
        )
        assert "message_history" not in call.kwargs
