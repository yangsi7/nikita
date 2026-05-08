"""Tests for AgentEmissionState sidecar (Spec 217-3A AC-8.1, AC-8.2).

Sidecar persistence model for transient agent emission state — chiefly
``pending_followup`` which the agent emits when it wants to insert a
clarifying question before the deterministic flow advances. The sidecar
is persisted at ``users.onboarding_profile.pending_followup`` (JSONB
sibling of ``slots``) and cleared via the JSONB ``#-`` operator (NOT
via a JSON null literal — see AC-8.2 forbidden-shape rule).

Scope (217-3A.1 prereqs only): model invariants + serialization shape +
"absent vs null" disambiguation. The actual ``/answer`` route persistence
+ ``mcp__supabase__execute_sql`` round-trip belong to 217-3A.2.
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# AgentEmissionState model invariants
# ---------------------------------------------------------------------------


class TestAgentEmissionStateBasic:
    def test_default_pending_followup_is_none(self):
        from nikita.agents.onboarding.agent_emission_state import (
            AgentEmissionState,
        )

        state = AgentEmissionState()
        assert state.pending_followup is None

    def test_set_pending_followup_via_constructor(self):
        from nikita.agents.onboarding.agent_emission_state import (
            AgentEmissionState,
        )
        from nikita.agents.onboarding.converse_contracts import (
            FollowUpQuestion,
        )

        followup = FollowUpQuestion(
            question_text="what does that ritual feel like?",
            target_slot="saturday_morning",
        )
        state = AgentEmissionState(pending_followup=followup)
        assert state.pending_followup is not None
        assert state.pending_followup.target_slot == "saturday_morning"

    def test_clear_pending_followup_via_model_copy(self):
        """Spec 217-3A AC-8.2 — clearing the sidecar is the immutable-update
        idiom; downstream JSONB writer translates ``None`` into the
        ``#-`` key-removal operation, NOT a JSON null literal.
        """
        from nikita.agents.onboarding.agent_emission_state import (
            AgentEmissionState,
        )
        from nikita.agents.onboarding.converse_contracts import (
            FollowUpQuestion,
        )

        followup = FollowUpQuestion(
            question_text="tell me more?",
            target_slot="city",
        )
        state = AgentEmissionState(pending_followup=followup)
        cleared = state.model_copy(update={"pending_followup": None})
        assert cleared.pending_followup is None
        # Original unchanged (immutability of model_copy).
        assert state.pending_followup is not None


# ---------------------------------------------------------------------------
# Serialization shape — JSONB persistence contract
# ---------------------------------------------------------------------------


class TestAgentEmissionStateSerialization:
    def test_dump_omits_none_pending_followup(self):
        """When no followup is pending, ``model_dump(exclude_none=True)``
        must omit the key entirely — this is what enables the JSONB
        writer to use ``#-`` for cleanup (key absent vs key=null).

        Per Spec 217-3A AC-8.2: setting the value to JSON null is
        FORBIDDEN. The model contract serializes "no pending followup"
        as key-absence, not key-null.
        """
        from nikita.agents.onboarding.agent_emission_state import (
            AgentEmissionState,
        )

        state = AgentEmissionState()
        dumped = state.model_dump(exclude_none=True)
        assert "pending_followup" not in dumped, (
            "AgentEmissionState.model_dump(exclude_none=True) must omit "
            "pending_followup when None — Spec 217-3A AC-8.2 forbids "
            "JSON null literal in JSONB."
        )

    def test_dump_includes_set_pending_followup(self):
        from nikita.agents.onboarding.agent_emission_state import (
            AgentEmissionState,
        )
        from nikita.agents.onboarding.converse_contracts import (
            FollowUpQuestion,
        )

        followup = FollowUpQuestion(
            question_text="tell me more?",
            target_slot="city",
        )
        state = AgentEmissionState(pending_followup=followup)
        dumped = state.model_dump(exclude_none=True)
        assert "pending_followup" in dumped
        assert dumped["pending_followup"]["target_slot"] == "city"
        assert dumped["pending_followup"]["question_text"] == "tell me more?"

    def test_round_trip_through_dict(self):
        """Persist → reload via plain dict (simulates JSONB round-trip)."""
        from nikita.agents.onboarding.agent_emission_state import (
            AgentEmissionState,
        )
        from nikita.agents.onboarding.converse_contracts import (
            FollowUpQuestion,
        )

        original = AgentEmissionState(
            pending_followup=FollowUpQuestion(
                question_text="what does morning feel like?",
                target_slot="saturday_morning",
            )
        )
        wire = original.model_dump(exclude_none=True)
        restored = AgentEmissionState.model_validate(wire)
        assert restored.pending_followup is not None
        assert (
            restored.pending_followup.question_text
            == original.pending_followup.question_text
        )
        assert (
            restored.pending_followup.target_slot
            == original.pending_followup.target_slot
        )


# ---------------------------------------------------------------------------
# Forbidden shape — JSON null literal must NOT round-trip silently
# ---------------------------------------------------------------------------


class TestAgentEmissionStateForbiddenShape:
    def test_explicit_null_pending_followup_validates_as_none(self):
        """Defensive: if a stored row somehow contains a literal null
        (legacy migration, manual edit), validation must coerce it to
        the absent state — never raise. The cleanup path is what
        prevents new writes; this guards reads.
        """
        from nikita.agents.onboarding.agent_emission_state import (
            AgentEmissionState,
        )

        state = AgentEmissionState.model_validate({"pending_followup": None})
        assert state.pending_followup is None

    def test_pending_followup_field_strict_type(self):
        """``pending_followup`` is ``FollowUpQuestion | None`` — feeding
        an arbitrary dict missing required fields must raise.
        """
        from nikita.agents.onboarding.agent_emission_state import (
            AgentEmissionState,
        )
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            AgentEmissionState.model_validate(
                {"pending_followup": {"target_slot": "name"}}  # missing question_text
            )
