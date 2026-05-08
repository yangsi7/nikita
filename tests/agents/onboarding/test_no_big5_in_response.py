"""T-B3-8 (Spec 216-B3): NR-05 — No Big Five personality vector in API responses.

The Replika 2025 / Pi.ai precedent: users feel manipulated when their hidden
personality model is shown to them. The 13-slot wizard infers OCEAN per-turn
(216-D-code) and stores it server-side as ``users.big5_vector`` JSONB, but
NEVER surfaces it on any HTTP response.

This test grep-audits the contract surface (LegacyAnswerResponse, StateResponse,
TurnOutputEnvelope, TurnFailureEnvelope) at both schema and runtime levels:

  - **Schema-level**: ``model_json_schema()`` MUST NOT mention any of the
    8 forbidden personality terms (``big5``, ``OCEAN``, ``openness``,
    ``conscientiousness``, ``extraversion``, ``agreeableness``,
    ``neuroticism``, ``confidence``).
  - **Runtime-level**: a populated instance dumped to JSON MUST NOT contain
    any forbidden term as a key or substring.

Mirrors ``.claude/rules/agentic-design-patterns.md`` Hard Rule §1 (state is
the cumulative WizardSlots, NOT a per-turn snapshot — Big5 is orthogonal
to slot state).

Rule cross-references:
  - master spec NR-05 (no Big5 in API responses)
  - 216-B3 brief §6 (T-B3-8 audit extends to LegacyAnswerResponse)
  - .claude/rules/testing.md "Tests That Don't Test" (multiple assertions)
"""

from __future__ import annotations

import json
from uuid import UUID, uuid4

import pytest

# 8 forbidden personality-axis terms (case-insensitive) per master spec NR-05.
FORBIDDEN_TERMS: tuple[str, ...] = (
    "big5",
    "ocean",
    "openness",
    "conscientiousness",
    "extraversion",
    "agreeableness",
    "neuroticism",
    "confidence",
)


def _assert_no_forbidden(payload: str, *, where: str) -> None:
    lowered = payload.lower()
    for term in FORBIDDEN_TERMS:
        assert term.lower() not in lowered, (
            f"NR-05 violation: forbidden personality term {term!r} appears "
            f"in {where}. The 13-slot wizard infers OCEAN server-side only "
            f"(216-D-code); response payloads MUST NOT leak it (Replika 2025 "
            f"/ Pi.ai precedent)."
        )


@pytest.mark.parametrize(
    "model_path",
    [
        "nikita.agents.onboarding.answer_contracts:LegacyAnswerResponse",
        "nikita.agents.onboarding.answer_contracts:StateResponse",
        "nikita.agents.onboarding.answer_contracts:TurnOutputEnvelope",
        "nikita.agents.onboarding.answer_contracts:TurnFailureEnvelope",
    ],
)
def test_response_models_schema_omits_big5_terms(model_path: str) -> None:
    """Static check: the JSON schema for each response model MUST NOT
    mention any forbidden personality term."""
    module_path, attr = model_path.rsplit(":", 1)
    import importlib

    module = importlib.import_module(module_path)
    model = getattr(module, attr)
    schema_json = json.dumps(model.model_json_schema())
    _assert_no_forbidden(schema_json, where=f"{model_path} schema")


def test_answer_response_runtime_dump_omits_big5_terms() -> None:
    """Runtime check: a populated LegacyAnswerResponse dumped to JSON MUST NOT
    contain any forbidden personality term."""
    from nikita.agents.onboarding.answer_contracts import (
        LegacyAnswerResponse,
        TurnOutputEnvelope,
    )
    from nikita.agents.onboarding.state import SlotDelta

    response = LegacyAnswerResponse(
        output=TurnOutputEnvelope(
            delta=SlotDelta(kind="city", data={"city": "Zürich"}),
            reply="got it.",
            next_slot_kind=None,
        ),
        progress_pct=23,
        is_complete=False,
        link_code=None,
        conversation_id=UUID("11111111-2222-3333-4444-555555555555"),
        meta={"source": "llm"},
    )
    dumped = response.model_dump_json()
    _assert_no_forbidden(dumped, where="LegacyAnswerResponse runtime dump")


def test_state_response_runtime_dump_omits_big5_terms() -> None:
    """Runtime check: a populated StateResponse dumped to JSON MUST NOT
    contain any forbidden personality term."""
    from nikita.agents.onboarding.answer_contracts import StateResponse

    response = StateResponse(
        last_assistant_turn={
            "role": "nikita",
            "content": "tell me your city.",
            "timestamp": "2026-05-03T00:00:00Z",
        },
        progress_pct=15,
        is_complete=False,
        link_code=None,
        elided_extracted={},
        conversation_id=uuid4(),
    )
    dumped = response.model_dump_json()
    _assert_no_forbidden(dumped, where="StateResponse runtime dump")


def test_failure_envelope_dump_omits_big5_terms() -> None:
    """Runtime check: TurnFailureEnvelope (graceful re-ask) dumped to JSON
    MUST NOT contain any forbidden personality term."""
    from nikita.agents.onboarding.answer_contracts import TurnFailureEnvelope

    failure = TurnFailureEnvelope(
        explanation="eighteen and up only.",
        last_slot_kind=None,
    )
    dumped = failure.model_dump_json()
    _assert_no_forbidden(dumped, where="TurnFailureEnvelope runtime dump")
