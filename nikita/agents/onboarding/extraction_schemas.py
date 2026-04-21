"""Pydantic extraction schemas for the conversational onboarding agent.

Six schemas — one per wizard topic — that the Pydantic AI agent can
emit as tool calls when it has extracted a concrete field from the
conversation:

- ``LocationExtraction`` — city
- ``SceneExtraction`` — social scene + optional life stage
- ``DarknessExtraction`` — drug tolerance 1-5
- ``IdentityExtraction`` — name / age / occupation
- ``BackstoryExtraction`` — chosen backstory option + cache_key
- ``PhoneExtraction`` — phone preference + optional E.164 phone number

Each schema carries a ``confidence: float`` (0.0-1.0) — values below
``CONFIDENCE_CONFIRMATION_THRESHOLD`` trigger the
``confirmation_required=true`` response branch.

Cross-cutting validation (AC-11d.3):

- ``IdentityExtraction.age`` ge=18 per ``MIN_USER_AGE``. <18 raises
  ``ValidationError``; the endpoint maps this to an in-character
  rejection rather than a 422 (AC-11d.9).
- ``PhoneExtraction.phone`` required when ``phone_preference == "voice"``
  and must parse as E.164 via ``phonenumbers``.

Union ``ConverseResult`` with a sentinel ``NoExtraction`` branch lets
the agent explicitly declare "no extraction this turn" on off-topic or
backtracking turns rather than emitting spurious tool calls.

Per ``.claude/rules/testing.md`` — no raw PII (name/age/occupation/phone)
appears in module-level log lines; this module logs nothing.
"""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from nikita.onboarding.tuning import MIN_USER_AGE


# ---------------------------------------------------------------------------
# Shared Literal type aliases (GH #382 D4/D4b — single source of truth)
# ---------------------------------------------------------------------------
# Both the Pydantic extraction schemas (below) AND the Pydantic AI tool
# signatures in ``conversation_agent.py`` must use these aliases, so that
# the LLM tool-call boundary rejects freeform strings identically to the
# model_validate path. Reviewers: do NOT duplicate these Literal sets at
# the tool-signature site; import these aliases.

SceneValue = Literal["techno", "art", "food", "cocktails", "nature"]
"""Allowed social-scene values. Any drift MUST update this single alias."""

LifeStageValue = Literal[
    "tech", "finance", "creative", "student", "entrepreneur", "other"
]
"""Allowed life-stage enumeration."""

PhonePreferenceValue = Literal["voice", "text"]
"""Allowed phone-preference modes."""

NoExtractionReasonValue = Literal[
    "off_topic", "clarifying", "backtracking", "low_confidence"
]
"""Allowed NoExtraction.reason values."""

DrugToleranceValue = Annotated[int, Field(ge=1, le=5)]
"""Constrained int for DarknessExtraction.drug_tolerance (1-5 scale).

Uses Annotated[int, Field()] rather than Literal so the tool JSON schema
emits {"type":"integer","minimum":1,"maximum":5} (range constraint) instead
of an enum. Pydantic v2 propagates ge/le into JSON schema correctly. Do NOT
change to bare int — that removes the LLM-facing constraint.
"""


# ---------------------------------------------------------------------------
# Per-topic extraction schemas
# ---------------------------------------------------------------------------


class _ConfidenceMixin(BaseModel):
    """Shared ``confidence`` field enforced across every extraction."""

    model_config = ConfigDict(extra="forbid")

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "0.0-1.0. Below CONFIDENCE_CONFIRMATION_THRESHOLD (0.85) the "
            "endpoint sets confirmation_required=true instead of committing "
            "the extraction directly."
        ),
    )


class LocationExtraction(_ConfidenceMixin):
    """Agent emits this when the user has stated a city."""

    kind: Literal["location"] = "location"
    city: str = Field(min_length=2, max_length=100)


class SceneExtraction(_ConfidenceMixin):
    """Agent emits this when the user has picked a social scene."""

    kind: Literal["scene"] = "scene"
    scene: SceneValue
    life_stage: LifeStageValue | None = None


class DarknessExtraction(_ConfidenceMixin):
    """Agent emits this when the user has chosen a 1-5 darkness rating."""

    kind: Literal["darkness"] = "darkness"
    drug_tolerance: DrugToleranceValue


