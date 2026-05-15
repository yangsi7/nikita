"""Spec 218 state.py tests — agentic-flow mandatory triplet + DAG + state_hash.

Per ``.claude/rules/agentic-design-patterns.md`` Hard Rules + ``.claude/
rules/testing.md`` Agentic-Flow Test Requirements:

1. Cumulative-state monotonicity (>=3-turn fixture; progress[t+1] >= progress[t])
2. Completion-gate triplet (empty -> False, partial -> False, full -> True)
3. (Mock-LLM-emits-wrong-tool recovery lives in test_decorator_agent_v2.py
   in PR-218-2; this file only covers state.)

Plus FR-007 DAG invalidation + FR-017 state_hash stability.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from nikita.agents.onboarding.v2.state import (
    PHASE_1_REQUIRED_SLOTS,
    PHASE_2_MAX_TURNS,
    PHASE_2_MIN_TURNS,
    FinalForm,
    Phase,
    SlotDeltaV2,
    SlotKindV2,
    WizardSlotsV2,
    WizardStateV2,
    state_hash,
)


# ---------------------------------------------------------------------------
# Tuning constants (regression guards per .claude/rules/tuning-constants.md)
# ---------------------------------------------------------------------------


def test_phase_1_required_slots_constant() -> None:
    """Spec 218 FR-006: 11 required slots in Phase 1."""
    assert PHASE_1_REQUIRED_SLOTS == 11


def test_phase_2_turn_bounds_constants() -> None:
    """FR-008: Phase 2 turn bounds 4..5.

    GH #623: max lowered from 8 to 5 (2026-05-15) to fire forced-completion
    gate earlier and prevent agent fixation loops observed in walk evidence.
    """
    assert PHASE_2_MIN_TURNS == 4
    assert PHASE_2_MAX_TURNS == 5


def test_slot_kind_v2_has_eleven_members() -> None:
    """SlotKindV2 must declare exactly 11 members (one per Phase 1 slot)."""
    assert len(list(SlotKindV2)) == 11


def test_phase_enum_values() -> None:
    """Phase enum values are stable strings used for JSONB persistence."""
    assert Phase.phase1.value == "phase1"
    assert Phase.phase2.value == "phase2"
    assert Phase.complete.value == "complete"


# ---------------------------------------------------------------------------
# (1) Cumulative-state monotonicity (>=3-turn fixture)
# ---------------------------------------------------------------------------


def test_progress_pct_monotonic_across_three_turns() -> None:
    """progress_pct must never regress as slots accumulate.

    Mandatory test class per .claude/rules/testing.md Agentic-Flow Test
    Requirements item 1.
    """
    state = WizardSlotsV2()
    assert state.progress_pct == 0

    # Turn 1: display_name
    state = state.apply(SlotDeltaV2(kind="display_name", data={"display_name": "Sam"}))
    progress_after_t1 = state.progress_pct

    # Turn 2: age
    state = state.apply(SlotDeltaV2(kind="age", data={"age": 30}))
    progress_after_t2 = state.progress_pct

    # Turn 3: city
    state = state.apply(SlotDeltaV2(kind="city", data={"city": "Berlin"}))
    progress_after_t3 = state.progress_pct

    assert progress_after_t1 >= 0
    assert progress_after_t2 >= progress_after_t1
    assert progress_after_t3 >= progress_after_t2
    # And each turn strictly increased progress (no stagnant turns)
    assert progress_after_t1 < progress_after_t2 < progress_after_t3


def test_no_extraction_delta_does_not_advance_progress() -> None:
    """no_extraction sentinel must leave state unchanged (no monotonicity break)."""
    state = WizardSlotsV2()
    state = state.apply(SlotDeltaV2(kind="display_name", data={"display_name": "Sam"}))
    p1 = state.progress_pct
    state = state.apply(SlotDeltaV2(kind="no_extraction", data={}))
    p2 = state.progress_pct
    assert p1 == p2


def test_apply_returns_new_instance_immutable() -> None:
    """``apply`` must return a NEW WizardSlotsV2 — original unchanged."""
    s1 = WizardSlotsV2()
    s2 = s1.apply(SlotDeltaV2(kind="display_name", data={"display_name": "Sam"}))
    assert s1.display_name is None
    assert s2.display_name == {"display_name": "Sam"}
    assert s1 is not s2


def test_progress_pct_one_hundred_when_full_phase_1() -> None:
    """All 11 required slots filled (text track) -> 100% progress."""
    full = _full_text_track_state()
    assert full.progress_pct == 100


def test_progress_pct_one_hundred_when_full_voice_track() -> None:
    """voice track: voice_or_text='voice' + phone filled -> 100%."""
    full = _full_voice_track_state()
    assert full.progress_pct == 100


# ---------------------------------------------------------------------------
# (2) Completion-gate triplet (empty / partial / full)
# ---------------------------------------------------------------------------


def test_finalform_rejects_empty_state() -> None:
    """Empty state -> FinalForm.model_validate raises ValidationError."""
    with pytest.raises(ValidationError):
        FinalForm.model_validate(WizardSlotsV2().slots_dict())


def test_finalform_rejects_partial_state() -> None:
    """Partially-filled state -> FinalForm raises ValidationError."""
    state = WizardSlotsV2().apply(
        SlotDeltaV2(kind="display_name", data={"display_name": "Sam"})
    )
    with pytest.raises(ValidationError):
        FinalForm.model_validate(state.slots_dict())


def test_finalform_accepts_full_text_track() -> None:
    """Fully-filled text-track state -> FinalForm validates."""
    full = _full_text_track_state()
    form = FinalForm.model_validate(full.slots_dict())
    assert form is not None


def test_finalform_accepts_full_voice_track() -> None:
    """voice + phone filled -> FinalForm validates."""
    full = _full_voice_track_state()
    form = FinalForm.model_validate(full.slots_dict())
    assert form is not None


def test_finalform_rejects_voice_without_phone() -> None:
    """voice_or_text='voice' AND missing phone -> ValidationError."""
    full = _full_text_track_state()
    # Flip voice_or_text to 'voice' without filling phone -> must fail
    state = full.model_copy(
        update={"voice_or_text": {"voice_or_text": "voice"}, "phone": None}
    )
    payload = state.slots_dict()
    payload.pop("phone", None)  # phone is conditional in FinalForm
    with pytest.raises(ValidationError):
        FinalForm.model_validate(payload)


def test_finalform_rejects_age_below_minimum() -> None:
    """age < MIN_USER_AGE (18) -> ValidationError."""
    full = _full_text_track_state()
    payload = full.slots_dict()
    payload["age"] = {"age": 17}
    with pytest.raises(ValidationError):
        FinalForm.model_validate(payload)


def test_finalform_rejects_empty_primary_hobbies() -> None:
    """primary_hobbies empty list -> ValidationError."""
    full = _full_text_track_state()
    payload = full.slots_dict()
    payload["primary_hobbies"] = {"primary_hobbies": []}
    with pytest.raises(ValidationError):
        FinalForm.model_validate(payload)


# ---------------------------------------------------------------------------
# DAG invalidation (FR-007)
# ---------------------------------------------------------------------------


def test_dag_invalidate_city_clears_hangouts() -> None:
    """Editing city must null-out hangouts_personalized when filled."""
    state = _full_text_track_state()
    new_state, invalidated = state.invalidate_dependents("city")
    assert "hangouts_personalized" in invalidated
    assert new_state.hangouts_personalized is None


def test_dag_invalidate_age_clears_hangouts() -> None:
    """Editing age must null-out hangouts_personalized when filled."""
    state = _full_text_track_state()
    new_state, invalidated = state.invalidate_dependents("age")
    assert "hangouts_personalized" in invalidated
    assert new_state.hangouts_personalized is None


def test_dag_invalidate_occupation_clears_hangouts() -> None:
    """Editing occupation must null-out hangouts_personalized when filled."""
    state = _full_text_track_state()
    new_state, invalidated = state.invalidate_dependents("occupation")
    assert "hangouts_personalized" in invalidated
    assert new_state.hangouts_personalized is None


def test_dag_invalidate_voice_or_text_clears_phone() -> None:
    """Editing voice_or_text must null-out phone when filled."""
    state = _full_voice_track_state()
    new_state, invalidated = state.invalidate_dependents("voice_or_text")
    assert "phone" in invalidated
    assert new_state.phone is None


def test_dag_invalidate_no_op_when_dependent_unfilled() -> None:
    """Editing a slot whose dependents are unfilled -> no invalidation."""
    state = WizardSlotsV2().apply(
        SlotDeltaV2(kind="city", data={"city": "Berlin"})
    )
    new_state, invalidated = state.invalidate_dependents("city")
    assert invalidated == []
    # Same instance returned when no change applied
    assert new_state is state


def test_dag_invalidate_unknown_slot_no_op() -> None:
    """Unknown slot name -> no invalidation, no error."""
    state = _full_text_track_state()
    new_state, invalidated = state.invalidate_dependents("nonexistent_slot")
    assert invalidated == []


# ---------------------------------------------------------------------------
# state_hash stability (FR-017)
# ---------------------------------------------------------------------------


def test_state_hash_stable_across_calls() -> None:
    """Same state -> same hash, deterministic across invocations."""
    s = _full_text_track_state()
    h1 = state_hash(s)
    h2 = state_hash(s)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex digest


def test_state_hash_changes_on_state_change() -> None:
    """Adding a slot -> new hash."""
    s1 = WizardSlotsV2()
    s2 = s1.apply(SlotDeltaV2(kind="display_name", data={"display_name": "Sam"}))
    assert state_hash(s1) != state_hash(s2)


def test_state_hash_independent_of_python_hash_seed() -> None:
    """Hash output must be identical for two equivalent states constructed
    independently (regression guard against dict ordering or PYTHONHASHSEED).
    """
    s_a = (
        WizardSlotsV2()
        .apply(SlotDeltaV2(kind="display_name", data={"display_name": "Sam"}))
        .apply(SlotDeltaV2(kind="age", data={"age": 30}))
    )
    s_b = (
        WizardSlotsV2()
        .apply(SlotDeltaV2(kind="age", data={"age": 30}))
        .apply(SlotDeltaV2(kind="display_name", data={"display_name": "Sam"}))
    )
    assert state_hash(s_a) == state_hash(s_b)


# ---------------------------------------------------------------------------
# WizardStateV2 envelope
# ---------------------------------------------------------------------------


def test_wizard_state_v2_default_phase_is_phase_1() -> None:
    """Top-level state defaults to Phase.phase1."""
    ws = WizardStateV2()
    assert ws.phase is Phase.phase1
    assert ws.phase_2_turn_count == 0
    assert ws.phase_2_started_at is None


def test_wizard_state_v2_phase_2_eligible_when_phase_1_complete() -> None:
    """is_phase_2_eligible True iff FinalForm validates."""
    incomplete = WizardStateV2()
    assert incomplete.is_phase_2_eligible is False

    complete_text = WizardStateV2(slots=_full_text_track_state())
    assert complete_text.is_phase_2_eligible is True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _full_text_track_state() -> WizardSlotsV2:
    """Return a WizardSlotsV2 with all 10 text-track slots filled (no phone).

    voice_or_text='text' so phone is conditional and unfilled.
    """
    return (
        WizardSlotsV2()
        .apply(SlotDeltaV2(kind="display_name", data={"display_name": "Sam"}))
        .apply(SlotDeltaV2(kind="age", data={"age": 30}))
        .apply(SlotDeltaV2(kind="city", data={"city": "Berlin"}))
        .apply(SlotDeltaV2(kind="occupation", data={"occupation": "engineer"}))
        .apply(
            SlotDeltaV2(
                kind="primary_hobbies",
                data={"primary_hobbies": ["techno", "running"]},
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
                kind="saturday_morning",
                data={"saturday_morning": "coffee + slow read"},
            )
        )
        .apply(SlotDeltaV2(kind="darkness_level", data={"darkness_level": 3}))
        .apply(SlotDeltaV2(kind="geek_out_on", data={"geek_out_on": "split keyboards"}))
    )


def _full_voice_track_state() -> WizardSlotsV2:
    """Return a state with voice_or_text='voice' AND phone filled."""
    return _full_text_track_state().model_copy(
        update={
            "voice_or_text": {"voice_or_text": "voice"},
            "phone": {"phone": "+14155550100"},
        }
    )
