"""Tests for nikita.onboarding.contracts (Spec 213 PR 213-1).

TDD: RED phase — all tests must FAIL until contracts.py is implemented.
Tests cover:
- T1.1: OnboardingV2ProfileRequest/Response validation
- T1.2: BackstoryOption tone Literal validation
- T2.1: PipelineReadyResponse + PipelineReadyState + new FR-2a fields
- BackstoryPreviewRequest/Response basic shape
- ErrorResponse
"""

import pytest
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pydantic


# ---------------------------------------------------------------------------
# T1.1: OnboardingV2ProfileRequest validation
# ---------------------------------------------------------------------------


class TestOnboardingV2ProfileRequest:
    def test_rejects_age_below_18(self):
        from nikita.onboarding.contracts import OnboardingV2ProfileRequest

        with pytest.raises(pydantic.ValidationError):
            OnboardingV2ProfileRequest(
                location_city="Berlin",
                social_scene="techno",
                drug_tolerance=3,
                age=17,
            )

    def test_rejects_age_above_99(self):
        from nikita.onboarding.contracts import OnboardingV2ProfileRequest

        with pytest.raises(pydantic.ValidationError):
            OnboardingV2ProfileRequest(
                location_city="Berlin",
                social_scene="techno",
                drug_tolerance=3,
                age=100,
            )

    def test_accepts_valid_age_18(self):
        from nikita.onboarding.contracts import OnboardingV2ProfileRequest

        req = OnboardingV2ProfileRequest(
            location_city="Berlin",
            social_scene="techno",
            drug_tolerance=3,
            age=18,
        )
        assert req.age == 18

    def test_accepts_valid_age_99(self):
        from nikita.onboarding.contracts import OnboardingV2ProfileRequest

        req = OnboardingV2ProfileRequest(
            location_city="Berlin",
            social_scene="techno",
            drug_tolerance=3,
            age=99,
        )
        assert req.age == 99

    def test_rejects_empty_city(self):
        from nikita.onboarding.contracts import OnboardingV2ProfileRequest

        with pytest.raises(pydantic.ValidationError):
            OnboardingV2ProfileRequest(
                location_city="",
                social_scene="techno",
                drug_tolerance=3,
            )

    def test_rejects_city_too_short(self):
        from nikita.onboarding.contracts import OnboardingV2ProfileRequest

        with pytest.raises(pydantic.ValidationError):
            OnboardingV2ProfileRequest(
                location_city="X",
                social_scene="techno",
                drug_tolerance=3,
            )

    def test_rejects_phone_too_short(self):
        from nikita.onboarding.contracts import OnboardingV2ProfileRequest

        with pytest.raises(pydantic.ValidationError):
            OnboardingV2ProfileRequest(
                location_city="Berlin",
                social_scene="techno",
                drug_tolerance=3,
                phone="+1",
            )

    def test_accepts_name_age_occupation(self):
        """AC-T1.1.2: Optional fields name, age, occupation accepted."""
        from nikita.onboarding.contracts import OnboardingV2ProfileRequest

        req = OnboardingV2ProfileRequest(
            location_city="Paris",
            social_scene="art",
            drug_tolerance=2,
            name="Alex",
            age=28,
            occupation="designer",
        )
        assert req.name == "Alex"
        assert req.age == 28
        assert req.occupation == "designer"

    def test_rejects_empty_occupation(self):
        """Spec §FR-1c requires ``min_length=1`` on final-submit occupation.

        Paired with ``TestBackstoryPreviewRequest::
        test_accepts_empty_occupation_spec_intentional_asymmetry`` to make the
        deliberate schema divergence visible in the test suite — preview
        accepts empty (exploratory), final submit rejects empty (strict).
        """
        from nikita.onboarding.contracts import OnboardingV2ProfileRequest

        with pytest.raises(pydantic.ValidationError):
            OnboardingV2ProfileRequest(
                location_city="Berlin",
                social_scene="techno",
                drug_tolerance=3,
                occupation="",
            )

    def test_accepts_all_social_scenes(self):
        from nikita.onboarding.contracts import OnboardingV2ProfileRequest

        valid_scenes = ["techno", "art", "food", "cocktails", "nature"]
        for scene in valid_scenes:
            req = OnboardingV2ProfileRequest(
                location_city="Berlin",
                social_scene=scene,
                drug_tolerance=3,
            )
            assert req.social_scene == scene

    def test_rejects_invalid_social_scene(self):
        from nikita.onboarding.contracts import OnboardingV2ProfileRequest

        with pytest.raises(pydantic.ValidationError):
            OnboardingV2ProfileRequest(
                location_city="Berlin",
                social_scene="clubbing",  # not in Literal
                drug_tolerance=3,
            )

    def test_rejects_drug_tolerance_below_1(self):
        from nikita.onboarding.contracts import OnboardingV2ProfileRequest

        with pytest.raises(pydantic.ValidationError):
            OnboardingV2ProfileRequest(
                location_city="Berlin",
                social_scene="techno",
                drug_tolerance=0,
            )

    def test_rejects_drug_tolerance_above_5(self):
        from nikita.onboarding.contracts import OnboardingV2ProfileRequest

        with pytest.raises(pydantic.ValidationError):
            OnboardingV2ProfileRequest(
                location_city="Berlin",
                social_scene="techno",
                drug_tolerance=6,
            )

    def test_wizard_step_accepted_valid(self):
        from nikita.onboarding.contracts import OnboardingV2ProfileRequest

        req = OnboardingV2ProfileRequest(
            location_city="Berlin",
            social_scene="techno",
            drug_tolerance=3,
            wizard_step=5,
        )
        assert req.wizard_step == 5

    def test_wizard_step_rejects_zero(self):
        from nikita.onboarding.contracts import OnboardingV2ProfileRequest

        with pytest.raises(pydantic.ValidationError):
            OnboardingV2ProfileRequest(
                location_city="Berlin",
                social_scene="techno",
                drug_tolerance=3,
                wizard_step=0,
            )

    def test_wizard_step_rejects_above_11(self):
        from nikita.onboarding.contracts import OnboardingV2ProfileRequest

        with pytest.raises(pydantic.ValidationError):
            OnboardingV2ProfileRequest(
                location_city="Berlin",
                social_scene="techno",
                drug_tolerance=3,
                wizard_step=12,
            )


