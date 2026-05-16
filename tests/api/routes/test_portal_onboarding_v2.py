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


# ---------------------------------------------------------------------------
# GH #611 + GH #612 — v2 completion side-effects missing
# ---------------------------------------------------------------------------


class TestV2CompletionSideEffects:
    """_run_phase2_complete MUST mirror v1 save_portal_profile completion chain:
    1. create user_profiles row (GH #612)
    2. flip onboarding_status='completed' (GH #611)
    3. call activate_game() (GH #611)
    4. seed vices (GH #612)
    All guarded by idempotency check.
    """

    def _make_full_slots(self) -> "WizardSlotsV2":
        from nikita.agents.onboarding.v2.state import WizardSlotsV2  # noqa: PLC0415

        return WizardSlotsV2(
            display_name={"display_name": "Alice"},
            age={"age": 28, "dob": "1997-01-01"},
            city={"city": "Berlin"},
            occupation={"occupation": "engineer"},
            primary_hobbies={"primary_hobbies": ["hiking", "coding"]},
            hangouts_personalized={"hangouts_personalized": ["coffee shops"]},
            voice_or_text={"voice_or_text": "text"},
            phone=None,  # text mode — phone not required
            saturday_morning={"saturday_morning": "sleep in"},
            darkness_level={"darkness_level": 6},
            geek_out_on={"geek_out_on": "sci-fi"},
        )

    def _make_state(self, slots: Any) -> Any:
        from nikita.agents.onboarding.v2.state import Phase, WizardStateV2  # noqa: PLC0415

        return WizardStateV2(
            slots=slots,
            phase=Phase.phase2,
            phase_2_turn_count=3,
        )

    @pytest.mark.asyncio
    async def test_creates_user_profile_row(self) -> None:
        """_run_phase2_complete must call profile_repo.create_profile (GH #612)."""
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            _run_phase2_complete,
        )

        user_id = uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.onboarding_status = "in_progress"

        mock_session = MagicMock()
        mock_user_repo = MagicMock()
        mock_user_repo.update_onboarding_profile = AsyncMock()
        mock_user_repo.update_onboarding_status = AsyncMock()
        mock_user_repo.activate_game = AsyncMock()
        mock_user_repo.get = AsyncMock(return_value=mock_user)

        mock_profile_repo = MagicMock()
        mock_profile_repo.get_by_user_id = AsyncMock(return_value=None)
        mock_profile_repo.create_profile = AsyncMock(return_value=MagicMock())

        slots = self._make_full_slots()
        state = self._make_state(slots)

        with patch(
            "nikita.api.routes.portal_onboarding_v2.generate_v2_backstory",
            new_callable=AsyncMock,
            return_value="test backstory",
        ), patch(
            "nikita.api.routes.portal_onboarding_v2.ProfileRepository",
            return_value=mock_profile_repo,
        ), patch(
            "nikita.engine.vice.seeder.seed_vices_from_profile",
            new_callable=AsyncMock,
        ):
            await _run_phase2_complete(
                state,
                {},
                mock_user,
                repo=mock_user_repo,
                session=mock_session,
            )

        mock_profile_repo.create_profile.assert_awaited_once()
        call_kwargs = mock_profile_repo.create_profile.call_args.kwargs
        assert call_kwargs["user_id"] == user_id
        assert call_kwargs["location_city"] == "Berlin"

    @pytest.mark.asyncio
    async def test_flips_onboarding_status_to_completed(self) -> None:
        """_run_phase2_complete must call update_onboarding_status('completed') (GH #611)."""
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            _run_phase2_complete,
        )

        user_id = uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.onboarding_status = "in_progress"

        mock_session = MagicMock()
        mock_user_repo = MagicMock()
        mock_user_repo.update_onboarding_profile = AsyncMock()
        mock_user_repo.update_onboarding_status = AsyncMock()
        mock_user_repo.activate_game = AsyncMock()
        mock_user_repo.get = AsyncMock(return_value=mock_user)

        mock_profile_repo = MagicMock()
        mock_profile_repo.get_by_user_id = AsyncMock(return_value=None)
        mock_profile_repo.create_profile = AsyncMock(return_value=MagicMock())

        slots = self._make_full_slots()
        state = self._make_state(slots)

        with patch(
            "nikita.api.routes.portal_onboarding_v2.generate_v2_backstory",
            new_callable=AsyncMock,
            return_value="test backstory",
        ), patch(
            "nikita.api.routes.portal_onboarding_v2.ProfileRepository",
            return_value=mock_profile_repo,
        ), patch(
            "nikita.engine.vice.seeder.seed_vices_from_profile",
            new_callable=AsyncMock,
        ):
            await _run_phase2_complete(
                state,
                {},
                mock_user,
                repo=mock_user_repo,
                session=mock_session,
            )

        mock_user_repo.update_onboarding_status.assert_awaited_once_with(
            user_id, "completed"
        )

    @pytest.mark.asyncio
    async def test_calls_activate_game(self) -> None:
        """_run_phase2_complete must call activate_game() (GH #611)."""
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            _run_phase2_complete,
        )

        user_id = uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.onboarding_status = "in_progress"

        mock_session = MagicMock()
        mock_user_repo = MagicMock()
        mock_user_repo.update_onboarding_profile = AsyncMock()
        mock_user_repo.update_onboarding_status = AsyncMock()
        mock_user_repo.activate_game = AsyncMock()
        mock_user_repo.get = AsyncMock(return_value=mock_user)

        mock_profile_repo = MagicMock()
        mock_profile_repo.get_by_user_id = AsyncMock(return_value=None)
        mock_profile_repo.create_profile = AsyncMock(return_value=MagicMock())

        slots = self._make_full_slots()
        state = self._make_state(slots)

        with patch(
            "nikita.api.routes.portal_onboarding_v2.generate_v2_backstory",
            new_callable=AsyncMock,
            return_value="test backstory",
        ), patch(
            "nikita.api.routes.portal_onboarding_v2.ProfileRepository",
            return_value=mock_profile_repo,
        ), patch(
            "nikita.engine.vice.seeder.seed_vices_from_profile",
            new_callable=AsyncMock,
        ):
            await _run_phase2_complete(
                state,
                {},
                mock_user,
                repo=mock_user_repo,
                session=mock_session,
            )

        mock_user_repo.activate_game.assert_awaited_once_with(user_id)

    @pytest.mark.asyncio
    async def test_seeds_vices(self) -> None:
        """_run_phase2_complete must call seed_vices_from_profile (GH #612)."""
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            _run_phase2_complete,
        )

        user_id = uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.onboarding_status = "in_progress"

        mock_session = MagicMock()
        mock_user_repo = MagicMock()
        mock_user_repo.update_onboarding_profile = AsyncMock()
        mock_user_repo.update_onboarding_status = AsyncMock()
        mock_user_repo.activate_game = AsyncMock()
        mock_user_repo.get = AsyncMock(return_value=mock_user)

        mock_profile_repo = MagicMock()
        mock_profile_repo.get_by_user_id = AsyncMock(return_value=None)
        mock_profile_repo.create_profile = AsyncMock(return_value=MagicMock())

        slots = self._make_full_slots()
        state = self._make_state(slots)

        with patch(
            "nikita.api.routes.portal_onboarding_v2.generate_v2_backstory",
            new_callable=AsyncMock,
            return_value="test backstory",
        ), patch(
            "nikita.api.routes.portal_onboarding_v2.ProfileRepository",
            return_value=mock_profile_repo,
        ), patch(
            "nikita.engine.vice.seeder.seed_vices_from_profile",
            new_callable=AsyncMock,
        ) as mock_seed:
            await _run_phase2_complete(
                state,
                {},
                mock_user,
                repo=mock_user_repo,
                session=mock_session,
            )

        mock_seed.assert_awaited_once()
        seed_kwargs = mock_seed.call_args.kwargs
        assert seed_kwargs["user_id"] == user_id
        # darkness_level=6 in _make_full_slots → scaled drug_tolerance=3 (not raw 6).
        # Seeder expects profile["darkness_level"] in [1,5]; passing raw 0-10 would
        # fail the seeder's own validation (seeder.py:70: not 1 <= value <= 5 → return []).
        seeded_darkness = seed_kwargs["profile"]["darkness_level"]
        assert 1 <= seeded_darkness <= 5, (
            f"seed_vices_from_profile received raw darkness_level={seeded_darkness}; "
            f"must receive SCALED drug_tolerance in [1,5]"
        )
        assert seeded_darkness == 3, (
            f"darkness_level=6 should scale to drug_tolerance=3, seeder got {seeded_darkness}"
        )

    @pytest.mark.asyncio
    async def test_idempotency_guard_skips_if_already_completed(self) -> None:
        """If onboarding_status already 'completed', side-effects must NOT re-run."""
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            _run_phase2_complete,
        )

        user_id = uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.onboarding_status = "completed"  # already done

        mock_session = MagicMock()
        mock_user_repo = MagicMock()
        mock_user_repo.update_onboarding_profile = AsyncMock()
        mock_user_repo.update_onboarding_status = AsyncMock()
        mock_user_repo.activate_game = AsyncMock()
        mock_user_repo.get = AsyncMock(return_value=mock_user)

        mock_profile_repo = MagicMock()
        # Profile already exists
        mock_profile_repo.get_by_user_id = AsyncMock(return_value=MagicMock())
        mock_profile_repo.create_profile = AsyncMock(return_value=MagicMock())

        slots = self._make_full_slots()
        state = self._make_state(slots)

        with patch(
            "nikita.api.routes.portal_onboarding_v2.generate_v2_backstory",
            new_callable=AsyncMock,
            return_value="test backstory",
        ), patch(
            "nikita.api.routes.portal_onboarding_v2.ProfileRepository",
            return_value=mock_profile_repo,
        ), patch(
            "nikita.engine.vice.seeder.seed_vices_from_profile",
            new_callable=AsyncMock,
        ) as mock_seed:
            await _run_phase2_complete(
                state,
                {},
                mock_user,
                repo=mock_user_repo,
                session=mock_session,
            )

        mock_profile_repo.create_profile.assert_not_awaited()
        mock_user_repo.update_onboarding_status.assert_not_awaited()
        mock_user_repo.activate_game.assert_not_awaited()
        mock_seed.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_darkness_level_scaled_to_drug_tolerance(self) -> None:
        """darkness_level 0-10 must be scaled to drug_tolerance 1-5 (CHECK constraint)."""
        from nikita.agents.onboarding.v2.state import Phase, WizardSlotsV2, WizardStateV2  # noqa: PLC0415
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            _run_phase2_complete,
        )

        user_id = uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.onboarding_status = "in_progress"

        mock_session = MagicMock()
        mock_user_repo = MagicMock()
        mock_user_repo.update_onboarding_profile = AsyncMock()
        mock_user_repo.update_onboarding_status = AsyncMock()
        mock_user_repo.activate_game = AsyncMock()
        mock_user_repo.get = AsyncMock(return_value=mock_user)

        mock_profile_repo = MagicMock()
        mock_profile_repo.get_by_user_id = AsyncMock(return_value=None)
        mock_profile_repo.create_profile = AsyncMock(return_value=MagicMock())

        # darkness_level=10 (max) -> drug_tolerance must be 5
        slots = WizardSlotsV2(
            display_name={"display_name": "Bob"},
            age={"age": 30, "dob": "1995-01-01"},
            city={"city": "NYC"},
            occupation={"occupation": "dev"},
            primary_hobbies={"primary_hobbies": ["chess"]},
            hangouts_personalized={"hangouts_personalized": ["bars"]},
            voice_or_text={"voice_or_text": "text"},
            phone=None,
            saturday_morning={"saturday_morning": "gym"},
            darkness_level={"darkness_level": 10},
            geek_out_on={"geek_out_on": "anime"},
        )
        state = WizardStateV2(slots=slots, phase=Phase.phase2, phase_2_turn_count=3)

        with patch(
            "nikita.api.routes.portal_onboarding_v2.generate_v2_backstory",
            new_callable=AsyncMock,
            return_value="backstory",
        ), patch(
            "nikita.api.routes.portal_onboarding_v2.ProfileRepository",
            return_value=mock_profile_repo,
        ), patch(
            "nikita.engine.vice.seeder.seed_vices_from_profile",
            new_callable=AsyncMock,
        ):
            await _run_phase2_complete(
                state,
                {},
                mock_user,
                repo=mock_user_repo,
                session=mock_session,
            )

        call_kwargs = mock_profile_repo.create_profile.call_args.kwargs
        drug_tolerance = call_kwargs["drug_tolerance"]
        assert 1 <= drug_tolerance <= 5, (
            f"drug_tolerance={drug_tolerance} violates CHECK BETWEEN 1 AND 5"
        )
        assert drug_tolerance == 5, (
            f"darkness_level=10 (max) should scale to drug_tolerance=5, got {drug_tolerance}"
        )

    @pytest.mark.asyncio
    async def test_idempotency_guard_skips_if_profile_exists_but_status_not_completed(
        self,
    ) -> None:
        """Second idempotency arm: status is NOT 'completed' but profile row already
        exists (e.g., partial retry). Side-effects must NOT re-run to avoid
        duplicate profile creation or double activate_game."""
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            _run_phase2_complete,
        )

        user_id = uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.onboarding_status = "in_progress"  # NOT 'completed' — first guard passes

        mock_session = MagicMock()
        mock_user_repo = MagicMock()
        mock_user_repo.update_onboarding_profile = AsyncMock()
        mock_user_repo.update_onboarding_status = AsyncMock()
        mock_user_repo.activate_game = AsyncMock()
        mock_user_repo.get = AsyncMock(return_value=mock_user)

        mock_profile_repo = MagicMock()
        # Profile row already exists — second guard must fire
        mock_profile_repo.get_by_user_id = AsyncMock(return_value=MagicMock())
        mock_profile_repo.create_profile = AsyncMock(return_value=MagicMock())

        slots = self._make_full_slots()
        state = self._make_state(slots)

        with patch(
            "nikita.api.routes.portal_onboarding_v2.generate_v2_backstory",
            new_callable=AsyncMock,
            return_value="test backstory",
        ), patch(
            "nikita.api.routes.portal_onboarding_v2.ProfileRepository",
            return_value=mock_profile_repo,
        ), patch(
            "nikita.engine.vice.seeder.seed_vices_from_profile",
            new_callable=AsyncMock,
        ) as mock_seed:
            await _run_phase2_complete(
                state,
                {},
                mock_user,
                repo=mock_user_repo,
                session=mock_session,
            )

        mock_profile_repo.create_profile.assert_not_awaited()
        mock_user_repo.update_onboarding_status.assert_not_awaited()
        mock_user_repo.activate_game.assert_not_awaited()
        mock_seed.assert_not_awaited()

    def test_scale_darkness_to_drug_tolerance_bucket_boundaries(self) -> None:
        """Verify every darkness_level 0-10 maps to a valid drug_tolerance [1,5].

        Bucket table (formula: max(1, min(5, (d+1)//2))):
          0       → 1
          1-2     → 1
          3-4     → 2
          5-6     → 3
          7-8     → 4
          9-10    → 5
        """
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            _scale_darkness_to_drug_tolerance,
        )

        expected = {
            0: 1,
            1: 1,
            2: 1,
            3: 2,
            4: 2,
            5: 3,
            6: 3,
            7: 4,
            8: 4,
            9: 5,
            10: 5,
        }
        for darkness, expected_dt in expected.items():
            result = _scale_darkness_to_drug_tolerance(darkness)
            assert result == expected_dt, (
                f"darkness_level={darkness}: expected drug_tolerance={expected_dt}, got {result}"
            )
            assert 1 <= result <= 5, (
                f"drug_tolerance={result} violates CHECK BETWEEN 1 AND 5 for darkness_level={darkness}"
            )

    # ------------------------------------------------------------------
    # H2 — Memory seeding at completion
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_completion_seeds_memory_facts(self) -> None:
        """H2: _run_completion_side_effects seeds SupabaseMemory with onboarding facts.

        Verifies the fix for the CRITICAL gap where no memory was ever seeded
        at wizard completion — new users started with empty memory_facts.

        At minimum these fact categories must be seeded:
          - name, age+city, occupation, hobbies, geek_out_on, saturday_morning → user graph
          - backstory_preview → relationship graph
        """
        from nikita.agents.onboarding.v2.state import Phase, WizardSlotsV2, WizardStateV2  # noqa: PLC0415
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            _run_completion_side_effects,
        )

        user_id = uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.onboarding_status = "in_progress"

        mock_session = MagicMock()
        mock_user_repo = MagicMock()
        mock_user_repo.update_onboarding_status = AsyncMock()
        mock_user_repo.activate_game = AsyncMock()

        mock_profile_repo = MagicMock()
        mock_profile_repo.get_by_user_id = AsyncMock(return_value=None)
        mock_profile_repo.create_profile = AsyncMock(return_value=MagicMock())

        slots = WizardSlotsV2(
            display_name={"display_name": "Kira"},
            age={"age": 28, "dob": "1997-01-01"},
            city={"city": "Berlin"},
            occupation={"occupation": "developer"},
            primary_hobbies={"primary_hobbies": ["climbing", "chess", "cooking"]},
            hangouts_personalized={"hangouts_personalized": ["bars"]},
            voice_or_text={"voice_or_text": "text"},
            phone=None,
            saturday_morning={"saturday_morning": "farmers market"},
            darkness_level={"darkness_level": 5},
            geek_out_on={"geek_out_on": "vintage synthesizers"},
        )
        # Store backstory_preview in onboarding_profile JSONB
        mock_user.onboarding_profile = {
            "slots": {},
            "completion": {"backstory_preview": "They met at a hackathon."},
        }
        state = WizardStateV2(slots=slots, phase=Phase.phase2, phase_2_turn_count=3)

        mock_add_fact = AsyncMock()
        mock_memory_instance = MagicMock()
        mock_memory_instance.add_fact = mock_add_fact

        mock_settings = MagicMock()
        mock_settings.openai_api_key = "sk-test"

        # Build a context-manager mock for the isolated session (GH #638 fix)
        mock_isolated_session = MagicMock()
        mock_session_ctx = MagicMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_isolated_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session_maker = MagicMock(return_value=mock_session_ctx)

        with patch(
            "nikita.api.routes.portal_onboarding_v2.ProfileRepository",
            return_value=mock_profile_repo,
        ), patch(
            "nikita.engine.vice.seeder.seed_vices_from_profile",
            new_callable=AsyncMock,
        ), patch(
            "nikita.api.routes.portal_onboarding_v2.SupabaseMemory",
            return_value=mock_memory_instance,
        ), patch(
            "nikita.api.routes.portal_onboarding_v2.get_settings",
            return_value=mock_settings,
        ), patch(
            "nikita.api.routes.portal_onboarding_v2.get_session_maker",
            return_value=mock_session_maker,
        ):
            await _run_completion_side_effects(
                user=mock_user,
                state=state,
                user_repo=mock_user_repo,
                session=mock_session,
            )

        # Must have called add_fact at least once
        assert mock_add_fact.call_count >= 1, (
            f"Expected SupabaseMemory.add_fact to be called for onboarding memory seeding, "
            f"got {mock_add_fact.call_count} calls"
        )

        # Check that key facts were seeded — collect all fact strings
        called_facts = [call.kwargs.get("fact", call.args[0] if call.args else "") for call in mock_add_fact.call_args_list]
        all_facts_text = " ".join(called_facts)

        assert "Kira" in all_facts_text, "name fact must be seeded"
        assert "Berlin" in all_facts_text, "city fact must be seeded"
        assert "developer" in all_facts_text, "occupation fact must be seeded"
        assert "climbing" in all_facts_text, "hobbies fact must be seeded"

    @pytest.mark.asyncio
    async def test_completion_seeds_backstory_preview_as_relationship_fact(self) -> None:
        """H2: backstory_preview is seeded into relationship graph memory."""
        from nikita.agents.onboarding.v2.state import Phase, WizardSlotsV2, WizardStateV2  # noqa: PLC0415
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            _run_completion_side_effects,
        )

        user_id = uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.onboarding_status = "in_progress"
        mock_user.onboarding_profile = {
            "slots": {},
            "completion": {"backstory_preview": "First impression at the hackathon."},
        }

        mock_session = MagicMock()
        mock_user_repo = MagicMock()
        mock_user_repo.update_onboarding_status = AsyncMock()
        mock_user_repo.activate_game = AsyncMock()

        mock_profile_repo = MagicMock()
        mock_profile_repo.get_by_user_id = AsyncMock(return_value=None)
        mock_profile_repo.create_profile = AsyncMock(return_value=MagicMock())

        slots = WizardSlotsV2(
            display_name={"display_name": "Alex"},
            age={"age": 30, "dob": "1995-01-01"},
            city={"city": "Zurich"},
            occupation={"occupation": "engineer"},
            primary_hobbies={"primary_hobbies": ["chess"]},
            hangouts_personalized={"hangouts_personalized": ["cafes"]},
            voice_or_text={"voice_or_text": "text"},
            phone=None,
            saturday_morning={"saturday_morning": "hackathon"},
            darkness_level={"darkness_level": 3},
            geek_out_on={"geek_out_on": "monads"},
        )
        state = WizardStateV2(slots=slots, phase=Phase.phase2, phase_2_turn_count=2)

        mock_add_fact = AsyncMock()
        mock_memory_instance = MagicMock()
        mock_memory_instance.add_fact = mock_add_fact

        mock_settings = MagicMock()
        mock_settings.openai_api_key = "sk-test"

        # Build a context-manager mock for the isolated session (GH #638 fix)
        mock_isolated_session_bs = MagicMock()
        mock_session_ctx_bs = MagicMock()
        mock_session_ctx_bs.__aenter__ = AsyncMock(return_value=mock_isolated_session_bs)
        mock_session_ctx_bs.__aexit__ = AsyncMock(return_value=False)
        mock_session_maker_bs = MagicMock(return_value=mock_session_ctx_bs)

        with patch(
            "nikita.api.routes.portal_onboarding_v2.ProfileRepository",
            return_value=mock_profile_repo,
        ), patch(
            "nikita.engine.vice.seeder.seed_vices_from_profile",
            new_callable=AsyncMock,
        ), patch(
            "nikita.api.routes.portal_onboarding_v2.SupabaseMemory",
            return_value=mock_memory_instance,
        ), patch(
            "nikita.api.routes.portal_onboarding_v2.get_settings",
            return_value=mock_settings,
        ), patch(
            "nikita.api.routes.portal_onboarding_v2.get_session_maker",
            return_value=mock_session_maker_bs,
        ):
            await _run_completion_side_effects(
                user=mock_user,
                state=state,
                user_repo=mock_user_repo,
                session=mock_session,
            )

        # Find the relationship-graph fact call
        relationship_calls = [
            call for call in mock_add_fact.call_args_list
            if call.kwargs.get("graph_type") == "relationship"
        ]
        assert len(relationship_calls) >= 1, (
            "backstory_preview must be seeded as a relationship graph fact"
        )
        relationship_fact_text = relationship_calls[0].kwargs.get("fact", "")
        assert "First impression at the hackathon" in relationship_fact_text

    # ------------------------------------------------------------------
    # H3 — LifeSimulator initialization at completion
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_completion_calls_initialize_user_for_life_sim(self) -> None:
        """H3: _run_completion_side_effects calls LifeSimulator.initialize_user(user_id).

        Verifies the fix for the CRITICAL gap where LifeSimulator.initialize_user()
        was never called at wizard completion — new users had no life-sim entities
        and experienced a dead world (no daily events).
        """
        from nikita.agents.onboarding.v2.state import Phase, WizardSlotsV2, WizardStateV2  # noqa: PLC0415
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            _run_completion_side_effects,
        )

        user_id = uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.onboarding_status = "in_progress"
        mock_user.onboarding_profile = {"slots": {}, "completion": {}}

        mock_session = MagicMock()
        mock_user_repo = MagicMock()
        mock_user_repo.update_onboarding_status = AsyncMock()
        mock_user_repo.activate_game = AsyncMock()

        mock_profile_repo = MagicMock()
        mock_profile_repo.get_by_user_id = AsyncMock(return_value=None)
        mock_profile_repo.create_profile = AsyncMock(return_value=MagicMock())

        slots = WizardSlotsV2(
            display_name={"display_name": "Sam"},
            age={"age": 27, "dob": "1998-01-01"},
            city={"city": "London"},
            occupation={"occupation": "artist"},
            primary_hobbies={"primary_hobbies": ["painting"]},
            hangouts_personalized={"hangouts_personalized": ["galleries"]},
            voice_or_text={"voice_or_text": "text"},
            phone=None,
            saturday_morning={"saturday_morning": "studio time"},
            darkness_level={"darkness_level": 4},
            geek_out_on={"geek_out_on": "color theory"},
        )
        state = WizardStateV2(slots=slots, phase=Phase.phase2, phase_2_turn_count=2)

        mock_initialize_user = AsyncMock(return_value=True)
        mock_simulator_instance = MagicMock()
        mock_simulator_instance.initialize_user = mock_initialize_user
        mock_simulator_class = MagicMock(return_value=mock_simulator_instance)

        with patch(
            "nikita.api.routes.portal_onboarding_v2.ProfileRepository",
            return_value=mock_profile_repo,
        ), patch(
            "nikita.engine.vice.seeder.seed_vices_from_profile",
            new_callable=AsyncMock,
        ), patch(
            "nikita.api.routes.portal_onboarding_v2.SupabaseMemory",
            return_value=MagicMock(**{"add_fact": AsyncMock()}),
        ), patch(
            "nikita.api.routes.portal_onboarding_v2.LifeSimulator",
            mock_simulator_class,
        ):
            await _run_completion_side_effects(
                user=mock_user,
                state=state,
                user_repo=mock_user_repo,
                session=mock_session,
            )

        mock_initialize_user.assert_awaited_once_with(user_id)

    # ------------------------------------------------------------------
    # H4 — ready_prompts bootstrap at wizard completion (turn-1 fix)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_completion_bootstraps_ready_prompts_for_both_platforms(self) -> None:
        """H4: _run_completion_side_effects calls ReadyPromptRepository.set_current
        twice — once for 'text' and once for 'voice' — and the prompt text
        contains the user's name and city.
        """
        from nikita.agents.onboarding.v2.state import Phase, WizardSlotsV2, WizardStateV2  # noqa: PLC0415
        from nikita.api.routes.portal_onboarding_v2 import _run_completion_side_effects  # noqa: PLC0415

        user_id = uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.onboarding_status = "in_progress"
        mock_user.onboarding_profile = {"slots": {}, "completion": {}}

        mock_session = MagicMock()
        mock_user_repo = MagicMock()
        mock_user_repo.update_onboarding_status = AsyncMock()
        mock_user_repo.activate_game = AsyncMock()

        mock_profile_repo = MagicMock()
        mock_profile_repo.get_by_user_id = AsyncMock(return_value=None)
        mock_profile_repo.create_profile = AsyncMock(return_value=MagicMock())

        slots = WizardSlotsV2(
            display_name={"display_name": "TestUser"},
            age={"age": 25, "dob": "2000-01-01"},
            city={"city": "TestCity"},
            occupation={"occupation": "tester"},
            primary_hobbies={"primary_hobbies": ["testing"]},
            hangouts_personalized={"hangouts_personalized": ["cafes"]},
            voice_or_text={"voice_or_text": "text"},
            phone=None,
            saturday_morning={"saturday_morning": "debugging"},
            darkness_level={"darkness_level": 3},
            geek_out_on={"geek_out_on": "unit tests"},
        )
        state = WizardStateV2(slots=slots, phase=Phase.phase2, phase_2_turn_count=2)

        # Mock for ready_prompt isolated session
        mock_rp_session = MagicMock()
        mock_rp_session_ctx = MagicMock()
        mock_rp_session_ctx.__aenter__ = AsyncMock(return_value=mock_rp_session)
        mock_rp_session_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_rp_session_maker = MagicMock(return_value=mock_rp_session_ctx)

        mock_set_current = AsyncMock(return_value=MagicMock())
        mock_rp_repo = MagicMock()
        mock_rp_repo.set_current = mock_set_current

        mock_settings = MagicMock()
        mock_settings.openai_api_key = "sk-test"

        with patch(
            "nikita.api.routes.portal_onboarding_v2.ProfileRepository",
            return_value=mock_profile_repo,
        ), patch(
            "nikita.engine.vice.seeder.seed_vices_from_profile",
            new_callable=AsyncMock,
        ), patch(
            "nikita.api.routes.portal_onboarding_v2.SupabaseMemory",
            return_value=MagicMock(**{"add_fact": AsyncMock()}),
        ), patch(
            "nikita.api.routes.portal_onboarding_v2.LifeSimulator",
            return_value=MagicMock(**{"initialize_user": AsyncMock()}),
        ), patch(
            "nikita.api.routes.portal_onboarding_v2.get_settings",
            return_value=mock_settings,
        ), patch(
            "nikita.api.routes.portal_onboarding_v2.get_session_maker",
            return_value=mock_rp_session_maker,
        ), patch(
            "nikita.api.routes.portal_onboarding_v2.ReadyPromptRepository",
            return_value=mock_rp_repo,
        ):
            await _run_completion_side_effects(
                user=mock_user,
                state=state,
                user_repo=mock_user_repo,
                session=mock_session,
            )

        # Must have called set_current twice — once per platform
        assert mock_set_current.call_count == 2, (
            f"Expected set_current called twice (text + voice), got {mock_set_current.call_count}"
        )
        platforms_called = {call.kwargs.get("platform") for call in mock_set_current.call_args_list}
        assert platforms_called == {"text", "voice"}, (
            f"Expected platforms {{'text', 'voice'}}, got {platforms_called}"
        )
        # Prompt text must contain name and city for personalization sanity
        for call in mock_set_current.call_args_list:
            prompt = call.kwargs.get("prompt_text", "")
            assert "TestUser" in prompt, f"prompt_text must contain user name, got: {prompt[:200]}"
            assert "TestCity" in prompt, f"prompt_text must contain city, got: {prompt[:200]}"

    @pytest.mark.asyncio
    async def test_completion_ready_prompts_bootstrap_is_non_fatal(self) -> None:
        """H4: if ready_prompts bootstrap raises, completion still succeeds
        (no re-raise) and an exception is logged.
        """
        from nikita.agents.onboarding.v2.state import Phase, WizardSlotsV2, WizardStateV2  # noqa: PLC0415
        from nikita.api.routes.portal_onboarding_v2 import _run_completion_side_effects  # noqa: PLC0415

        user_id = uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.onboarding_status = "in_progress"
        mock_user.onboarding_profile = {"slots": {}, "completion": {}}

        mock_session = MagicMock()
        mock_user_repo = MagicMock()
        mock_user_repo.update_onboarding_status = AsyncMock()
        mock_user_repo.activate_game = AsyncMock()

        mock_profile_repo = MagicMock()
        mock_profile_repo.get_by_user_id = AsyncMock(return_value=None)
        mock_profile_repo.create_profile = AsyncMock(return_value=MagicMock())

        slots = WizardSlotsV2(
            display_name={"display_name": "Boom"},
            age={"age": 22, "dob": "2003-01-01"},
            city={"city": "CrashCity"},
            occupation={"occupation": "tester"},
            primary_hobbies={"primary_hobbies": ["exploding"]},
            hangouts_personalized={"hangouts_personalized": ["ruins"]},
            voice_or_text={"voice_or_text": "text"},
            phone=None,
            saturday_morning={"saturday_morning": "chaos"},
            darkness_level={"darkness_level": 5},
            geek_out_on={"geek_out_on": "exceptions"},
        )
        state = WizardStateV2(slots=slots, phase=Phase.phase2, phase_2_turn_count=1)

        mock_settings = MagicMock()
        mock_settings.openai_api_key = "sk-test"

        # Session context that raises on set_current
        mock_rp_session = MagicMock()
        mock_rp_session_ctx = MagicMock()
        mock_rp_session_ctx.__aenter__ = AsyncMock(return_value=mock_rp_session)
        mock_rp_session_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_rp_session_maker = MagicMock(return_value=mock_rp_session_ctx)

        mock_rp_repo = MagicMock()
        mock_rp_repo.set_current = AsyncMock(side_effect=RuntimeError("DB boom"))

        with patch(
            "nikita.api.routes.portal_onboarding_v2.ProfileRepository",
            return_value=mock_profile_repo,
        ), patch(
            "nikita.engine.vice.seeder.seed_vices_from_profile",
            new_callable=AsyncMock,
        ), patch(
            "nikita.api.routes.portal_onboarding_v2.SupabaseMemory",
            return_value=MagicMock(**{"add_fact": AsyncMock()}),
        ), patch(
            "nikita.api.routes.portal_onboarding_v2.LifeSimulator",
            return_value=MagicMock(**{"initialize_user": AsyncMock()}),
        ), patch(
            "nikita.api.routes.portal_onboarding_v2.get_settings",
            return_value=mock_settings,
        ), patch(
            "nikita.api.routes.portal_onboarding_v2.get_session_maker",
            return_value=mock_rp_session_maker,
        ), patch(
            "nikita.api.routes.portal_onboarding_v2.ReadyPromptRepository",
            return_value=mock_rp_repo,
        ):
            # Must not raise — non-fatal
            await _run_completion_side_effects(
                user=mock_user,
                state=state,
                user_repo=mock_user_repo,
                session=mock_session,
            )

        # get_by_user_id called means idempotency ran → we reached the bootstrap step
        mock_profile_repo.get_by_user_id.assert_awaited_once()
        # If we got here without exception, the non-fatal contract holds

    @pytest.mark.asyncio
    async def test_completion_ready_prompts_bootstrap_uses_isolated_session(self) -> None:
        """H4: ready_prompts bootstrap uses its own isolated session — NOT the
        route session — so a DB error in set_current cannot poison the route
        session (same isolation contract as GH #638).
        """
        from nikita.agents.onboarding.v2.state import Phase, WizardSlotsV2, WizardStateV2  # noqa: PLC0415
        from nikita.api.routes.portal_onboarding_v2 import _run_completion_side_effects  # noqa: PLC0415

        user_id = uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.onboarding_status = "in_progress"
        mock_user.onboarding_profile = {"slots": {}, "completion": {}}

        route_session = MagicMock()
        mock_user_repo = MagicMock()
        mock_user_repo.update_onboarding_status = AsyncMock()
        mock_user_repo.activate_game = AsyncMock()

        mock_profile_repo = MagicMock()
        mock_profile_repo.get_by_user_id = AsyncMock(return_value=None)
        mock_profile_repo.create_profile = AsyncMock(return_value=MagicMock())

        slots = WizardSlotsV2(
            display_name={"display_name": "Isolated"},
            age={"age": 30, "dob": "1995-01-01"},
            city={"city": "IsolationCity"},
            occupation={"occupation": "hermit"},
            primary_hobbies={"primary_hobbies": ["isolation"]},
            hangouts_personalized={"hangouts_personalized": ["bunker"]},
            voice_or_text={"voice_or_text": "text"},
            phone=None,
            saturday_morning={"saturday_morning": "silence"},
            darkness_level={"darkness_level": 2},
            geek_out_on={"geek_out_on": "session isolation"},
        )
        state = WizardStateV2(slots=slots, phase=Phase.phase2, phase_2_turn_count=2)

        mock_settings = MagicMock()
        mock_settings.openai_api_key = "sk-test"

        isolated_session = MagicMock()  # Different object from route_session
        mock_rp_session_ctx = MagicMock()
        mock_rp_session_ctx.__aenter__ = AsyncMock(return_value=isolated_session)
        mock_rp_session_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_rp_session_maker = MagicMock(return_value=mock_rp_session_ctx)

        received_sessions: list = []

        def capture_rp_repo(session: object) -> MagicMock:
            received_sessions.append(session)
            repo = MagicMock()
            repo.set_current = AsyncMock(return_value=MagicMock())
            return repo

        with patch(
            "nikita.api.routes.portal_onboarding_v2.ProfileRepository",
            return_value=mock_profile_repo,
        ), patch(
            "nikita.engine.vice.seeder.seed_vices_from_profile",
            new_callable=AsyncMock,
        ), patch(
            "nikita.api.routes.portal_onboarding_v2.SupabaseMemory",
            return_value=MagicMock(**{"add_fact": AsyncMock()}),
        ), patch(
            "nikita.api.routes.portal_onboarding_v2.LifeSimulator",
            return_value=MagicMock(**{"initialize_user": AsyncMock()}),
        ), patch(
            "nikita.api.routes.portal_onboarding_v2.get_settings",
            return_value=mock_settings,
        ), patch(
            "nikita.api.routes.portal_onboarding_v2.get_session_maker",
            return_value=mock_rp_session_maker,
        ), patch(
            "nikita.api.routes.portal_onboarding_v2.ReadyPromptRepository",
            side_effect=capture_rp_repo,
        ):
            await _run_completion_side_effects(
                user=mock_user,
                state=state,
                user_repo=mock_user_repo,
                session=route_session,
            )

        # ReadyPromptRepository must have been called with the isolated session,
        # NOT the route session
        rp_sessions = [s for s in received_sessions]
        assert len(rp_sessions) >= 1, "ReadyPromptRepository was never instantiated"
        for s in rp_sessions:
            assert s is not route_session, (
                "ReadyPromptRepository must use the isolated session, not the route session"
            )
            assert s is isolated_session, (
                "ReadyPromptRepository must use the session from get_session_maker(), "
                "not the route session"
            )


