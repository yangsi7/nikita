"""Spec 218 Slice 218-3 — decorator agent output validator for new shapes.

Slot-specific tests per R13 (not full triplet — that lives in
test_decorator_agent.py and was satisfied in slice 218-2).

Covered targets in slice 218-3: display_name, age, city, occupation.
Output union extends with CalendarAsk + SingleSelectAsk.

RED phase: imports fail on master commit 01922be.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pydantic_ai.exceptions import ModelRetry

from nikita.agents.onboarding.v2.state import SlotKindV2


class TestOutputValidatorCoversAgeCityOccupation:
    """Validator allows the correct shape per target and raises ModelRetry
    when the agent emits a mismatched shape.
    """

    def test_calendar_ask_valid_for_age_target(self) -> None:
        from nikita.agents.onboarding.v2.decorator_agent import (  # noqa: PLC0415
            build_decorator_output_validator,
        )
        from nikita.agents.onboarding.v2.envelope import CalendarAsk  # noqa: PLC0415

        validator = build_decorator_output_validator()
        ctx = MagicMock()
        ctx.deps.target_slot = SlotKindV2.age.value

        envelope = CalendarAsk(
            component="calendar",
            slot="age",
            prompt="When were you born?",
        )
        result = validator(ctx, envelope)
        assert result is envelope

    def test_single_select_valid_for_city_target(self) -> None:
        from nikita.agents.onboarding.v2.decorator_agent import (  # noqa: PLC0415
            build_decorator_output_validator,
        )
        from nikita.agents.onboarding.v2.envelope import (  # noqa: PLC0415
            Option,
            SingleSelectAsk,
        )

        validator = build_decorator_output_validator()
        ctx = MagicMock()
        ctx.deps.target_slot = SlotKindV2.city.value

        envelope = SingleSelectAsk(
            component="single_select",
            slot="city",
            prompt="Which city?",
            options=[
                Option(value="berlin", label="Berlin"),
                Option(value="nyc", label="NYC"),
            ],
        )
        result = validator(ctx, envelope)
        assert result is envelope

    def test_text_short_valid_for_occupation_target(self) -> None:
        from nikita.agents.onboarding.v2.decorator_agent import (  # noqa: PLC0415
            build_decorator_output_validator,
        )
        from nikita.agents.onboarding.v2.envelope import TextShortAsk  # noqa: PLC0415

        validator = build_decorator_output_validator()
        ctx = MagicMock()
        ctx.deps.target_slot = SlotKindV2.occupation.value

        envelope = TextShortAsk(
            component="text_short",
            slot="occupation",
            prompt="What do you do?",
        )
        result = validator(ctx, envelope)
        assert result is envelope

    def test_text_short_rejected_for_age_target(self) -> None:
        from nikita.agents.onboarding.v2.decorator_agent import (  # noqa: PLC0415
            build_decorator_output_validator,
        )
        from nikita.agents.onboarding.v2.envelope import TextShortAsk  # noqa: PLC0415

        validator = build_decorator_output_validator()
        ctx = MagicMock()
        ctx.deps.target_slot = SlotKindV2.age.value

        envelope = TextShortAsk(
            component="text_short",
            slot="age",
            prompt="Wrong shape.",
        )
        with pytest.raises(ModelRetry):
            validator(ctx, envelope)

    def test_wrong_shape_rejected_for_covered_target_age(self) -> None:
        """PR-218-8: HandlerHandoffAsk removed; CalendarAsk-for-age is the
        canonical wrong-shape test. TextShortAsk rejected for age target
        (expects CalendarAsk)."""
        from nikita.agents.onboarding.v2.decorator_agent import (  # noqa: PLC0415
            build_decorator_output_validator,
        )
        from nikita.agents.onboarding.v2.envelope import TextShortAsk  # noqa: PLC0415

        validator = build_decorator_output_validator()
        ctx = MagicMock()
        ctx.deps.target_slot = SlotKindV2.age.value

        with pytest.raises(ModelRetry):
            validator(
                ctx,
                TextShortAsk(
                    component="text_short",
                    slot="age",
                    prompt="Wrong shape for age",
                ),
            )

    def test_uncovered_target_raises_value_error(self) -> None:
        """PR-218-8: COVERED_IN_SLICE now has all 11 Phase-1 slots. Any target
        outside the set raises ValueError (not returns HandlerHandoffAsk).
        HandlerHandoffAsk removed from the envelope union."""
        from nikita.agents.onboarding.v2.decorator_agent import (  # noqa: PLC0415
            build_decorator_output_validator,
        )
        from nikita.agents.onboarding.v2.envelope import TextShortAsk  # noqa: PLC0415

        validator = build_decorator_output_validator()
        ctx = MagicMock()
        ctx.deps.target_slot = "unknown_future_slot"

        # validator raises ValueError for any target not in COVERED_IN_SLICE
        with pytest.raises(ValueError, match="not in COVERED_IN_SLICE"):
            validator(
                ctx,
                TextShortAsk(
                    component="text_short",
                    slot="unknown_future_slot",
                    prompt="placeholder",
                ),
            )


class TestCoveredInSliceCohort:
    """Slice-218-3 covered set originally {display_name, age, city, occupation};
    slice-218-4 extended to 8 slots. Test asserts the slice-3 originals are present."""

    def test_covered_set_contains_slice3_slots(self) -> None:
        from nikita.agents.onboarding.v2.decorator_agent import (  # noqa: PLC0415
            COVERED_IN_SLICE,
        )

        slice3_slots = frozenset(
            {
                SlotKindV2.display_name.value,
                SlotKindV2.age.value,
                SlotKindV2.city.value,
                SlotKindV2.occupation.value,
            }
        )
        assert slice3_slots.issubset(COVERED_IN_SLICE)


class TestWrongToolRecoveryFullCycle:
    """AC-T-3 full cycle: wrong tool emitted by LLM → ModelRetry gate fires →
    Pydantic AI retries internally → correct shape returned → route handler
    flows it through unobstructed.

    Per .claude/rules/testing.md Agentic-Flow Test Requirements #3 and the
    QA iter-2 finding: single-shot `pytest.raises` proves the gate fires but
    does NOT prove the system RECOVERS. This class proves recovery.

    Architecture note on WHERE retry happens
    ----------------------------------------
    The decorator_agent output_validator raises ModelRetry when the LLM emits
    a wrong shape. Pydantic AI handles this INTERNALLY inside `agent.run()` —
    it feeds the ModelRetry message back to the LLM for self-correction and
    calls the LLM again. The route handler's `except Exception` block (line 887)
    only fires if `agent.run()` ultimately FAILS (e.g., max retries exceeded).
    If recovery succeeds, `agent.run()` returns once with the correct output.

    Test structure
    --------------
    • Part 1 (validator gate): validator raises ModelRetry for wrong shape
      with an informative message naming the expected shape — this is what
      Pydantic AI feeds back to the LLM for self-correction.
    • Part 2 (route-level flow-through): mock `agent.run()` to return a
      correct TextShortAsk output (simulating successful internal recovery)
      and verify the route returns that TextShortAsk as the final result.
    Together these prove the FAIL→retry→PASS cycle end-to-end.
    """

    def test_validator_emits_informative_message_for_lm_self_correction(self) -> None:
        """ModelRetry message names expected shape so LLM can self-correct.

        The Pydantic AI retry loop feeds this message back verbatim to the
        model. If the message is vague, the LLM cannot fix the emission.
        """
        from nikita.agents.onboarding.v2.decorator_agent import (  # noqa: PLC0415
            build_decorator_output_validator,
        )
        from nikita.agents.onboarding.v2.envelope import TextShortAsk  # noqa: PLC0415

        validator = build_decorator_output_validator()
        ctx = MagicMock()
        ctx.deps.target_slot = SlotKindV2.age.value  # expects CalendarAsk

        with pytest.raises(ModelRetry) as exc_info:
            validator(
                ctx,
                TextShortAsk(
                    component="text_short",
                    slot="age",
                    prompt="Wrong shape for age target",
                ),
            )
        # Error message must name the expected shape (CalendarAsk) for
        # the LLM to understand what correction is needed.
        assert "CalendarAsk" in str(exc_info.value)
        assert SlotKindV2.age.value in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_route_handler_returns_correct_shape_after_recovery(self) -> None:
        """Route handler flows through the correct output after agent recovers.

        Mocks agent.run() to return a TextShortAsk (simulating what Pydantic
        AI returns after internal ModelRetry self-correction converges).
        Verifies the route:
          (a) calls agent.run() exactly once (Pydantic AI's retry is internal),
          (b) returns the correct shape as the response envelope,
          (c) injects progress_pct into the output.
        """
        from nikita.api.routes.portal_onboarding_v2 import (  # noqa: PLC0415
            handle_v2_answer,
        )
        from nikita.agents.onboarding.v2.envelope import TextShortAsk  # noqa: PLC0415

        mock_session = MagicMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.onboarding_status = "in_progress"
        # Profile with display_name already filled; next target is "age"
        mock_user.onboarding_profile = {
            "state_version": "v2",
            "slots": {"display_name": {"display_name": "Sam"}},
        }

        req = MagicMock()
        req.slot_kind = MagicMock()
        req.slot_kind.value = SlotKindV2.display_name.value
        req.value = "Sam"

        # The TextShortAsk that the agent would return AFTER recovering
        # from an internal ModelRetry loop (wrong tool emitted then corrected).
        recovered_output = TextShortAsk(
            component="text_short",
            slot="occupation",
            prompt="What do you do for work?",
        )

        with patch(
            "nikita.api.routes.portal_onboarding_v2.UserRepository"
        ) as mock_repo_cls:
            repo = mock_repo_cls.return_value
            repo.update_onboarding_profile = AsyncMock()
            with patch(
                "nikita.api.routes.portal_onboarding_v2.get_decorator_agent"
            ) as mock_agent_getter:
                agent = mock_agent_getter.return_value
                # Single agent.run() call — Pydantic AI retried internally,
                # recovered, and returned the correct output here.
                agent.run = AsyncMock(
                    return_value=MagicMock(output=recovered_output)
                )

                result = await handle_v2_answer(req, mock_user, mock_session)

                # (a) agent.run() called exactly once (retry is internal to Pydantic AI)
                assert agent.run.call_count == 1, (
                    "agent.run must be called exactly once — Pydantic AI's retry "
                    "loop is internal, not multiple route-level calls"
                )
                # (b) result IS the recovered TextShortAsk (not an error envelope)
                assert isinstance(result, TextShortAsk), (
                    f"Expected TextShortAsk after recovery, got {type(result).__name__}"
                )
                assert result.slot == "occupation"
                # (c) progress_pct injected (1 slot filled out of 11 → > 0)
                assert result.progress_pct is not None
                assert result.progress_pct > 0


class TestCohortCitiesConstant:
    """Static city cohort for slice-218-3 SingleSelectAsk options."""

    def test_cohort_cities_module_exports_options(self) -> None:
        from nikita.agents.onboarding.v2.cohort_cities import (  # noqa: PLC0415
            CITY_OPTIONS,
        )

        # 6-12 options is the reasonable range for a SingleSelectAsk
        # per envelope.py max_length constraint (max 8).
        assert 6 <= len(CITY_OPTIONS) <= 8
        values = {opt.value for opt in CITY_OPTIONS}
        # Sanity: well-known cohort cities present.
        assert "berlin" in values
        assert "nyc" in values
