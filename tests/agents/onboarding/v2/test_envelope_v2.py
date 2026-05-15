"""Spec 218 envelope.py tests — 8-shape AskUnion discriminator + frozen.

Per FR-005 + spec 218 §23.1: exactly 8 component shapes, NO MORE,
discriminator field is ``component`` (string Literal per shape),
each branch uses ``ConfigDict(extra="forbid", frozen=True)``.
"""

from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError

from nikita.agents.onboarding.v2.envelope import (
    AskUnion,
    CalendarAsk,
    ChipMultiAsk,
    CompleteAsk,
    Option,
    PhoneAsk,
    SingleSelectAsk,
    SliderAsk,
    TextLongAsk,
    TextShortAsk,
)


_ADAPTER = TypeAdapter(AskUnion)


# ---------------------------------------------------------------------------
# Shape coverage — exactly 8 components, no more no less
# ---------------------------------------------------------------------------


def test_eight_component_shapes_supported() -> None:
    """AskUnion supports exactly 8 components per FR-005."""
    expected = {
        "text_short",
        "text_long",
        "single_select",
        "chip_multi",
        "slider",
        "calendar",
        "phone",
        "complete",
    }
    # Round-trip one example of each through the discriminated-union adapter
    samples = [
        TextShortAsk(slot="display_name", prompt="what should I call you?"),
        TextLongAsk(slot="geek_out_on", prompt="tell me a story"),
        SingleSelectAsk(
            slot="occupation",
            prompt="day job?",
            options=[Option(value="eng", label="engineer"), Option(value="other", label="other")],
        ),
        ChipMultiAsk(
            slot="primary_hobbies",
            prompt="pick what you're into",
            options=[
                Option(value="techno", label="techno"),
                Option(value="running", label="running"),
            ],
            max_pick=2,
        ),
        SliderAsk(slot="darkness_level", prompt="how dark do you want this?", min_val=1, max_val=5),
        CalendarAsk(slot="age", prompt="when's your birthday?"),
        PhoneAsk(slot="phone", prompt="number?"),
        CompleteAsk(next_route="/dashboard"),
    ]
    seen = set()
    for sample in samples:
        wire = sample.model_dump()
        parsed = _ADAPTER.validate_python(wire)
        seen.add(parsed.component)
    assert seen == expected


def test_no_reaction_only_shape() -> None:
    """Per spec 218 §23.1, reaction_only is killed; not a valid component."""
    with pytest.raises(ValidationError):
        _ADAPTER.validate_python(
            {"component": "reaction_only", "text": "ooh", "duration_ms": 1500}
        )


def test_unknown_component_rejected() -> None:
    """Unknown discriminator value -> ValidationError."""
    with pytest.raises(ValidationError):
        _ADAPTER.validate_python(
            {"component": "futuristic_widget", "slot": "x", "prompt": "y"}
        )


# ---------------------------------------------------------------------------
# extra="forbid" — strict shape per branch
# ---------------------------------------------------------------------------


def test_extra_field_rejected_on_text_short() -> None:
    """ConfigDict(extra='forbid') -> unknown fields rejected."""
    with pytest.raises(ValidationError):
        TextShortAsk(
            slot="display_name",
            prompt="hi",
            naughty_extra="should not pass",  # type: ignore[call-arg]
        )


def test_extra_field_rejected_on_chip_multi() -> None:
    with pytest.raises(ValidationError):
        ChipMultiAsk(
            slot="primary_hobbies",
            prompt="pick",
            options=[Option(value="a", label="A"), Option(value="b", label="B")],
            extra_garbage=True,  # type: ignore[call-arg]
        )


# ---------------------------------------------------------------------------
# frozen=True — immutable per branch
# ---------------------------------------------------------------------------


def test_text_short_is_frozen() -> None:
    """frozen=True -> field assignment raises ValidationError."""
    ask = TextShortAsk(slot="display_name", prompt="hi")
    with pytest.raises(ValidationError):
        ask.prompt = "different"  # type: ignore[misc]


def test_complete_is_frozen() -> None:
    ask = CompleteAsk(next_route="/dashboard")
    with pytest.raises(ValidationError):
        ask.next_route = "/other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Per-shape constraint validators
# ---------------------------------------------------------------------------


def test_chip_multi_min_pick_must_be_le_max_pick() -> None:
    with pytest.raises(ValidationError):
        ChipMultiAsk(
            slot="primary_hobbies",
            prompt="pick",
            options=[Option(value="a", label="A"), Option(value="b", label="B")],
            min_pick=3,
            max_pick=1,
        )


def test_chip_multi_max_pick_capped_by_options_length() -> None:
    with pytest.raises(ValidationError):
        ChipMultiAsk(
            slot="primary_hobbies",
            prompt="pick",
            options=[Option(value="a", label="A"), Option(value="b", label="B")],
            max_pick=10,
        )


def test_chip_multi_min_options_two() -> None:
    """At least 2 options required (single-option chip is degenerate)."""
    with pytest.raises(ValidationError):
        ChipMultiAsk(
            slot="primary_hobbies",
            prompt="pick",
            options=[Option(value="a", label="A")],
        )