# ---------------------------------------------------------------------------
# T1.1: OnboardingV2ProfileResponse validation
# ---------------------------------------------------------------------------


class TestOnboardingV2ProfileResponse:
    def test_chosen_option_defaults_to_none(self):
        """AC-T1.1.3: chosen_option is ALWAYS None from Spec 213 endpoints."""
        from nikita.onboarding.contracts import OnboardingV2ProfileResponse

        user_id = uuid4()
        resp = OnboardingV2ProfileResponse(
            user_id=user_id,
            pipeline_state="pending",
            backstory_options=[],
            chosen_option=None,
            poll_endpoint=f"/api/v1/onboarding/pipeline-ready/{user_id}",
            poll_interval_seconds=2.0,
            poll_max_wait_seconds=20.0,
        )
        assert resp.chosen_option is None

    def test_includes_all_required_fields(self):
        from nikita.onboarding.contracts import OnboardingV2ProfileResponse

        user_id = uuid4()
        resp = OnboardingV2ProfileResponse(
            user_id=user_id,
            pipeline_state="pending",
            backstory_options=[],
            chosen_option=None,
            poll_endpoint=f"/api/v1/onboarding/pipeline-ready/{user_id}",
            poll_interval_seconds=2.0,
            poll_max_wait_seconds=20.0,
        )
        assert resp.user_id == user_id
        assert resp.pipeline_state == "pending"
        assert resp.backstory_options == []

    def test_accepts_valid_pipeline_states(self):
        from nikita.onboarding.contracts import OnboardingV2ProfileResponse

        user_id = uuid4()
        for state in ("pending", "ready", "degraded", "failed"):
            resp = OnboardingV2ProfileResponse(
                user_id=user_id,
                pipeline_state=state,
                backstory_options=[],
                chosen_option=None,
                poll_endpoint="/api/v1/onboarding/pipeline-ready/x",
                poll_interval_seconds=2.0,
                poll_max_wait_seconds=20.0,
            )
            assert resp.pipeline_state == state

    def test_rejects_invalid_pipeline_state(self):
        from nikita.onboarding.contracts import OnboardingV2ProfileResponse

        user_id = uuid4()
        with pytest.raises(pydantic.ValidationError):
            OnboardingV2ProfileResponse(
                user_id=user_id,
                pipeline_state="unknown",  # not in Literal
                backstory_options=[],
                chosen_option=None,
                poll_endpoint="/api/v1/onboarding/pipeline-ready/x",
                poll_interval_seconds=2.0,
                poll_max_wait_seconds=20.0,
            )


