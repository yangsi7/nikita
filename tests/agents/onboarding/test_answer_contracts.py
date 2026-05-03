"""T-B3-2 (Spec 216-B3): AnswerRequest / AnswerResponse / StateResponse contracts.

Pydantic v2 discriminated-union response with placeholder fields for
216-D-code wiring (cohort_chips + archetype_cards default to None).

Per spec.md HTTP API Contracts:

    class AnswerRequest:
        slot_kind: SlotKind            # StrEnum, 13 members
        value: str                      # ≤2000 chars
        turn_id: UUID4                  # idempotency key
        conversation_id: UUID4 | None   # server-issued post-turn-1

    class AnswerResponse:
        output: TurnOutputEnvelope | TurnFailureEnvelope = Field(
            discriminator="kind"
        )
        progress_pct: int               # 0..100
        is_complete: bool               # FinalForm.model_validate result
        link_code: str | None
        conversation_id: UUID4
        meta: dict[str, str] | None

Rule cross-references:
  - .claude/rules/agentic-design-patterns.md Hard Rule §2 (Pydantic completion gate)
  - .claude/rules/testing.md "Tests That Don't Test" (asserts present)
  - master spec.md "HTTP API Contracts" section
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# Module-existence + symbol exports
# ---------------------------------------------------------------------------


class TestAnswerContractsModuleSurface:
    """T-B3-2 surface: answer_contracts.py exposes the 4 expected symbols."""

    def test_module_exports_all_four_contracts(self) -> None:
        """AnswerRequest, AnswerResponse, StateResponse, and the two envelope
        types must be importable from a single module so the route layer has
        one source of truth."""
        from nikita.agents.onboarding.answer_contracts import (
            AnswerRequest,
            AnswerResponse,
            StateResponse,
            TurnOutputEnvelope,
            TurnFailureEnvelope,
        )

        assert AnswerRequest.__name__ == "AnswerRequest"
        assert AnswerResponse.__name__ == "AnswerResponse"
        assert StateResponse.__name__ == "StateResponse"
        assert TurnOutputEnvelope.__name__ == "TurnOutputEnvelope"
        assert TurnFailureEnvelope.__name__ == "TurnFailureEnvelope"


# ---------------------------------------------------------------------------
# AnswerRequest
# ---------------------------------------------------------------------------


class TestAnswerRequest:
    """AnswerRequest schema validation."""

    def test_minimal_valid_payload(self) -> None:
        from nikita.agents.onboarding.answer_contracts import AnswerRequest
        from nikita.agents.onboarding.question_registry import SlotKind

        req = AnswerRequest(
            slot_kind=SlotKind.city,
            value="Zürich",
            turn_id=uuid4(),
        )
        assert req.slot_kind == SlotKind.city
        assert req.value == "Zürich"
        assert req.conversation_id is None  # server-issued post-turn-1

    def test_value_max_length_2000(self) -> None:
        """Spec: value ≤2000 chars."""
        from nikita.agents.onboarding.answer_contracts import AnswerRequest
        from nikita.agents.onboarding.question_registry import SlotKind

        with pytest.raises(ValidationError) as exc_info:
            AnswerRequest(
                slot_kind=SlotKind.city,
                value="x" * 2001,
                turn_id=uuid4(),
            )
        assert "string" in str(exc_info.value).lower()

    def test_value_min_length_1(self) -> None:
        """Spec: value must be non-empty (clarification turns use slot_kind=no_extraction
        sentinel inside the agent, but the route always receives a real string)."""
        from nikita.agents.onboarding.answer_contracts import AnswerRequest
        from nikita.agents.onboarding.question_registry import SlotKind

        with pytest.raises(ValidationError):
            AnswerRequest(
                slot_kind=SlotKind.city,
                value="",
                turn_id=uuid4(),
            )

    def test_extra_forbid(self) -> None:
        """Defense in depth: AnswerRequest forbids unknown fields so a
        malicious client can't smuggle in bypass keys."""
        from nikita.agents.onboarding.answer_contracts import AnswerRequest
        from nikita.agents.onboarding.question_registry import SlotKind

        with pytest.raises(ValidationError) as exc_info:
            AnswerRequest(
                slot_kind=SlotKind.city,
                value="Zürich",
                turn_id=uuid4(),
                user_id="should-not-be-here",  # type: ignore[call-arg]
            )
        assert "extra" in str(exc_info.value).lower()

    def test_turn_id_must_be_uuid(self) -> None:
        from nikita.agents.onboarding.answer_contracts import AnswerRequest
        from nikita.agents.onboarding.question_registry import SlotKind

        with pytest.raises(ValidationError):
            AnswerRequest(
                slot_kind=SlotKind.city,
                value="Zürich",
                turn_id="not-a-uuid",  # type: ignore[arg-type]
            )

    def test_slot_kind_must_be_in_enum(self) -> None:
        from nikita.agents.onboarding.answer_contracts import AnswerRequest

        with pytest.raises(ValidationError):
            AnswerRequest(
                slot_kind="bogus_kind",  # type: ignore[arg-type]
                value="Zürich",
                turn_id=uuid4(),
            )


