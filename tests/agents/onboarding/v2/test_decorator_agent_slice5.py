"""Spec 218 Slice 218-5 — decorator agent extension for slider + text_long slots.

New slots in slice 218-5:
  saturday_morning  -> SliderAsk
  darkness_level    -> SliderAsk
  geek_out_on       -> TextLongAsk

COVERED_IN_SLICE must expand to 11 slots (full Phase-1 coverage):
  {display_name, age, city, occupation,
   primary_hobbies, hangouts_personalized, voice_or_text, phone,
   saturday_morning, darkness_level, geek_out_on}

RED phase: tests fail until PR-218-5 implementation lands.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pydantic_ai.exceptions import ModelRetry

from nikita.agents.onboarding.v2.state import SlotKindV2


class TestOutputValidatorCoversNewSlots:
    """Validator allows correct shape per target for slice-218-5 slots and
    raises ModelRetry on mismatched shape."""

    def test_slider_ask_valid_for_saturday_morning_target(self) -> None:
        from nikita.agents.onboarding.v2.decorator_agent import (  # noqa: PLC0415
            build_decorator_output_validator,
        )
        from nikita.agents.onboarding.v2.envelope import SliderAsk  # noqa: PLC0415

        validator = build_decorator_output_validator()
        ctx = MagicMock()
        ctx.deps.target_slot = SlotKindV2.saturday_morning.value

        envelope = SliderAsk(
            component="slider",
            slot="saturday_morning",
            prompt="On a scale of 0-10, how active are you on Saturday mornings?",
            min_val=0,
            max_val=10,
            step=1,
            labels={0: "Lazy", 5: "Balanced", 10: "Super active"},
        )
        result = validator(ctx, envelope)
        assert result is envelope

    def test_slider_ask_valid_for_darkness_level_target(self) -> None:
        from nikita.agents.onboarding.v2.decorator_agent import (  # noqa: PLC0415
            build_decorator_output_validator,
        )
        from nikita.agents.onboarding.v2.envelope import SliderAsk  # noqa: PLC0415

        validator = build_decorator_output_validator()
        ctx = MagicMock()
        ctx.deps.target_slot = SlotKindV2.darkness_level.value

        envelope = SliderAsk(
            component="slider",
            slot="darkness_level",
            prompt="How dark do you like your humor?",
            min_val=0,
            max_val=10,
            step=1,
            labels={0: "Light", 5: "Medium", 10: "Very dark"},
        )
        result = validator(ctx, envelope)
        assert result is envelope

    def test_text_long_ask_valid_for_geek_out_on_target(self) -> None:
        from nikita.agents.onboarding.v2.decorator_agent import (  # noqa: PLC0415
            build_decorator_output_validator,
        )
        from nikita.agents.onboarding.v2.envelope import TextLongAsk  # noqa: PLC0415

        validator = build_decorator_output_validator()
        ctx = MagicMock()
        ctx.deps.target_slot = SlotKindV2.geek_out_on.value

        envelope = TextLongAsk(
            component="text_long",
            slot="geek_out_on",
            prompt="Tell me something you could geek out on for hours.",
            placeholder="e.g. vintage synthesizers, the Weimar Republic...",
            max_chars=1000,
        )
        result = validator(ctx, envelope)
        assert result is envelope

    def test_text_short_rejected_for_saturday_morning_target(self) -> None:
        from nikita.agents.onboarding.v2.decorator_agent import (  # noqa: PLC0415
            build_decorator_output_validator,
        )
        from nikita.agents.onboarding.v2.envelope import TextShortAsk  # noqa: PLC0415

        validator = build_decorator_output_validator()
        ctx = MagicMock()
        ctx.deps.target_slot = SlotKindV2.saturday_morning.value

        envelope = TextShortAsk(
            component="text_short",
            slot="saturday_morning",
            prompt="Wrong shape.",
        )
        with pytest.raises(ModelRetry):
            validator(ctx, envelope)

    def test_text_short_rejected_for_geek_out_on_target(self) -> None:
        from nikita.agents.onboarding.v2.decorator_agent import (  # noqa: PLC0415
            build_decorator_output_validator,
        )
        from nikita.agents.onboarding.v2.envelope import TextShortAsk  # noqa: PLC0415

        validator = build_decorator_output_validator()
        ctx = MagicMock()
        ctx.deps.target_slot = SlotKindV2.geek_out_on.value

        envelope = TextShortAsk(
            component="text_short",
            slot="geek_out_on",
            prompt="Wrong shape.",
        )
        with pytest.raises(ModelRetry):
            validator(ctx, envelope)

    def test_handoff_rejected_for_covered_target_saturday_morning(self) -> None:
        from nikita.agents.onboarding.v2.decorator_agent import (  # noqa: PLC0415
            build_decorator_output_validator,
        )
        from nikita.agents.onboarding.v2.envelope import HandlerHandoffAsk  # noqa: PLC0415

        validator = build_decorator_output_validator()
        ctx = MagicMock()
        ctx.deps.target_slot = SlotKindV2.saturday_morning.value

        with pytest.raises(ModelRetry):
            validator(
                ctx,
                HandlerHandoffAsk(
                    component="handler_handoff",
                    handler="v1",
                    next_url="/api/v1/converse/onboarding",
                ),
            )

    def test_handoff_rejected_for_covered_target_darkness_level(self) -> None:
        from nikita.agents.onboarding.v2.decorator_agent import (  # noqa: PLC0415
            build_decorator_output_validator,
        )
        from nikita.agents.onboarding.v2.envelope import HandlerHandoffAsk  # noqa: PLC0415

        validator = build_decorator_output_validator()
        ctx = MagicMock()
        ctx.deps.target_slot = SlotKindV2.darkness_level.value

        with pytest.raises(ModelRetry):
            validator(
                ctx,
                HandlerHandoffAsk(
                    component="handler_handoff",
                    handler="v1",
                    next_url="/api/v1/converse/onboarding",
                ),
            )

    def test_handoff_rejected_for_covered_target_geek_out_on(self) -> None:
        from nikita.agents.onboarding.v2.decorator_agent import (  # noqa: PLC0415
            build_decorator_output_validator,
        )
        from nikita.agents.onboarding.v2.envelope import HandlerHandoffAsk  # noqa: PLC0415

        validator = build_decorator_output_validator()
        ctx = MagicMock()
        ctx.deps.target_slot = SlotKindV2.geek_out_on.value

        with pytest.raises(ModelRetry):
            validator(
                ctx,
                HandlerHandoffAsk(
                    component="handler_handoff",
                    handler="v1",
                    next_url="/api/v1/converse/onboarding",
                ),
            )

    def test_handoff_accepted_for_truly_uncovered_target(self) -> None:
        """A literal string not in SlotKindV2 must still accept HandlerHandoffAsk."""
        from nikita.agents.onboarding.v2.decorator_agent import (  # noqa: PLC0415
            build_decorator_output_validator,
        )
        from nikita.agents.onboarding.v2.envelope import HandlerHandoffAsk  # noqa: PLC0415

        validator = build_decorator_output_validator()
        ctx = MagicMock()
        ctx.deps.target_slot = "unknown_future_slot"

        envelope = HandlerHandoffAsk(
            component="handler_handoff",
            handler="v1",
            next_url="/api/v1/converse/onboarding",
        )
        result = validator(ctx, envelope)
        assert result is envelope


class TestCoveredInSliceExpanded:
    """Slice-218-5 covered set is all 11 Phase-1 slots."""

    def test_covered_set_contains_eleven_slots(self) -> None:
        from nikita.agents.onboarding.v2.decorator_agent import (  # noqa: PLC0415
            COVERED_IN_SLICE,
        )

        expected = frozenset(
            {
                SlotKindV2.display_name.value,
                SlotKindV2.age.value,
                SlotKindV2.city.value,
                SlotKindV2.occupation.value,
                SlotKindV2.primary_hobbies.value,
                SlotKindV2.hangouts_personalized.value,
                SlotKindV2.voice_or_text.value,
                SlotKindV2.phone.value,
                SlotKindV2.saturday_morning.value,
                SlotKindV2.darkness_level.value,
                SlotKindV2.geek_out_on.value,
            }
        )
        assert COVERED_IN_SLICE == expected

    def test_saturday_morning_in_covered_set(self) -> None:
        from nikita.agents.onboarding.v2.decorator_agent import (  # noqa: PLC0415
            COVERED_IN_SLICE,
        )

        assert SlotKindV2.saturday_morning.value in COVERED_IN_SLICE

    def test_darkness_level_in_covered_set(self) -> None:
        from nikita.agents.onboarding.v2.decorator_agent import (  # noqa: PLC0415
            COVERED_IN_SLICE,
        )

        assert SlotKindV2.darkness_level.value in COVERED_IN_SLICE

    def test_geek_out_on_in_covered_set(self) -> None:
        from nikita.agents.onboarding.v2.decorator_agent import (  # noqa: PLC0415
            COVERED_IN_SLICE,
        )

        assert SlotKindV2.geek_out_on.value in COVERED_IN_SLICE


class TestSliderSlotMismatchRaisesModelRetry:
    """SliderAsk with wrong slot field must raise ModelRetry."""

    def test_slider_slot_mismatch_raises_model_retry(self) -> None:
        from nikita.agents.onboarding.v2.decorator_agent import (  # noqa: PLC0415
            build_decorator_output_validator,
        )
        from nikita.agents.onboarding.v2.envelope import SliderAsk  # noqa: PLC0415

        validator = build_decorator_output_validator()
        ctx = MagicMock()
        ctx.deps.target_slot = SlotKindV2.saturday_morning.value

        # slot field says darkness_level but target says saturday_morning
        envelope = SliderAsk(
            component="slider",
            slot="darkness_level",
            prompt="Wrong target.",
            min_val=0,
            max_val=10,
        )
        with pytest.raises(ModelRetry):
            validator(ctx, envelope)