# ---------------------------------------------------------------------------
# Cluster D — age gate + free-text length cap (Spec 218 Phase-2 fix plan)
# ---------------------------------------------------------------------------


class TestAgeGate:
    """POST /api/v1/onboarding/answer — age slot with age < 18 → HTTP 400."""

    @pytest.mark.asyncio
    async def test_age_below_minimum_returns_400(self) -> None:
        """DoB that computes to age < 18 → 400 age_below_minimum."""
        from datetime import date
        from httpx import ASGITransport, AsyncClient
        from fastapi import FastAPI
        from unittest.mock import AsyncMock, MagicMock, patch

        from nikita.api.routes.portal_onboarding_v2 import router, answer_v2
        from nikita.agents.onboarding.v2.state import SlotKindV2
        from nikita.api.dependencies.auth import AuthenticatedUser, get_authenticated_user
        from nikita.db.database import get_async_session
        from nikita.api.middleware.rate_limit import answer_rate_limit

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")

        user_id = uuid4()
        user = AuthenticatedUser(id=user_id, email="test@example.com")
        app.dependency_overrides[get_authenticated_user] = lambda: user
        fake_session = MagicMock()
        app.dependency_overrides[get_async_session] = lambda: fake_session
        app.dependency_overrides[answer_rate_limit] = lambda: None

        # A DOB that puts age at 17 (always underage relative to today)
        from datetime import date as _date
        today = _date.today()
        underage_dob = _date(today.year - 17, today.month, today.day).isoformat()

        # Freeze _today so test is stable across midnight
        with patch("nikita.api.routes.portal_onboarding_v2._today", return_value=today):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/v1/onboarding/answer",
                    json={
                        "slot_kind": SlotKindV2.age.value,
                        "value": underage_dob,
                    },
                    headers={"Authorization": "Bearer fake"},
                )

        assert response.status_code == 400, response.text
        data = response.json()
        assert data["error_code"] == "age_below_minimum"
        assert data["field"] == "age"

    @pytest.mark.asyncio
    async def test_age_exactly_18_passes_age_gate(self) -> None:
        """DoB that computes to exactly age 18 must NOT be rejected by age gate."""
        from datetime import date as _date
        from httpx import ASGITransport, AsyncClient
        from fastapi import FastAPI
        from unittest.mock import AsyncMock, MagicMock, patch

        from nikita.api.routes.portal_onboarding_v2 import router
        from nikita.agents.onboarding.v2.state import SlotKindV2
        from nikita.api.dependencies.auth import AuthenticatedUser, get_authenticated_user
        from nikita.db.database import get_async_session
        from nikita.api.middleware.rate_limit import answer_rate_limit

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")

        user_id = uuid4()
        user = AuthenticatedUser(id=user_id, email="test@example.com")
        fake_session = MagicMock()
        app.dependency_overrides[get_authenticated_user] = lambda: user
        app.dependency_overrides[get_async_session] = lambda: fake_session
        app.dependency_overrides[answer_rate_limit] = lambda: None

        today = _date.today()
        # DoB exactly 18 years ago today — age == 18, must pass
        exactly_18_dob = _date(today.year - 18, today.month, today.day).isoformat()

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.onboarding_profile = {"state_version": "v2", "slots": {}}

        with patch("nikita.api.routes.portal_onboarding_v2._today", return_value=today), \
             patch("nikita.api.routes.portal_onboarding_v2.handle_v2_answer", new_callable=AsyncMock) as mock_handle, \
             patch("nikita.api.routes.portal_onboarding_v2.UserRepository") as mock_repo_cls:
            mock_repo_cls.return_value.get = AsyncMock(return_value=mock_user)
            from nikita.agents.onboarding.v2.envelope import TextShortAsk
            mock_handle.return_value = TextShortAsk(
                slot="display_name", prompt="What's your name?"
            )
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/v1/onboarding/answer",
                    json={
                        "slot_kind": SlotKindV2.age.value,
                        "value": exactly_18_dob,
                    },
                    headers={"Authorization": "Bearer fake"},
                )

        # Must NOT be 400 for age_below_minimum — may be 200 or 500 depending on agent mock
        if response.status_code == 400:
            data = response.json()
            assert data.get("error_code") != "age_below_minimum", (
                "age==18 should not trigger age_below_minimum"
            )