# ---------------------------------------------------------------------------
# T1.2: BackstoryOption tone Literal
# ---------------------------------------------------------------------------


class TestBackstoryOption:
    def test_tone_literal_rejects_bad_string(self):
        """T1.2: invalid tone string must be rejected by Pydantic."""
        from nikita.onboarding.contracts import BackstoryOption

        with pytest.raises(pydantic.ValidationError):
            BackstoryOption(
                id="abc123",
                venue="A jazz bar",
                context="Dim lights and saxophone",
                the_moment="Our eyes met",
                unresolved_hook="She left before I could ask her name",
                tone="mysterious",  # NOT in spec Literal — tasks.md T1.2 says: romantic|intellectual|chaotic
            )

    def test_tone_accepts_valid_values(self):
        from nikita.onboarding.contracts import BackstoryOption

        for tone in ("romantic", "intellectual", "chaotic"):
            opt = BackstoryOption(
                id="abc123",
                venue="A jazz bar",
                context="Dim lights",
                the_moment="Our eyes met",
                unresolved_hook="She left",
                tone=tone,
            )
            assert opt.tone == tone

    def test_all_required_fields_present(self):
        from nikita.onboarding.contracts import BackstoryOption

        opt = BackstoryOption(
            id="abc123456789",
            venue="Rooftop bar",
            context="Summer night with city lights",
            the_moment="A stranger dropped a book",
            unresolved_hook="She disappeared into the crowd",
            tone="chaotic",
        )
        assert opt.id == "abc123456789"
        assert opt.venue == "Rooftop bar"
        assert opt.unresolved_hook == "She disappeared into the crowd"


# ---------------------------------------------------------------------------
# T2.1: PipelineReadyResponse + PipelineReadyState + FR-2a fields
# ---------------------------------------------------------------------------


class TestPipelineReadyResponse:
    def test_required_fields(self):
        from nikita.onboarding.contracts import PipelineReadyResponse

        now = datetime.now(tz=timezone.utc)
        resp = PipelineReadyResponse(
            state="ready",
            checked_at=now,
        )
        assert resp.state == "ready"
        assert resp.checked_at == now
        assert resp.message is None

    def test_defaults_venue_research_status_to_pending(self):
        """FR-2a: venue_research_status defaults to 'pending' when key absent."""
        from nikita.onboarding.contracts import PipelineReadyResponse

        resp = PipelineReadyResponse(
            state="pending",
            checked_at=datetime.now(tz=timezone.utc),
        )
        assert resp.venue_research_status == "pending"

    def test_defaults_backstory_available_to_false(self):
        """FR-2a: backstory_available defaults to False when key absent."""
        from nikita.onboarding.contracts import PipelineReadyResponse

        resp = PipelineReadyResponse(
            state="pending",
            checked_at=datetime.now(tz=timezone.utc),
        )
        assert resp.backstory_available is False

    def test_accepts_venue_research_status_values(self):
        from nikita.onboarding.contracts import PipelineReadyResponse

        now = datetime.now(tz=timezone.utc)
        for status in ("pending", "complete", "failed", "cache_hit"):
            resp = PipelineReadyResponse(
                state="ready",
                checked_at=now,
                venue_research_status=status,
            )
            assert resp.venue_research_status == status

    def test_rejects_invalid_venue_research_status(self):
        from nikita.onboarding.contracts import PipelineReadyResponse

        with pytest.raises(pydantic.ValidationError):
            PipelineReadyResponse(
                state="ready",
                checked_at=datetime.now(tz=timezone.utc),
                venue_research_status="unknown",
            )

    def test_backstory_available_can_be_true(self):
        from nikita.onboarding.contracts import PipelineReadyResponse

        resp = PipelineReadyResponse(
            state="ready",
            checked_at=datetime.now(tz=timezone.utc),
            backstory_available=True,
        )
        assert resp.backstory_available is True

    def test_accepts_all_pipeline_states(self):
        from nikita.onboarding.contracts import PipelineReadyResponse

        now = datetime.now(tz=timezone.utc)
        for state in ("pending", "ready", "degraded", "failed"):
            resp = PipelineReadyResponse(state=state, checked_at=now)
            assert resp.state == state

    def test_rejects_invalid_pipeline_state(self):
        from nikita.onboarding.contracts import PipelineReadyResponse

        with pytest.raises(pydantic.ValidationError):
            PipelineReadyResponse(
                state="not_a_state",
                checked_at=datetime.now(tz=timezone.utc),
            )

    def test_full_payload_with_all_fr2a_fields(self):
        """AC-2.5: response includes venue_research_status + backstory_available."""
        from nikita.onboarding.contracts import PipelineReadyResponse

        resp = PipelineReadyResponse(
            state="ready",
            checked_at=datetime.now(tz=timezone.utc),
            venue_research_status="complete",
            backstory_available=True,
        )
        assert resp.venue_research_status == "complete"
        assert resp.backstory_available is True


