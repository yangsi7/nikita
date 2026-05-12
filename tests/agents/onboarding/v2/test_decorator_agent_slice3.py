"""Spec 218 Slice 218-3 — decorator agent output validator for new shapes.

Slot-specific tests per R13 (not full triplet — that lives in
test_decorator_agent.py and was satisfied in slice 218-2).

Covered targets in slice 218-3: display_name, age, city, occupation.
Output union extends with CalendarAsk + SingleSelectAsk.

RED phase: imports fail on master commit 01922be.
"""

from __future__ import annotations

from unittest.mock import MagicMock

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

    def test_handoff_rejected_for_covered_target_age(self) -> None:
        from nikita.agents.onboarding.v2.decorator_agent import (  # noqa: PLC0415
            build_decorator_output_validator,
        )
        from nikita.agents.onboarding.v2.envelope import HandlerHandoffAsk  # noqa: PLC0415

        validator = build_decorator_output_validator()
        ctx = MagicMock()
        ctx.deps.target_slot = SlotKindV2.age.value

        with pytest.raises(ModelRetry):
            validator(
                ctx,
                HandlerHandoffAsk(
                    component="handler_handoff",
                    handler="v1",
                    next_url="/api/v1/converse/onboarding",
                ),
            )

    def test_handoff_accepted_for_uncovered_target_primary_hobbies(self) -> None:
        from nikita.agents.onboarding.v2.decorator_agent import (  # noqa: PLC0415
            build_decorator_output_validator,
        )
        from nikita.agents.onboarding.v2.envelope import HandlerHandoffAsk  # noqa: PLC0415

        validator = build_decorator_output_validator()
        ctx = MagicMock()
        ctx.deps.target_slot = SlotKindV2.primary_hobbies.value

        envelope = HandlerHandoffAsk(
            component="handler_handoff",
            handler="v1",
            next_url="/api/v1/converse/onboarding",
        )
        result = validator(ctx, envelope)
        assert result is envelope


class TestCoveredInSliceCohort:
    """Slice-218-3 covered set is {display_name, age, city, occupation}."""

    def test_covered_set_contains_four_slots(self) -> None:
        from nikita.agents.onboarding.v2.decorator_agent import (  # noqa: PLC0415
            COVERED_IN_SLICE,
        )

        assert COVERED_IN_SLICE == frozenset(
            {
                SlotKindV2.display_name.value,
                SlotKindV2.age.value,
                SlotKindV2.city.value,
                SlotKindV2.occupation.value,
            }
        )


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
