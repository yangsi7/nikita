"""Spec 218 router.py tests — deterministic ordering + DAG dependency-respect.

Per FR-003 + FR-006 + FR-007. Walk V (2026-04-22) precedent: agent
must NOT pick the next slot — the router does.
"""

from __future__ import annotations

from nikita.agents.onboarding.v2.router import (
    REQUIRED_ORDER,
    dag_invalidate,
    pick_next_target,
)
from nikita.agents.onboarding.v2.state import (
    PHASE_1_REQUIRED_SLOTS,
    SLOT_DEPENDENCIES,
    SlotDeltaV2,
    SlotKindV2,
    WizardSlotsV2,
)


# ---------------------------------------------------------------------------
# REQUIRED_ORDER invariants
# ---------------------------------------------------------------------------


def test_required_order_length_matches_slot_count() -> None:
    """REQUIRED_ORDER must have exactly PHASE_1_REQUIRED_SLOTS entries."""
    assert len(REQUIRED_ORDER) == PHASE_1_REQUIRED_SLOTS


def test_required_order_has_no_duplicates() -> None:
    """Each SlotKindV2 appears at most once in the order."""
    values = [s.value for s in REQUIRED_ORDER]
    assert len(values) == len(set(values))


def test_required_order_respects_dag() -> None:
    """For every slot with a non-empty dependency tuple, all of its
    dependencies must appear EARLIER in REQUIRED_ORDER.
    """
    positions = {slot.value: idx for idx, slot in enumerate(REQUIRED_ORDER)}
    for slot_name, deps in SLOT_DEPENDENCIES.items():
        for dep in deps:
            assert positions[dep] < positions[slot_name], (
                f"DAG violation: {slot_name} depends on {dep} but appears earlier"
            )


# ---------------------------------------------------------------------------
# pick_next_target — deterministic ordering
# ---------------------------------------------------------------------------


def test_pick_next_target_empty_state_returns_first_slot() -> None:
    """Empty state -> display_name (first in REQUIRED_ORDER)."""
    assert pick_next_target(WizardSlotsV2()) is SlotKindV2.display_name


def test_pick_next_target_walks_in_required_order() -> None:
    """As slots fill in REQUIRED_ORDER, pick_next_target advances 1-by-1."""
    state = WizardSlotsV2()
    expected_path = [
        SlotKindV2.display_name,
        SlotKindV2.age,
        SlotKindV2.city,
        SlotKindV2.occupation,
        SlotKindV2.primary_hobbies,
        SlotKindV2.hangouts_personalized,
        SlotKindV2.voice_or_text,
    ]
    payloads = {
        "display_name": {"display_name": "Sam"},
        "age": {"age": 30},
        "city": {"city": "Berlin"},
        "occupation": {"occupation": "engineer"},
        "primary_hobbies": {"primary_hobbies": ["techno"]},
        "hangouts_personalized": {"hangouts_personalized": ["berghain"]},
    }
    for expected in expected_path:
        assert pick_next_target(state) is expected
        if expected.value in payloads:
            state = state.apply(
                SlotDeltaV2(kind=expected.value, data=payloads[expected.value])
            )


def test_pick_next_target_returns_none_when_complete_text_track() -> None:
    """All Phase 1 slots filled (text track) -> None signals Phase 2."""
    state = (
        WizardSlotsV2()
        .apply(SlotDeltaV2(kind="display_name", data={"display_name": "Sam"}))
        .apply(SlotDeltaV2(kind="age", data={"age": 30}))
        .apply(SlotDeltaV2(kind="city", data={"city": "Berlin"}))
        .apply(SlotDeltaV2(kind="occupation", data={"occupation": "engineer"}))
        .apply(
            SlotDeltaV2(
                kind="primary_hobbies", data={"primary_hobbies": ["techno"]}
            )
        )
        .apply(
            SlotDeltaV2(
                kind="hangouts_personalized",
                data={"hangouts_personalized": ["berghain"]},
            )
        )
        .apply(SlotDeltaV2(kind="voice_or_text", data={"voice_or_text": "text"}))
        .apply(
            SlotDeltaV2(
                kind="saturday_morning", data={"saturday_morning": "coffee"}
            )
        )
        .apply(SlotDeltaV2(kind="darkness_level", data={"darkness_level": 3}))
        .apply(SlotDeltaV2(kind="geek_out_on", data={"geek_out_on": "kbd"}))
    )
    assert pick_next_target(state) is None