class IdentityExtraction(_ConfidenceMixin):
    """Agent emits this when at least one of name/age/occupation is given.

    Server-enforced ``age >= MIN_USER_AGE`` (18). Under-18 raises
    ``ValidationError`` — the endpoint returns a 200 in-character
    rejection rather than exposing the 422 to the client (AC-11d.9).
    """

    kind: Literal["identity"] = "identity"
    name: str | None = Field(default=None, max_length=100)
    age: int | None = Field(default=None, ge=MIN_USER_AGE, le=99)
    occupation: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def _at_least_one_field(self) -> "IdentityExtraction":
        if self.name is None and self.age is None and self.occupation is None:
            raise ValueError(
                "identity extraction requires at least one of "
                "name / age / occupation"
            )
        return self


class BackstoryExtraction(_ConfidenceMixin):
    """Agent emits this when the user has picked a backstory scenario."""

    kind: Literal["backstory"] = "backstory"
    chosen_option_id: str = Field(pattern=r"^[a-f0-9]{12}$")
    cache_key: str = Field(pattern=r"^[a-z0-9_\-|]{1,128}$")


class PhoneExtraction(_ConfidenceMixin):
    """Agent emits this when the user has chosen voice or text.

    Voice requires a phone number that parses as E.164 via
    ``phonenumbers.parse``. Text is valid with ``phone=None``.
    """

    kind: Literal["phone"] = "phone"
    phone_preference: PhonePreferenceValue
    phone: str | None = None

    @field_validator("phone")
    @classmethod
    def _phone_format(cls, value: str | None) -> str | None:
        """Validate + normalize to E.164.

        Prefers ``phonenumbers`` when available (matches the existing
        ``nikita/onboarding/validation.py`` stack); falls back to a pure
        regex E.164 guard so this module remains usable without the
        phonenumbers dep (e.g. for tuning-only tests and for the
        lightweight ``extraction_schemas`` import paths).
        """
        if value is None:
            return value
        try:  # preferred: phonenumbers E.164 parser (matches validation.py)
            import phonenumbers
        except ImportError:  # pragma: no cover — phonenumbers optional
            import re

            stripped = re.sub(r"[\s\-()]", "", value)
            if not re.fullmatch(r"\+[1-9][0-9]{7,19}", stripped):
                raise ValueError(
                    "phone must be E.164 (e.g. +14155552671)"
                )
            return stripped
        # N4 QA iter-1: catch the specific phonenumbers parse exception
        # rather than bare `Exception`, which previously swallowed
        # unrelated errors (KeyError, MemoryError) silently.
        try:
            parsed = phonenumbers.parse(value, None)
        except phonenumbers.NumberParseException as exc:
            raise ValueError(f"phone must be E.164: {exc}") from exc
        if not phonenumbers.is_valid_number(parsed):
            raise ValueError("phone is not a valid E.164 number")
        return phonenumbers.format_number(
            parsed, phonenumbers.PhoneNumberFormat.E164
        )

    @model_validator(mode="after")
    def _voice_requires_phone(self) -> "PhoneExtraction":
        if self.phone_preference == "voice" and not self.phone:
            raise ValueError("phone_preference='voice' requires a phone number")
        return self


# ---------------------------------------------------------------------------
# No-extraction sentinel + union result type
# ---------------------------------------------------------------------------


class NoExtraction(BaseModel):
    """Sentinel emitted when the agent chose not to extract a field this turn.

    Distinguishes "off-topic / backtracking / clarifying" turns from
    low-confidence extractions. Keeps ``ConverseResult`` a proper union
    so Pydantic round-trip always succeeds (vs. ``None`` which the
    endpoint would have to special-case).
    """

    model_config = ConfigDict(extra="forbid")

    kind: Literal["no_extraction"] = "no_extraction"
    reason: NoExtractionReasonValue = "off_topic"


# Discriminated union of 6 extractions + 1 no_extraction sentinel = 7 branches.
# The ``kind`` literal discriminator gives Pydantic a fast-path decoder and
# guarantees round-trip stability for the endpoint's idempotency cache.
ConverseResult = Annotated[
    Union[
        LocationExtraction,
        SceneExtraction,
        DarknessExtraction,
        IdentityExtraction,
        BackstoryExtraction,
        PhoneExtraction,
        NoExtraction,
    ],
    Field(discriminator="kind"),
]


__all__ = [
    "BackstoryExtraction",
    "ConverseResult",
    "DarknessExtraction",
    "DrugToleranceValue",
    "IdentityExtraction",
    "LifeStageValue",
    "LocationExtraction",
    "NoExtraction",
    "NoExtractionReasonValue",
    "PhoneExtraction",
    "PhonePreferenceValue",
    "SceneExtraction",
    "SceneValue",
]