def test_single_select_min_options_two() -> None:
    with pytest.raises(ValidationError):
        SingleSelectAsk(
            slot="occupation",
            prompt="?",
            options=[Option(value="a", label="A")],
        )


def test_slider_min_lt_max() -> None:
    with pytest.raises(ValidationError):
        SliderAsk(slot="darkness_level", prompt="?", min_val=5, max_val=1)


def test_phone_default_country_two_chars() -> None:
    with pytest.raises(ValidationError):
        PhoneAsk(prompt="?", default_country="USA")


def test_text_short_max_chars_bounded() -> None:
    with pytest.raises(ValidationError):
        TextShortAsk(slot="display_name", prompt="hi", max_chars=10_000)


def test_prompt_min_length_one() -> None:
    """Empty prompt rejected — every Ask must carry a non-empty agent voice."""
    with pytest.raises(ValidationError):
        TextShortAsk(slot="display_name", prompt="")


# ---------------------------------------------------------------------------
# Discriminator round-trip
# ---------------------------------------------------------------------------


def test_discriminator_round_trip_text_short() -> None:
    ask = TextShortAsk(slot="display_name", prompt="what should I call you?")
    wire = ask.model_dump()
    assert wire["component"] == "text_short"
    parsed = _ADAPTER.validate_python(wire)
    assert isinstance(parsed, TextShortAsk)
    assert parsed.slot == "display_name"


# ---------------------------------------------------------------------------
# progress_pct field on all 8 shapes (Cluster X — design-tone + state wiring)
# ---------------------------------------------------------------------------


def test_progress_pct_default_none_all_shapes() -> None:
    """All 8 shapes default progress_pct to None when not supplied."""
    assert TextShortAsk(slot="display_name", prompt="?").progress_pct is None
    assert TextLongAsk(slot="geek_out_on", prompt="?").progress_pct is None
    assert SingleSelectAsk(
        slot="occupation",
        prompt="?",
        options=[Option(value="a", label="A"), Option(value="b", label="B")],
    ).progress_pct is None
    assert ChipMultiAsk(
        slot="primary_hobbies",
        prompt="?",
        options=[Option(value="a", label="A"), Option(value="b", label="B")],
        max_pick=2,
    ).progress_pct is None
    assert SliderAsk(slot="darkness_level", prompt="?", min_val=0, max_val=10).progress_pct is None
    assert CalendarAsk(slot="age", prompt="?").progress_pct is None
    assert PhoneAsk(slot="phone", prompt="?").progress_pct is None
    assert CompleteAsk(next_route="/dashboard").progress_pct is None


def test_progress_pct_accepted_all_shapes() -> None:
    """All 8 shapes accept an explicit progress_pct value 0-100."""
    assert TextShortAsk(slot="display_name", prompt="?", progress_pct=40).progress_pct == 40
    assert TextLongAsk(slot="geek_out_on", prompt="?", progress_pct=0).progress_pct == 0
    assert SingleSelectAsk(
        slot="occupation",
        prompt="?",
        options=[Option(value="a", label="A"), Option(value="b", label="B")],
        progress_pct=100,
    ).progress_pct == 100
    assert ChipMultiAsk(
        slot="primary_hobbies",
        prompt="?",
        options=[Option(value="a", label="A"), Option(value="b", label="B")],
        max_pick=2,
        progress_pct=55,
    ).progress_pct == 55
    assert SliderAsk(slot="darkness_level", prompt="?", min_val=0, max_val=10, progress_pct=72).progress_pct == 72
    assert CalendarAsk(slot="age", prompt="?", progress_pct=9).progress_pct == 9
    assert PhoneAsk(slot="phone", prompt="?", progress_pct=81).progress_pct == 81
    assert CompleteAsk(next_route="/dashboard", progress_pct=100).progress_pct == 100


def test_progress_pct_out_of_range_rejected() -> None:
    """progress_pct outside 0-100 is rejected by Pydantic (ge=0, le=100)."""
    with pytest.raises(ValidationError):
        TextShortAsk(slot="display_name", prompt="?", progress_pct=-1)
    with pytest.raises(ValidationError):
        TextShortAsk(slot="display_name", prompt="?", progress_pct=101)


def test_progress_pct_survives_round_trip() -> None:
    """progress_pct serialises correctly through model_dump / _ADAPTER."""
    ask = TextShortAsk(slot="display_name", prompt="?", progress_pct=42)
    wire = ask.model_dump()
    assert wire["progress_pct"] == 42
    parsed = _ADAPTER.validate_python(wire)
    assert isinstance(parsed, TextShortAsk)
    assert parsed.progress_pct == 42


def test_discriminator_round_trip_complete() -> None:
    ask = CompleteAsk(next_route="/dashboard", backstory_preview="you walked in...")
    wire = ask.model_dump()
    parsed = _ADAPTER.validate_python(wire)
    assert isinstance(parsed, CompleteAsk)
    assert parsed.next_route == "/dashboard"


def test_option_extra_forbid() -> None:
    with pytest.raises(ValidationError):
        Option(value="a", label="A", garbage="x")  # type: ignore[call-arg]
