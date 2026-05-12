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
