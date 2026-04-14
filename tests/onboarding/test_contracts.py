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


class TestPipelineReadyState:
    def test_type_alias_exported(self):
        from nikita.onboarding.contracts import PipelineReadyState

        # Should be importable (type alias, not a class — just check it's something)
        assert PipelineReadyState is not None