# ---------------------------------------------------------------------------
# TurnOutputEnvelope / TurnFailureEnvelope (discriminator carriers)
# ---------------------------------------------------------------------------


class TestEnvelopes:
    """Envelopes wrap TurnOutput/TurnFailure with a `kind` discriminator
    so AnswerResponse.output uses Field(discriminator='kind') without
    mutating the 216-B1+B2 agent contracts."""

    def test_turn_output_envelope_kind_is_success(self) -> None:
        from nikita.agents.onboarding.answer_contracts import TurnOutputEnvelope

        envelope = TurnOutputEnvelope(reply="hello")  # kind defaults to 'success'
        assert envelope.kind == "success"
        assert envelope.reply == "hello"
        assert envelope.delta is None
        assert envelope.next_slot_kind is None
        # 216-D-code placeholders default to None
        assert envelope.cohort_chips is None
        assert envelope.archetype_cards is None

    def test_turn_failure_envelope_kind_is_failure(self) -> None:
        from nikita.agents.onboarding.answer_contracts import TurnFailureEnvelope

        envelope = TurnFailureEnvelope(explanation="eighteen and up only.")
        assert envelope.kind == "failure"
        assert envelope.explanation == "eighteen and up only."
        assert envelope.last_slot_kind is None

    def test_envelopes_serialize_kind_field_explicitly(self) -> None:
        """The discriminator must round-trip — required for AnswerResponse
        validation when the FE replays a server response."""
        from nikita.agents.onboarding.answer_contracts import (
            TurnOutputEnvelope,
            TurnFailureEnvelope,
        )

        success_dump = TurnOutputEnvelope(reply="hi").model_dump()
        assert success_dump["kind"] == "success"
        assert "reply" in success_dump

        failure_dump = TurnFailureEnvelope(explanation="rejected").model_dump()
        assert failure_dump["kind"] == "failure"


# ---------------------------------------------------------------------------
# AnswerResponse — discriminated union
# ---------------------------------------------------------------------------


