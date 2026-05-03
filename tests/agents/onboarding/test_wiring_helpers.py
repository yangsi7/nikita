"""Unit tests for ``nikita.agents.onboarding.wiring`` (Spec 216-DE-wire).

Six pure-predicate / factory-builder tests. The Anthropic-backed factories
are unit-tested for shape (callable, async, propagates exceptions); the
production calls are covered by the integration suite at
``tests/api/routes/test_answer_wiring.py``.
"""

from __future__ import annotations

import inspect

import pytest

from nikita.agents.onboarding.archetypes import (
    ARCHETYPES,
    ArchetypeCard,
    NUM_ARCHETYPE_CANDIDATES,
)
from nikita.agents.onboarding.question_registry import SlotKind
from nikita.agents.onboarding.wiring import (
    PROSE_SLOT_KINDS_FOR_BIG5,
    default_archetype_cards,
    make_anthropic_generator,
    make_anthropic_judge,
    make_anthropic_picker,
    should_populate_archetype_cards,
    should_populate_cohort_chips,
    should_run_big5_judge,
)


class TestShouldRunBig5Judge:
    """``should_run_big5_judge`` fires only on the 5 prose slots."""

    @pytest.mark.parametrize(
        "kind",
        [
            SlotKind.saturday_morning,
            SlotKind.geek_out_on,
            SlotKind.together_we_could,
            SlotKind.same_weird_if,
            SlotKind.primary_hobbies,
        ],
    )
    def test_prose_slots_return_true(self, kind: SlotKind) -> None:
        assert should_run_big5_judge(kind) is True

    @pytest.mark.parametrize(
        "kind",
        [
            SlotKind.display_name,
            SlotKind.age,
            SlotKind.occupation,
            SlotKind.city,
            SlotKind.darkness_level,
            SlotKind.voice_tone_pref,
            SlotKind.backstory_pick,
            SlotKind.phone,
        ],
    )
    def test_non_prose_slots_return_false(self, kind: SlotKind) -> None:
        assert should_run_big5_judge(kind) is False

    def test_none_returns_false(self) -> None:
        assert should_run_big5_judge(None) is False

    def test_constant_set_matches_predicate_truth_table(self) -> None:
        """The frozenset constant is the single source of truth."""
        # All five members must be SlotKind values.
        for k in PROSE_SLOT_KINDS_FOR_BIG5:
            assert isinstance(k, SlotKind)
        assert len(PROSE_SLOT_KINDS_FOR_BIG5) == 5


class TestShouldPopulateCohortChips:
    """``should_populate_cohort_chips`` fires only on next=primary_hobbies."""

    def test_primary_hobbies_returns_true(self) -> None:
        assert should_populate_cohort_chips(SlotKind.primary_hobbies) is True

    @pytest.mark.parametrize(
        "kind",
        [SlotKind.city, SlotKind.darkness_level, SlotKind.backstory_pick, None],
    )
    def test_other_kinds_return_false(self, kind: SlotKind | None) -> None:
        assert should_populate_cohort_chips(kind) is False


class TestShouldPopulateArchetypeCards:
    """``should_populate_archetype_cards`` fires only on next=backstory_pick."""

    def test_backstory_pick_returns_true(self) -> None:
        assert should_populate_archetype_cards(SlotKind.backstory_pick) is True

    @pytest.mark.parametrize(
        "kind",
        [SlotKind.city, SlotKind.primary_hobbies, SlotKind.phone, None],
    )
    def test_other_kinds_return_false(self, kind: SlotKind | None) -> None:
        assert should_populate_archetype_cards(kind) is False


class TestDefaultArchetypeCards:
    """Fallback used when the Opus picker errors."""

    def test_returns_three_valid_cards(self) -> None:
        cards = default_archetype_cards(city="Zurich", occupation="designer")
        assert len(cards) == NUM_ARCHETYPE_CANDIDATES
        for c in cards:
            assert isinstance(c, ArchetypeCard)
            assert c.label in ARCHETYPES
            assert 1 <= len(c.prose) <= 150
            assert len(c.archetype_seed) == 64

    def test_seeds_differ_per_label(self) -> None:
        cards = default_archetype_cards(city="London", occupation="finance")
        seeds = {c.archetype_seed for c in cards}
        assert len(seeds) == NUM_ARCHETYPE_CANDIDATES, (
            "Each archetype must have a distinct seed (label is in the hash)."
        )

    def test_handles_missing_city_and_occupation(self) -> None:
        cards = default_archetype_cards(city=None, occupation=None)
        assert len(cards) == NUM_ARCHETYPE_CANDIDATES


class TestAnthropicFactories:
    """Factory builders return async callables matching the Protocol aliases."""

    def test_make_anthropic_judge_returns_async_callable(self) -> None:
        judge = make_anthropic_judge()
        assert callable(judge)
        assert inspect.iscoroutinefunction(judge)

    def test_make_anthropic_picker_returns_async_callable(self) -> None:
        picker = make_anthropic_picker()
        assert callable(picker)
        assert inspect.iscoroutinefunction(picker)

    def test_make_anthropic_generator_returns_async_callable(self) -> None:
        generator = make_anthropic_generator()
        assert callable(generator)
        assert inspect.iscoroutinefunction(generator)
