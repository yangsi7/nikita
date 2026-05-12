"""Spec 218 Slice 218-5 — persist for slider (saturday_morning, darkness_level)
and text_long (geek_out_on) slots.

Per ``specs/218-onboarding-wizard-v2-agent-driven/subspecs/5/slice.md``.

New slot persistence in slice 218-5:
  saturday_morning  -> int 0-10 (slider value)
  darkness_level    -> int 0-10 (slider value)
  geek_out_on       -> str stripped, max 1000 chars

FR-007 DAG: no new edges from these 3 slots (no dependents).

RED phase: tests fail until PR-218-5 implementation lands.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _reset_retry_counts():
    """Clear ``_retry_counts`` between tests — defense-in-depth per slice-218-3 pattern."""
    from nikita.api.routes import portal_onboarding_v2  # noqa: PLC0415

    portal_onboarding_v2._retry_counts.clear()
    yield
    portal_onboarding_v2._retry_counts.clear()


# ---------------------------------------------------------------------------
# saturday_morning persistence (_slot_payload unit tests)
# ---------------------------------------------------------------------------


class TestSlotPayloadSaturdayMorning:
    """_slot_payload correctly converts saturday_morning slider values."""

    def test_valid_int_persisted(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import _slot_payload  # noqa: PLC0415

        result = _slot_payload("saturday_morning", 7)
        assert result == {"saturday_morning": 7}

    def test_zero_persisted(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import _slot_payload  # noqa: PLC0415

        result = _slot_payload("saturday_morning", 0)
        assert result == {"saturday_morning": 0}

    def test_ten_persisted(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import _slot_payload  # noqa: PLC0415

        result = _slot_payload("saturday_morning", 10)
        assert result == {"saturday_morning": 10}

    def test_negative_int_returns_none(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import _slot_payload  # noqa: PLC0415

        assert _slot_payload("saturday_morning", -1) is None

    def test_above_ten_returns_none(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import _slot_payload  # noqa: PLC0415

        assert _slot_payload("saturday_morning", 11) is None

    def test_string_value_returns_none(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import _slot_payload  # noqa: PLC0415

        assert _slot_payload("saturday_morning", "7") is None

    def test_float_value_returns_none(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import _slot_payload  # noqa: PLC0415

        assert _slot_payload("saturday_morning", 7.5) is None

    def test_bool_true_returns_none(self) -> None:
        """bool is subclass of int — must be rejected explicitly."""
        from nikita.api.routes.portal_onboarding_v2 import _slot_payload  # noqa: PLC0415

        assert _slot_payload("saturday_morning", True) is None

    def test_bool_false_returns_none(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import _slot_payload  # noqa: PLC0415

        assert _slot_payload("saturday_morning", False) is None


# ---------------------------------------------------------------------------
# darkness_level persistence (_slot_payload unit tests)
# ---------------------------------------------------------------------------


class TestSlotPayloadDarknessLevel:
    """_slot_payload correctly converts darkness_level slider values."""

    def test_valid_int_persisted(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import _slot_payload  # noqa: PLC0415

        result = _slot_payload("darkness_level", 5)
        assert result == {"darkness_level": 5}

    def test_zero_persisted(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import _slot_payload  # noqa: PLC0415

        result = _slot_payload("darkness_level", 0)
        assert result == {"darkness_level": 0}

    def test_negative_returns_none(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import _slot_payload  # noqa: PLC0415

        assert _slot_payload("darkness_level", -1) is None

    def test_above_ten_returns_none(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import _slot_payload  # noqa: PLC0415

        assert _slot_payload("darkness_level", 11) is None

    def test_bool_returns_none(self) -> None:
        """bool subclass of int — must be rejected explicitly."""
        from nikita.api.routes.portal_onboarding_v2 import _slot_payload  # noqa: PLC0415

        assert _slot_payload("darkness_level", True) is None
        assert _slot_payload("darkness_level", False) is None


# ---------------------------------------------------------------------------
# geek_out_on persistence (_slot_payload unit tests)
# ---------------------------------------------------------------------------


class TestSlotPayloadGeekOutOn:
    """_slot_payload correctly converts geek_out_on text_long values."""

    def test_valid_string_stripped(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import _slot_payload  # noqa: PLC0415

        result = _slot_payload("geek_out_on", "  vintage synthesizers  ")
        assert result == {"geek_out_on": "vintage synthesizers"}

    def test_empty_string_returns_none(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import _slot_payload  # noqa: PLC0415

        assert _slot_payload("geek_out_on", "   ") is None

    def test_exactly_1000_chars_persisted(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import _slot_payload  # noqa: PLC0415

        value = "x" * 1000
        result = _slot_payload("geek_out_on", value)
        assert result == {"geek_out_on": value}

    def test_over_1000_chars_returns_none(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import _slot_payload  # noqa: PLC0415

        value = "x" * 1001
        assert _slot_payload("geek_out_on", value) is None

    def test_non_string_returns_none(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import _slot_payload  # noqa: PLC0415

        assert _slot_payload("geek_out_on", 42) is None


# ---------------------------------------------------------------------------
# PERSISTABLE set coverage
# ---------------------------------------------------------------------------


class TestPersistableSlotNamesCoversSlice5:
    """_PERSISTABLE_SLOT_NAMES must include all 3 new slice-5 slots."""

    def test_saturday_morning_in_persistable(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            _PERSISTABLE_SLOT_NAMES,
        )

        assert "saturday_morning" in _PERSISTABLE_SLOT_NAMES

    def test_darkness_level_in_persistable(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            _PERSISTABLE_SLOT_NAMES,
        )

        assert "darkness_level" in _PERSISTABLE_SLOT_NAMES

    def test_geek_out_on_in_persistable(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            _PERSISTABLE_SLOT_NAMES,
        )

        assert "geek_out_on" in _PERSISTABLE_SLOT_NAMES


# ---------------------------------------------------------------------------
# handle_v2_answer integration: persist path for slice-5 slots (QA iter-1)
# ---------------------------------------------------------------------------


_PHASE1_PRIOR_SLOTS = {
    "display_name": {"display_name": "Sam"},
    "age": {"age": 28, "dob": "1998-04-12"},
    "city": {"city": "berlin"},
    "occupation": {"occupation": "engineer"},
    "primary_hobbies": {"primary_hobbies": ["music", "sports"]},
    "hangouts_personalized": {"hangouts_personalized": ["berghain", "tresor"]},
    "voice_or_text": {"voice_or_text": "voice"},
    "phone": {"phone": "+14155551234"},
}


class TestHandleV2AnswerPersistsSlice5Slots:
    """handle_v2_answer wires _apply_prior_submission for slice-5 slots."""

    @pytest.mark.asyncio
    async def test_saturday_morning_persists_via_handler(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            handle_v2_answer,
        )

        mock_session = MagicMock()
        mock_user = MagicMock()
        from uuid import uuid4  # noqa: PLC0415
        mock_user.id = uuid4()
        mock_user.onboarding_profile = {
            "state_version": "v2",
            "slots": dict(_PHASE1_PRIOR_SLOTS),
        }

        req = MagicMock()
        req.slot_kind = MagicMock()
        req.slot_kind.value = "saturday_morning"
        req.value = 5

        with patch(
            "nikita.api.routes.portal_onboarding_v2.UserRepository"
        ) as mock_repo_cls:
            repo = mock_repo_cls.return_value
            repo.update_onboarding_profile = AsyncMock()
            with patch(
                "nikita.api.routes.portal_onboarding_v2.get_decorator_agent"
            ) as mock_agent_getter:
                from nikita.agents.onboarding.v2.envelope import (  # noqa: PLC0415
                    SliderAsk,
                )

                agent = mock_agent_getter.return_value
                agent.run = AsyncMock(
                    return_value=MagicMock(
                        output=SliderAsk(
                            component="slider",
                            slot="darkness_level",
                            prompt="next slider",
                            min_val=0,
                            max_val=10,
                            step=1,
                            labels={"0": "playful", "10": "very dark"},
                        )
                    )
                )

                await handle_v2_answer(req, mock_user, mock_session)

                repo.update_onboarding_profile.assert_awaited_once()
                updates = repo.update_onboarding_profile.await_args.kwargs.get(
                    "profile_updates"
                )
                assert updates is not None
                assert updates["slots"]["saturday_morning"]["saturday_morning"] == 5

    @pytest.mark.asyncio
    async def test_darkness_level_persists_via_handler(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            handle_v2_answer,
        )

        mock_session = MagicMock()
        mock_user = MagicMock()
        from uuid import uuid4  # noqa: PLC0415
        mock_user.id = uuid4()
        mock_user.onboarding_profile = {
            "state_version": "v2",
            "slots": {**_PHASE1_PRIOR_SLOTS, "saturday_morning": {"saturday_morning": 5}},
        }

        req = MagicMock()
        req.slot_kind = MagicMock()
        req.slot_kind.value = "darkness_level"
        req.value = 7

        with patch(
            "nikita.api.routes.portal_onboarding_v2.UserRepository"
        ) as mock_repo_cls:
            repo = mock_repo_cls.return_value
            repo.update_onboarding_profile = AsyncMock()
            with patch(
                "nikita.api.routes.portal_onboarding_v2.get_decorator_agent"
            ) as mock_agent_getter:
                from nikita.agents.onboarding.v2.envelope import (  # noqa: PLC0415
                    TextLongAsk,
                )

                agent = mock_agent_getter.return_value
                agent.run = AsyncMock(
                    return_value=MagicMock(
                        output=TextLongAsk(
                            component="text_long",
                            slot="geek_out_on",
                            prompt="tell me",
                            max_chars=1000,
                        )
                    )
                )

                await handle_v2_answer(req, mock_user, mock_session)

                repo.update_onboarding_profile.assert_awaited_once()
                updates = repo.update_onboarding_profile.await_args.kwargs.get(
                    "profile_updates"
                )
                assert updates["slots"]["darkness_level"]["darkness_level"] == 7

    @pytest.mark.asyncio
    async def test_geek_out_on_persists_via_handler(self) -> None:
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            handle_v2_answer,
        )

        mock_session = MagicMock()
        mock_user = MagicMock()
        from uuid import uuid4  # noqa: PLC0415
        mock_user.id = uuid4()
        # Do NOT pre-load saturday_morning / darkness_level so pick_next_target
        # returns saturday_morning (not None) after geek_out_on is persisted.
        # That keeps Phase-2 entry from triggering and avoids a real LLM call
        # (CI has a dummy key).  The test still validates geek_out_on persistence.
        mock_user.onboarding_profile = {
            "state_version": "v2",
            "slots": dict(_PHASE1_PRIOR_SLOTS),
        }

        req = MagicMock()
        req.slot_kind = MagicMock()
        req.slot_kind.value = "geek_out_on"
        req.value = "  rust borrow checker proofs  "

        with patch(
            "nikita.api.routes.portal_onboarding_v2.UserRepository"
        ) as mock_repo_cls:
            repo = mock_repo_cls.return_value
            repo.update_onboarding_profile = AsyncMock()
            with patch(
                "nikita.api.routes.portal_onboarding_v2.get_decorator_agent"
            ) as mock_agent_getter:
                from nikita.agents.onboarding.v2.envelope import (  # noqa: PLC0415
                    HandlerHandoffAsk,
                )

                agent = mock_agent_getter.return_value
                agent.run = AsyncMock(
                    return_value=MagicMock(
                        output=HandlerHandoffAsk(
                            component="handler_handoff",
                            handler="v1",
                            next_url="/api/v1/converse/onboarding",
                        )
                    )
                )

                await handle_v2_answer(req, mock_user, mock_session)

                repo.update_onboarding_profile.assert_awaited_once()
                updates = repo.update_onboarding_profile.await_args.kwargs.get(
                    "profile_updates"
                )
                # Strip applied: surrounding whitespace removed.
                assert (
                    updates["slots"]["geek_out_on"]["geek_out_on"]
                    == "rust borrow checker proofs"
                )
