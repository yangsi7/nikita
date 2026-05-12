"""Spec 218 Slice 218-4 — decorator agent extension for chip_multi + phone + voice_or_text.

Slot-specific tests per R13 (not full triplet re-run — that lives in
test_decorator_agent.py and was satisfied in slice 218-2).

New slots in slice 218-4:
  primary_hobbies     -> ChipMultiAsk
  hangouts_personalized -> ChipMultiAsk
  voice_or_text       -> SingleSelectAsk
  phone               -> PhoneAsk

COVERED_IN_SLICE must expand to 8 slots:
  {display_name, age, city, occupation,
   primary_hobbies, hangouts_personalized, voice_or_text, phone}

RED phase: tests fail until PR-218-4 implementation lands.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pydantic_ai.exceptions import ModelRetry

from nikita.agents.onboarding.v2.state import SlotKindV2


class TestOutputValidatorCoversNewSlots:
    """Validator allows correct shape per target for slice-218-4 slots and
    raises ModelRetry on mismatched shape."""

    def test_chip_multi_valid_for_primary_hobbies_target(self) -> None:
        from nikita.agents.onboarding.v2.decorator_agent import (  # noqa: PLC0415
            build_decorator_output_validator,
        )
        from nikita.agents.onboarding.v2.envelope import ChipMultiAsk, Option  # noqa: PLC0415

        validator = build_decorator_output_validator()
        ctx = MagicMock()
        ctx.deps.target_slot = SlotKindV2.primary_hobbies.value

        envelope = ChipMultiAsk(
            component="chip_multi",
            slot="primary_hobbies",
            prompt="What are your hobbies?",
            options=[
                Option(value="music", label="Music"),
                Option(value="sports", label="Sports"),
                Option(value="travel", label="Travel"),
            ],
            min_pick=1,
            max_pick=3,
        )
        result = validator(ctx, envelope)
        assert result is envelope

    def test_chip_multi_valid_for_hangouts_personalized_target(self) -> None:
        from nikita.agents.onboarding.v2.decorator_agent import (  # noqa: PLC0415
            build_decorator_output_validator,
        )
        from nikita.agents.onboarding.v2.envelope import ChipMultiAsk, Option  # noqa: PLC0415

        validator = build_decorator_output_validator()
        ctx = MagicMock()
        ctx.deps.target_slot = SlotKindV2.hangouts_personalized.value

        envelope = ChipMultiAsk(
            component="chip_multi",
            slot="hangouts_personalized",
            prompt="Which spots vibe for you?",
            options=[
                Option(value="berghain", label="Berghain"),
                Option(value="kitkat", label="KitKat"),
                Option(value="tresor", label="Tresor"),
            ],
            min_pick=1,
            max_pick=3,
        )
        result = validator(ctx, envelope)
        assert result is envelope

    def test_single_select_valid_for_voice_or_text_target(self) -> None:
        from nikita.agents.onboarding.v2.decorator_agent import (  # noqa: PLC0415
            build_decorator_output_validator,
        )
        from nikita.agents.onboarding.v2.envelope import Option, SingleSelectAsk  # noqa: PLC0415

        validator = build_decorator_output_validator()
        ctx = MagicMock()
        ctx.deps.target_slot = SlotKindV2.voice_or_text.value

        envelope = SingleSelectAsk(
            component="single_select",
            slot="voice_or_text",
            prompt="How do you prefer to talk?",
            options=[
                Option(value="voice", label="Voice calls"),
                Option(value="text", label="Text messages"),
            ],
        )
        result = validator(ctx, envelope)
        assert result is envelope

    def test_phone_ask_valid_for_phone_target(self) -> None:
        from nikita.agents.onboarding.v2.decorator_agent import (  # noqa: PLC0415
            build_decorator_output_validator,
        )
        from nikita.agents.onboarding.v2.envelope import PhoneAsk  # noqa: PLC0415

        validator = build_decorator_output_validator()
        ctx = MagicMock()
        ctx.deps.target_slot = SlotKindV2.phone.value

        envelope = PhoneAsk(
            component="phone",
            slot="phone",
            prompt="What's your number?",
        )
        result = validator(ctx, envelope)
        assert result is envelope

    def test_text_short_rejected_for_primary_hobbies_target(self) -> None:
        from nikita.agents.onboarding.v2.decorator_agent import (  # noqa: PLC0415
            build_decorator_output_validator,
        )
        from nikita.agents.onboarding.v2.envelope import TextShortAsk  # noqa: PLC0415

        validator = build_decorator_output_validator()
        ctx = MagicMock()
        ctx.deps.target_slot = SlotKindV2.primary_hobbies.value

        envelope = TextShortAsk(
            component="text_short",
            slot="primary_hobbies",
            prompt="Wrong shape.",
        )
        with pytest.raises(ModelRetry):
            validator(ctx, envelope)

    def test_text_short_rejected_for_phone_target(self) -> None:
        from nikita.agents.onboarding.v2.decorator_agent import (  # noqa: PLC0415
            build_decorator_output_validator,
        )
        from nikita.agents.onboarding.v2.envelope import TextShortAsk  # noqa: PLC0415

        validator = build_decorator_output_validator()
        ctx = MagicMock()
        ctx.deps.target_slot = SlotKindV2.phone.value

        envelope = TextShortAsk(
            component="text_short",
            slot="phone",
            prompt="Wrong shape.",
        )
        with pytest.raises(ModelRetry):
            validator(ctx, envelope)

    def test_handoff_rejected_for_covered_target_primary_hobbies(self) -> None:
        from nikita.agents.onboarding.v2.decorator_agent import (  # noqa: PLC0415
            build_decorator_output_validator,
        )
        from nikita.agents.onboarding.v2.envelope import HandlerHandoffAsk  # noqa: PLC0415

        validator = build_decorator_output_validator()
        ctx = MagicMock()
        ctx.deps.target_slot = SlotKindV2.primary_hobbies.value

        with pytest.raises(ModelRetry):
            validator(
                ctx,
                HandlerHandoffAsk(
                    component="handler_handoff",
                    handler="v1",
                    next_url="/api/v1/converse/onboarding",
                ),
            )

    def test_handoff_accepted_for_uncovered_target_saturday_morning(self) -> None:
        """saturday_morning is slice-218-5 territory; must still handoff."""
        from nikita.agents.onboarding.v2.decorator_agent import (  # noqa: PLC0415
            build_decorator_output_validator,
        )
        from nikita.agents.onboarding.v2.envelope import HandlerHandoffAsk  # noqa: PLC0415

        validator = build_decorator_output_validator()
        ctx = MagicMock()
        ctx.deps.target_slot = SlotKindV2.saturday_morning.value

        envelope = HandlerHandoffAsk(
            component="handler_handoff",
            handler="v1",
            next_url="/api/v1/converse/onboarding",
        )
        result = validator(ctx, envelope)
        assert result is envelope

    def test_chip_multi_over_max_pick_raises_model_retry(self) -> None:
        from nikita.agents.onboarding.v2.decorator_agent import (  # noqa: PLC0415
            build_decorator_output_validator,
            CHIP_MULTI_MAX_PICK,
        )
        from nikita.agents.onboarding.v2.envelope import ChipMultiAsk, Option  # noqa: PLC0415

        validator = build_decorator_output_validator()
        ctx = MagicMock()
        ctx.deps.target_slot = SlotKindV2.primary_hobbies.value

        envelope = ChipMultiAsk(
            component="chip_multi",
            slot=SlotKindV2.primary_hobbies.value,
            prompt="pick a few",
            options=[
                Option(value="a", label="A"),
                Option(value="b", label="B"),
                Option(value="c", label="C"),
                Option(value="d", label="D"),
                Option(value="e", label="E"),
                Option(value="f", label="F"),
            ],
            min_pick=1,
            max_pick=CHIP_MULTI_MAX_PICK + 1,
        )
        with pytest.raises(ModelRetry, match=r"exceeds CHIP_MULTI_MAX_PICK"):
            validator(ctx, envelope)

    def test_chip_multi_slot_mismatch_raises_model_retry(self) -> None:
        """ChipMultiAsk with wrong slot field (e.g., slot='hangouts_personalized'
        when target='primary_hobbies') must raise ModelRetry."""
        from nikita.agents.onboarding.v2.decorator_agent import (  # noqa: PLC0415
            build_decorator_output_validator,
        )
        from nikita.agents.onboarding.v2.envelope import ChipMultiAsk, Option  # noqa: PLC0415

        validator = build_decorator_output_validator()
        ctx = MagicMock()
        ctx.deps.target_slot = SlotKindV2.primary_hobbies.value

        # slot field says hangouts but target says primary_hobbies
        envelope = ChipMultiAsk(
            component="chip_multi",
            slot="hangouts_personalized",
            prompt="Which spots?",
            options=[
                Option(value="a", label="A"),
                Option(value="b", label="B"),
            ],
            min_pick=1,
            max_pick=2,
        )
        with pytest.raises(ModelRetry):
            validator(ctx, envelope)


class TestCoveredInSliceExpanded:
    """Slice-218-4 covered set is all 8 Phase-1 slots up through phone."""

    def test_covered_set_contains_eight_slots(self) -> None:
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
            }
        )
        assert COVERED_IN_SLICE == expected

    def test_covered_set_does_not_include_saturday_morning(self) -> None:
        from nikita.agents.onboarding.v2.decorator_agent import (  # noqa: PLC0415
            COVERED_IN_SLICE,
        )

        assert SlotKindV2.saturday_morning.value not in COVERED_IN_SLICE


class TestCohortHobbyAndHangoutConstants:
    """cohort_cities module exports HOBBY_OPTIONS and HANGOUT_OPTIONS."""

    def test_hobby_options_exported_with_reasonable_count(self) -> None:
        from nikita.agents.onboarding.v2.cohort_cities import (  # noqa: PLC0415
            HOBBY_OPTIONS,
        )

        # 3-24: ChipMultiAsk.options min_length=2, max_length=24
        assert 3 <= len(HOBBY_OPTIONS) <= 24
        values = {opt.value for opt in HOBBY_OPTIONS}
        # At least some canonical hobbies are present
        assert len(values) >= 3

    def test_hangout_options_exported_with_reasonable_count(self) -> None:
        from nikita.agents.onboarding.v2.cohort_cities import (  # noqa: PLC0415
            HANGOUT_OPTIONS,
        )

        assert 3 <= len(HANGOUT_OPTIONS) <= 24
        values = {opt.value for opt in HANGOUT_OPTIONS}
        assert len(values) >= 3

    def test_hobby_options_all_have_non_empty_labels(self) -> None:
        from nikita.agents.onboarding.v2.cohort_cities import (  # noqa: PLC0415
            HOBBY_OPTIONS,
        )

        for opt in HOBBY_OPTIONS:
            assert opt.label.strip(), f"Empty label for hobby option {opt.value!r}"

    def test_hangout_options_all_have_non_empty_labels(self) -> None:
        from nikita.agents.onboarding.v2.cohort_cities import (  # noqa: PLC0415
            HANGOUT_OPTIONS,
        )

        for opt in HANGOUT_OPTIONS:
            assert opt.label.strip(), f"Empty label for hangout option {opt.value!r}"