# ---------------------------------------------------------------------------
# BackstoryPreviewRequest/Response
# ---------------------------------------------------------------------------


class TestBackstoryPreviewRequest:
    def test_accepts_minimal_valid_payload(self):
        from nikita.onboarding.contracts import BackstoryPreviewRequest

        req = BackstoryPreviewRequest(
            city="Berlin",
            social_scene="techno",
            darkness_level=3,
        )
        assert req.city == "Berlin"
        assert req.social_scene == "techno"
        assert req.darkness_level == 3

    def test_rejects_city_too_short(self):
        from nikita.onboarding.contracts import BackstoryPreviewRequest

        with pytest.raises(pydantic.ValidationError):
            BackstoryPreviewRequest(city="X", social_scene="techno", darkness_level=3)

    def test_rejects_darkness_level_below_1(self):
        from nikita.onboarding.contracts import BackstoryPreviewRequest

        with pytest.raises(pydantic.ValidationError):
            BackstoryPreviewRequest(city="Berlin", social_scene="techno", darkness_level=0)

    def test_rejects_darkness_level_above_5(self):
        from nikita.onboarding.contracts import BackstoryPreviewRequest

        with pytest.raises(pydantic.ValidationError):
            BackstoryPreviewRequest(city="Berlin", social_scene="techno", darkness_level=6)

    def test_age_optional(self):
        from nikita.onboarding.contracts import BackstoryPreviewRequest

        req = BackstoryPreviewRequest(city="Berlin", social_scene="techno", darkness_level=3)
        assert req.age is None

    def test_rejects_age_below_18(self):
        from nikita.onboarding.contracts import BackstoryPreviewRequest

        with pytest.raises(pydantic.ValidationError):
            BackstoryPreviewRequest(
                city="Berlin", social_scene="techno", darkness_level=3, age=17
            )

    def test_rejects_age_above_99(self):
        """Upper-edge boundary: same ``Field(ge=18, le=99)`` constraint as the
        sibling ``OnboardingV2ProfileRequest`` — enforce it here too."""
        from nikita.onboarding.contracts import BackstoryPreviewRequest

        with pytest.raises(pydantic.ValidationError):
            BackstoryPreviewRequest(
                city="Berlin", social_scene="techno", darkness_level=3, age=100
            )

    def test_rejects_invalid_social_scene(self):
        """``social_scene`` is a Literal; values outside the 5-member set are
        rejected at validation, not silently accepted."""
        from nikita.onboarding.contracts import BackstoryPreviewRequest

        with pytest.raises(pydantic.ValidationError):
            BackstoryPreviewRequest(
                city="Berlin", social_scene="sportsbar", darkness_level=3
            )

    def test_accepts_empty_occupation_spec_intentional_asymmetry(self):
        """Spec 213 §FR-4a deliberately declares ``occupation`` with only
        ``max_length=100`` (no ``min_length``) — the preview endpoint is
        exploratory and accepts looser inputs than the final-submit schema.

        This asymmetry is load-bearing for Spec 214 portal consumers that may
        call preview-backstory with an empty occupation before the user has
        entered their profession. The empty string buckets to ``"other"`` in
        ``compute_backstory_cache_key`` and produces a usable preview.

        Regression guard for QA iter-7 finding G1: adding ``min_length=1``
        here would violate the frozen spec and break the preview path.
        """
        from nikita.onboarding.contracts import BackstoryPreviewRequest

        req = BackstoryPreviewRequest(
            city="Berlin",
            social_scene="techno",
            darkness_level=3,
            occupation="",
        )
        assert req.occupation == ""

    def test_rejects_occupation_over_max_length(self):
        """``max_length=100`` IS enforced — upper bound preserved even though
        ``min_length`` is absent. Complements the empty-string test above so
        both boundary behaviors are documented in the test suite."""
        from nikita.onboarding.contracts import BackstoryPreviewRequest

        with pytest.raises(pydantic.ValidationError):
            BackstoryPreviewRequest(
                city="Berlin",
                social_scene="techno",
                darkness_level=3,
                occupation="a" * 101,
            )