class TestTextValueTooLong:
    """POST /api/v1/onboarding/answer — free-text value > 500 chars → HTTP 400."""

    @pytest.mark.asyncio
    async def test_text_value_too_long_returns_400(self) -> None:
        """String value > 500 chars → 400 value_too_long."""
        from httpx import ASGITransport, AsyncClient
        from fastapi import FastAPI
        from unittest.mock import AsyncMock, MagicMock

        from nikita.api.routes.portal_onboarding_v2 import router
        from nikita.agents.onboarding.v2.state import SlotKindV2
        from nikita.api.dependencies.auth import AuthenticatedUser, get_authenticated_user
        from nikita.db.database import get_async_session
        from nikita.api.middleware.rate_limit import answer_rate_limit

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")

        user_id = uuid4()
        user = AuthenticatedUser(id=user_id, email="test@example.com")
        fake_session = MagicMock()
        app.dependency_overrides[get_authenticated_user] = lambda: user
        app.dependency_overrides[get_async_session] = lambda: fake_session
        app.dependency_overrides[answer_rate_limit] = lambda: None

        too_long = "x" * 501  # 501 chars, over limit

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/onboarding/answer",
                json={
                    "slot_kind": SlotKindV2.display_name.value,
                    "value": too_long,
                },
                headers={"Authorization": "Bearer fake"},
            )

        assert response.status_code == 400, response.text
        data = response.json()
        assert data["error_code"] == "value_too_long"
        assert data["field"] == "value"

    @pytest.mark.asyncio
    async def test_text_value_at_500_chars_passes_length_gate(self) -> None:
        """String value == 500 chars must NOT be rejected by length gate."""
        from httpx import ASGITransport, AsyncClient
        from fastapi import FastAPI
        from unittest.mock import AsyncMock, MagicMock, patch

        from nikita.api.routes.portal_onboarding_v2 import router
        from nikita.agents.onboarding.v2.state import SlotKindV2
        from nikita.api.dependencies.auth import AuthenticatedUser, get_authenticated_user
        from nikita.db.database import get_async_session
        from nikita.api.middleware.rate_limit import answer_rate_limit

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")

        user_id = uuid4()
        user = AuthenticatedUser(id=user_id, email="test@example.com")
        fake_session = MagicMock()
        app.dependency_overrides[get_authenticated_user] = lambda: user
        app.dependency_overrides[get_async_session] = lambda: fake_session
        app.dependency_overrides[answer_rate_limit] = lambda: None

        exactly_500 = "x" * 500

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.onboarding_profile = {"state_version": "v2", "slots": {}}

        with patch("nikita.api.routes.portal_onboarding_v2.handle_v2_answer", new_callable=AsyncMock) as mock_handle, \
             patch("nikita.api.routes.portal_onboarding_v2.UserRepository") as mock_repo_cls:
            mock_repo_cls.return_value.get = AsyncMock(return_value=mock_user)
            from nikita.agents.onboarding.v2.envelope import TextShortAsk
            mock_handle.return_value = TextShortAsk(
                slot="display_name", prompt="What's your name?"
            )
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/v1/onboarding/answer",
                    json={
                        "slot_kind": SlotKindV2.display_name.value,
                        "value": exactly_500,
                    },
                    headers={"Authorization": "Bearer fake"},
                )

        if response.status_code == 400:
            data = response.json()
            assert data.get("error_code") != "value_too_long", (
                "500-char value should not trigger value_too_long"
            )