class TestAnswerResponse:
    """AnswerResponse with discriminated output union + completion gate fields."""

    def test_success_path_minimal_fields(self) -> None:
        from nikita.agents.onboarding.answer_contracts import (
            AnswerResponse,
            TurnOutputEnvelope,
        )

        conv_id = uuid4()
        resp = AnswerResponse(
            output=TurnOutputEnvelope(reply="welcome"),
            progress_pct=8,
            is_complete=False,
            conversation_id=conv_id,
        )
        assert resp.output.kind == "success"
        assert resp.progress_pct == 8
        assert resp.is_complete is False
        assert resp.link_code is None
        assert resp.meta is None

    def test_failure_path_minimal_fields(self) -> None:
        from nikita.agents.onboarding.answer_contracts import (
            AnswerResponse,
            TurnFailureEnvelope,
        )

        resp = AnswerResponse(
            output=TurnFailureEnvelope(explanation="age requirement"),
            progress_pct=8,
            is_complete=False,
            conversation_id=uuid4(),
        )
        assert resp.output.kind == "failure"

    def test_progress_pct_bounds(self) -> None:
        """0..100 inclusive."""
        from nikita.agents.onboarding.answer_contracts import (
            AnswerResponse,
            TurnOutputEnvelope,
        )

        for pct in (-1, 101, 200):
            with pytest.raises(ValidationError):
                AnswerResponse(
                    output=TurnOutputEnvelope(reply="x"),
                    progress_pct=pct,
                    is_complete=False,
                    conversation_id=uuid4(),
                )

    def test_discriminator_dispatches_correctly(self) -> None:
        """When validating a raw dict, Pydantic must dispatch to the right
        envelope based on the 'kind' field — failing-shape success body
        with kind='failure' must reject."""
        from nikita.agents.onboarding.answer_contracts import AnswerResponse

        # Mismatched kind: shape says success (has 'reply') but kind='failure'
        # should require 'explanation' instead.
        with pytest.raises(ValidationError):
            AnswerResponse.model_validate(
                {
                    "output": {"kind": "failure", "reply": "hi"},
                    "progress_pct": 0,
                    "is_complete": False,
                    "conversation_id": str(uuid4()),
                }
            )

    def test_meta_carries_fallback_reason(self) -> None:
        """B1.17: in-character fallback always-200 carries meta.fallback_reason."""
        from nikita.agents.onboarding.answer_contracts import (
            AnswerResponse,
            TurnOutputEnvelope,
        )

        resp = AnswerResponse(
            output=TurnOutputEnvelope(reply="give me a moment."),
            progress_pct=15,
            is_complete=False,
            conversation_id=uuid4(),
            meta={"fallback_reason": "UnexpectedModelBehavior"},
        )
        assert resp.meta is not None
        assert resp.meta["fallback_reason"] == "UnexpectedModelBehavior"

    def test_extra_forbid_on_response(self) -> None:
        from nikita.agents.onboarding.answer_contracts import (
            AnswerResponse,
            TurnOutputEnvelope,
        )

        with pytest.raises(ValidationError):
            AnswerResponse(
                output=TurnOutputEnvelope(reply="x"),
                progress_pct=0,
                is_complete=False,
                conversation_id=uuid4(),
                big5_vector={"O": 0.5},  # type: ignore[call-arg]
            )


# ---------------------------------------------------------------------------
# StateResponse
# ---------------------------------------------------------------------------


class TestStateResponse:
    """GET /state response — last assistant turn + cumulative state projection."""

    def test_minimal_fields(self) -> None:
        from nikita.agents.onboarding.answer_contracts import StateResponse

        resp = StateResponse(
            last_assistant_turn=None,
            progress_pct=0,
            is_complete=False,
            link_code=None,
            elided_extracted={},
            conversation_id=None,
        )
        assert resp.progress_pct == 0
        assert resp.is_complete is False
        assert resp.last_assistant_turn is None

    def test_progress_pct_bounds(self) -> None:
        from nikita.agents.onboarding.answer_contracts import StateResponse

        for pct in (-1, 101):
            with pytest.raises(ValidationError):
                StateResponse(
                    last_assistant_turn=None,
                    progress_pct=pct,
                    is_complete=False,
                    link_code=None,
                    elided_extracted={},
                    conversation_id=None,
                )


# ---------------------------------------------------------------------------
# NR-05: no Big5 leakage in any model_dump
# ---------------------------------------------------------------------------


class TestNoBig5Leakage:
    """NR-05 hard rule: Big5/OCEAN never appears in AnswerResponse or
    StateResponse JSON. Audit by string-grep on serialized output.
    """

    @pytest.mark.parametrize(
        "forbidden",
        [
            "big5",
            "OCEAN",
            "openness",
            "conscientiousness",
            "extraversion",
            "agreeableness",
            "neuroticism",
            "confidence",
        ],
    )
    def test_answer_response_omits_big5_terms(self, forbidden: str) -> None:
        from nikita.agents.onboarding.answer_contracts import (
            AnswerResponse,
            TurnOutputEnvelope,
        )

        resp = AnswerResponse(
            output=TurnOutputEnvelope(reply="welcome"),
            progress_pct=10,
            is_complete=False,
            conversation_id=uuid4(),
            meta={"fallback_reason": "none"},
        )
        dumped = resp.model_dump_json()
        assert forbidden.lower() not in dumped.lower(), (
            f"AnswerResponse leaked Big5 term '{forbidden}'. "
            "NR-05 forbids any personality-axis term in API responses."
        )