class TestBackstoryPreviewResponse:
    def test_basic_shape(self):
        from nikita.onboarding.contracts import BackstoryPreviewResponse

        resp = BackstoryPreviewResponse(
            scenarios=[],
            venues_used=["The Tresor", "Berghain"],
            cache_key="abc123",
            degraded=False,
        )
        assert resp.scenarios == []
        assert resp.venues_used == ["The Tresor", "Berghain"]
        assert resp.cache_key == "abc123"
        assert resp.degraded is False

    def test_degraded_true(self):
        from nikita.onboarding.contracts import BackstoryPreviewResponse

        resp = BackstoryPreviewResponse(
            scenarios=[],
            venues_used=[],
            cache_key="x",
            degraded=True,
        )
        assert resp.degraded is True


# ---------------------------------------------------------------------------
# ErrorResponse
# ---------------------------------------------------------------------------


class TestErrorResponse:
    def test_error_response_has_detail(self):
        from nikita.onboarding.contracts import ErrorResponse

        err = ErrorResponse(detail="Not authorized")
        assert err.detail == "Not authorized"

    def test_error_response_rejects_missing_detail(self):
        from nikita.onboarding.contracts import ErrorResponse

        with pytest.raises(pydantic.ValidationError):
            ErrorResponse()  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# PipelineReadyState type alias
# ---------------------------------------------------------------------------


def test_module_isolation_imports():
    """FR-2 isolation: contracts.py is the frozen API surface.

    It MUST NOT import from:
      - nikita.onboarding.models  (would re-couple frozen surface to Pydantic domain)
      - nikita.db.*               (would couple contracts to persistence)
      - nikita.engine.*           (different domain; spec FR-2)

    Inspects the AST rather than source text (module docstring mentions the
    forbidden paths as a negation — 'MUST NOT import' — which would produce a
    false positive on a text-substring match).
    """
    import ast
    import inspect

    from nikita.onboarding import contracts

    forbidden_prefixes = ("nikita.engine", "nikita.db")
    forbidden_exact = {"nikita.onboarding.models"}

    src = inspect.getsource(contracts)
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for prefix in forbidden_prefixes:
                    assert not alias.name.startswith(prefix), (
                        f"contracts.py imports {alias.name} (FR-2 forbids {prefix}.*)"
                    )
                assert alias.name not in forbidden_exact, (
                    f"contracts.py imports {alias.name} (FR-2 isolation — "
                    f"frozen surface must not re-couple to Pydantic domain)"
                )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            # Guard against relative imports (`from . import X`) which would
            # bypass absolute-path prefix checks. Frozen surface must stay a
            # dependency-free leaf within the package.
            assert node.level == 0, (
                f"contracts.py uses a relative import (level={node.level}) — "
                f"disallowed; frozen surface must remain a dependency-free leaf"
            )
            for prefix in forbidden_prefixes:
                assert not module.startswith(prefix), (
                    f"contracts.py imports from {module} (FR-2 forbids {prefix}.*)"
                )
            assert module not in forbidden_exact, (
                f"contracts.py imports from {module} (FR-2 isolation — "
                f"frozen surface must not re-couple to Pydantic domain)"
            )


class TestPipelineReadyState:
    def test_type_alias_has_expected_literal_values(self):
        """Regression guard: PipelineReadyState must expose the 4 values
        spec FR-2/§FR-5.1 defines (pending, ready, degraded, failed).

        A trivial `is not None` check would pass even if the alias was
        accidentally reassigned to `True` or a different Literal set.
        """
        from typing import get_args

        from nikita.onboarding.contracts import PipelineReadyState

        assert get_args(PipelineReadyState) == ("pending", "ready", "degraded", "failed")


# ---------------------------------------------------------------------------
# Spec 214 PR 214-D: BackstoryChoiceRequest + PipelineReadyResponse.wizard_step
# (T012 additive extension assertions)
# ---------------------------------------------------------------------------