# ---------------------------------------------------------------------------
# Conditional-skip — phone slot when voice_or_text='text'
# ---------------------------------------------------------------------------


def test_pick_next_target_skips_phone_when_text_track() -> None:
    """voice_or_text='text' AND phone unfilled -> phone is skipped;
    pick_next_target advances to saturday_morning."""
    state = (
        WizardSlotsV2()
        .apply(SlotDeltaV2(kind="display_name", data={"display_name": "Sam"}))
        .apply(SlotDeltaV2(kind="age", data={"age": 30}))
        .apply(SlotDeltaV2(kind="city", data={"city": "Berlin"}))
        .apply(SlotDeltaV2(kind="occupation", data={"occupation": "engineer"}))
        .apply(
            SlotDeltaV2(
                kind="primary_hobbies", data={"primary_hobbies": ["techno"]}
            )
        )
        .apply(
            SlotDeltaV2(
                kind="hangouts_personalized",
                data={"hangouts_personalized": ["berghain"]},
            )
        )
        .apply(SlotDeltaV2(kind="voice_or_text", data={"voice_or_text": "text"}))
    )
    assert pick_next_target(state) is SlotKindV2.saturday_morning


def test_pick_next_target_asks_phone_when_voice_track() -> None:
    """voice_or_text='voice' AND phone unfilled -> phone is the next slot."""
    state = (
        WizardSlotsV2()
        .apply(SlotDeltaV2(kind="display_name", data={"display_name": "Sam"}))
        .apply(SlotDeltaV2(kind="age", data={"age": 30}))
        .apply(SlotDeltaV2(kind="city", data={"city": "Berlin"}))
        .apply(SlotDeltaV2(kind="occupation", data={"occupation": "engineer"}))
        .apply(
            SlotDeltaV2(
                kind="primary_hobbies", data={"primary_hobbies": ["techno"]}
            )
        )
        .apply(
            SlotDeltaV2(
                kind="hangouts_personalized",
                data={"hangouts_personalized": ["berghain"]},
            )
        )
        .apply(SlotDeltaV2(kind="voice_or_text", data={"voice_or_text": "voice"}))
    )
    assert pick_next_target(state) is SlotKindV2.phone


# ---------------------------------------------------------------------------
# DAG invalidate
# ---------------------------------------------------------------------------


def test_dag_invalidate_city_clears_hangouts() -> None:
    """City edit -> hangouts_personalized invalidated."""
    state = (
        WizardSlotsV2()
        .apply(SlotDeltaV2(kind="city", data={"city": "Berlin"}))
        .apply(SlotDeltaV2(kind="age", data={"age": 30}))
        .apply(SlotDeltaV2(kind="occupation", data={"occupation": "eng"}))
        .apply(
            SlotDeltaV2(
                kind="hangouts_personalized",
                data={"hangouts_personalized": ["berghain"]},
            )
        )
    )
    new_state, invalidated = dag_invalidate(state, "city")
    assert "hangouts_personalized" in invalidated
    assert new_state.hangouts_personalized is None
    # And city itself is preserved (the edit is to be re-applied by the caller)
    assert new_state.city == {"city": "Berlin"}


def test_dag_invalidate_voice_or_text_clears_phone() -> None:
    """voice_or_text edit -> phone invalidated."""
    state = (
        WizardSlotsV2()
        .apply(SlotDeltaV2(kind="voice_or_text", data={"voice_or_text": "voice"}))
        .apply(SlotDeltaV2(kind="phone", data={"phone": "+14155550100"}))
    )
    new_state, invalidated = dag_invalidate(state, "voice_or_text")
    assert "phone" in invalidated
    assert new_state.phone is None


def test_dag_invalidate_unknown_slot_no_op() -> None:
    """Unknown slot -> no-op, no exception."""
    state = WizardSlotsV2()
    new_state, invalidated = dag_invalidate(state, "nonexistent")
    assert invalidated == []
    assert new_state is state