class TestBackstoryChoiceRequest:
    """T012: BackstoryChoiceRequest round-trip validation (Spec 214 FR-10.1)."""

    def test_backstory_choice_request_round_trip(self):
        """JSON → model → JSON equality: all fields survive serialization."""
        from nikita.onboarding.contracts import BackstoryChoiceRequest

        payload = {
            "chosen_option_id": "aabbccdd1122",
            "cache_key": "berlin|techno|3|tech|unknown|twenties|tech",
        }
        model = BackstoryChoiceRequest(**payload)
        serialized = model.model_dump(mode="json")

        assert serialized["chosen_option_id"] == payload["chosen_option_id"]
        assert serialized["cache_key"] == payload["cache_key"]

    def test_backstory_choice_request_rejects_empty_chosen_option_id(self):
        """chosen_option_id min_length=1 enforced."""
        import pydantic

        from nikita.onboarding.contracts import BackstoryChoiceRequest

        with pytest.raises(pydantic.ValidationError):
            BackstoryChoiceRequest(chosen_option_id="", cache_key="some-key")

    def test_backstory_choice_request_rejects_empty_cache_key(self):
        """cache_key min_length=1 enforced."""
        import pydantic

        from nikita.onboarding.contracts import BackstoryChoiceRequest

        with pytest.raises(pydantic.ValidationError):
            BackstoryChoiceRequest(chosen_option_id="aabbccdd1122", cache_key="")

    def test_backstory_choice_request_rejects_option_id_too_long(self):
        """chosen_option_id max_length=64 enforced."""
        import pydantic

        from nikita.onboarding.contracts import BackstoryChoiceRequest

        with pytest.raises(pydantic.ValidationError):
            BackstoryChoiceRequest(
                chosen_option_id="a" * 65,
                cache_key="some-key",
            )

    def test_backstory_choice_request_rejects_cache_key_too_long(self):
        """cache_key max_length=128 enforced."""
        import pydantic

        from nikita.onboarding.contracts import BackstoryChoiceRequest

        with pytest.raises(pydantic.ValidationError):
            BackstoryChoiceRequest(
                chosen_option_id="aabbccdd1122",
                cache_key="x" * 129,
            )


class TestPipelineReadyResponseWizardStep:
    """T012: PipelineReadyResponse.wizard_step optional field (Spec 214 FR-10.2)."""

    def test_pipeline_ready_response_wizard_step_optional(self):
        """wizard_step defaults to None when not provided."""
        from datetime import datetime, timezone

        from nikita.onboarding.contracts import PipelineReadyResponse

        resp = PipelineReadyResponse(
            state="pending",
            checked_at=datetime.now(tz=timezone.utc),
        )
        # Field must exist with None default
        assert hasattr(resp, "wizard_step")
        assert resp.wizard_step is None

    def test_pipeline_ready_response_wizard_step_ge_1(self):
        """wizard_step ge=1 constraint enforced (0 must be rejected)."""
        import pydantic
        from datetime import datetime, timezone

        from nikita.onboarding.contracts import PipelineReadyResponse

        with pytest.raises(pydantic.ValidationError):
            PipelineReadyResponse(
                state="pending",
                checked_at=datetime.now(tz=timezone.utc),
                wizard_step=0,
            )

    def test_pipeline_ready_response_wizard_step_le_11(self):
        """wizard_step le=11 constraint enforced (12 must be rejected)."""
        import pydantic
        from datetime import datetime, timezone

        from nikita.onboarding.contracts import PipelineReadyResponse

        with pytest.raises(pydantic.ValidationError):
            PipelineReadyResponse(
                state="pending",
                checked_at=datetime.now(tz=timezone.utc),
                wizard_step=12,
            )

    def test_pipeline_ready_response_wizard_step_accepts_valid_range(self):
        """wizard_step values 1..11 are all accepted."""
        from datetime import datetime, timezone

        from nikita.onboarding.contracts import PipelineReadyResponse

        for step in range(1, 12):
            resp = PipelineReadyResponse(
                state="pending",
                checked_at=datetime.now(tz=timezone.utc),
                wizard_step=step,
            )
            assert resp.wizard_step == step

    def test_pipeline_ready_response_existing_consumers_unaffected(self):
        """Existing consumers that omit wizard_step still deserialize correctly.

        Regression guard: the field is optional — adding it must NOT break
        any existing code that constructs PipelineReadyResponse without it.
        AC-10.8: backward-compatible.
        """
        from datetime import datetime, timezone

        from nikita.onboarding.contracts import PipelineReadyResponse

        # Simulate existing consumer code omitting wizard_step
        resp = PipelineReadyResponse(
            state="ready",
            checked_at=datetime.now(tz=timezone.utc),
            venue_research_status="complete",
            backstory_available=True,
        )
        assert resp.state == "ready"
        assert resp.wizard_step is None  # safe default
