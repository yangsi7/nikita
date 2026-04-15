"""Unit tests for portal_onboarding facade — Spec 213 PR 213-3.

TDD RED phase: tests written BEFORE implementation.
All external services mocked — no live DB, no live LLM.

Coverage targets (per spec NFR-9):
  - facade process(): cache hit, cache miss, venue timeout, backstory failure
  - _scenario_to_option(): sha256 id formula, tone validation
  - PII redaction: name/phone absent from caplog records
  - FR-11 idempotence: double-call skips on already-ready state

Per .claude/rules/testing.md:
  - Non-empty fixtures for all iterator/worker paths
  - Every async def test_* has at least one assert
  - Patch source module, NOT importer
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, call, patch
from uuid import UUID, uuid4

import pytest


USER_ID = UUID("550e8400-e29b-41d4-a716-446655440000")
SAMPLE_CACHE_KEY = "berlin|techno|3|tech|music|twenties|tech"

# Minimal scenario dict that mirrors the JSONB envelope shape
SAMPLE_SCENARIO_DICT = {
    "id": "abc123def456",
    "venue": "Berghain",
    "context": "Dark basement techno night",
    "the_moment": "Our eyes locked across the dance floor",
    "unresolved_hook": "The DJ changed and she disappeared into the crowd",
    "tone": "romantic",
}
SAMPLE_ENVELOPE = {
    "scenarios": [SAMPLE_SCENARIO_DICT],
    "venues_used": ["Berghain"],
}


# ---------------------------------------------------------------------------
# _scenario_to_option converter
# ---------------------------------------------------------------------------


class TestScenarioToOption:
    """Tests for _scenario_to_option private converter (FR-3.2)."""

    def test_id_is_sha256_prefix(self):
        """id formula: sha256(cache_key:index)[:12] — deterministic, opaque."""
        import hashlib

        from nikita.services.portal_onboarding import _scenario_to_option
        from nikita.services.backstory_generator import BackstoryScenario

        scenario = BackstoryScenario(
            venue="Berghain",
            context="ctx",
            the_moment="moment",
            unresolved_hook="hook",
            tone="romantic",
        )
        option = _scenario_to_option("mykey", 0, scenario)
        expected_id = hashlib.sha256("mykey:0".encode()).hexdigest()[:12]
        assert option.id == expected_id

    def test_id_is_stable_across_calls(self):
        """Same inputs produce identical id — cache coherence invariant."""
        from nikita.services.portal_onboarding import _scenario_to_option
        from nikita.services.backstory_generator import BackstoryScenario

        scenario = BackstoryScenario(
            venue="Tresor",
            context="ctx",
            the_moment="moment",
            unresolved_hook="hook",
            tone="intellectual",
        )
        opt_a = _scenario_to_option("key", 2, scenario)
        opt_b = _scenario_to_option("key", 2, scenario)
        assert opt_a.id == opt_b.id

    def test_valid_tone_preserved(self):
        """Known valid tones pass through unchanged."""
        from nikita.services.portal_onboarding import _scenario_to_option
        from nikita.services.backstory_generator import BackstoryScenario

        for tone in ("romantic", "intellectual", "chaotic"):
            scenario = BackstoryScenario(
                venue="V", context="c", the_moment="m", unresolved_hook="h", tone=tone
            )
            opt = _scenario_to_option("k", 0, scenario)
            assert opt.tone == tone

    def test_invalid_tone_defaults_to_chaotic(self):
        """Unknown tone → 'chaotic' fallback (most flexible per spec FR-3)."""
        from nikita.services.portal_onboarding import _scenario_to_option
        from nikita.services.backstory_generator import BackstoryScenario

        scenario = BackstoryScenario(
            venue="V", context="c", the_moment="m", unresolved_hook="h", tone="mysterious"
        )
        opt = _scenario_to_option("k", 0, scenario)
        assert opt.tone == "chaotic"

    def test_all_fields_transferred(self):
        """venue, context, the_moment, unresolved_hook all copied."""
        from nikita.services.portal_onboarding import _scenario_to_option
        from nikita.services.backstory_generator import BackstoryScenario

        scenario = BackstoryScenario(
            venue="My Venue",
            context="My Context",
            the_moment="My Moment",
            unresolved_hook="My Hook",
            tone="chaotic",
        )
        opt = _scenario_to_option("k", 1, scenario)
        assert opt.venue == "My Venue"
        assert opt.context == "My Context"
        assert opt.the_moment == "My Moment"
        assert opt.unresolved_hook == "My Hook"


# ---------------------------------------------------------------------------
# PortalOnboardingFacade.process() — cache hit path
# ---------------------------------------------------------------------------


class TestFacadeProcessCacheHit:
    """Cache hit short-circuits LLM calls and returns deserialized options."""

    @pytest.fixture
    def mock_session(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_cache_hit_skips_venue_research(self, mock_session):
        """On cache hit: VenueResearchService.research_venues NOT called."""
        from nikita.services.portal_onboarding import PortalOnboardingFacade

        profile = SimpleNamespace(
            city="berlin",
            social_scene="techno",
            darkness_level=3,
            life_stage="tech",
            interest="music",
            age=28,
            occupation="engineer",
            name="Anna",
        )

        with (
            patch(
                "nikita.services.portal_onboarding.BackstoryCacheRepository"
            ) as MockCacheRepo,
            patch(
                "nikita.services.portal_onboarding.VenueResearchService"
            ) as MockVenueService,
            patch(
                "nikita.services.portal_onboarding.BackstoryGeneratorService"
            ) as MockBGService,
        ):
            mock_repo_inst = AsyncMock()
            mock_repo_inst.get.return_value = [SAMPLE_SCENARIO_DICT]
            MockCacheRepo.return_value = mock_repo_inst

            facade = PortalOnboardingFacade()
            result = await facade.process(USER_ID, profile, mock_session)

            assert len(result) == 1
            mock_repo_inst.get.assert_awaited_once()
            MockVenueService.return_value.research_venues.assert_not_called()
            MockBGService.return_value.generate_scenarios.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_hit_returns_backstory_options(self, mock_session):
        """Cache hit deserializes raw dicts → list[BackstoryOption]."""
        from nikita.onboarding.contracts import BackstoryOption
        from nikita.services.portal_onboarding import PortalOnboardingFacade

        profile = SimpleNamespace(
            city="berlin",
            social_scene="techno",
            darkness_level=3,
            life_stage="tech",
            interest="music",
            age=28,
            occupation="engineer",
            name=None,
        )

        with patch(
            "nikita.services.portal_onboarding.BackstoryCacheRepository"
        ) as MockCacheRepo:
            mock_repo_inst = AsyncMock()
            mock_repo_inst.get.return_value = [SAMPLE_SCENARIO_DICT]
            MockCacheRepo.return_value = mock_repo_inst

            with patch("nikita.services.portal_onboarding.VenueResearchService"):
                with patch("nikita.services.portal_onboarding.BackstoryGeneratorService"):
                    facade = PortalOnboardingFacade()
                    result = await facade.process(USER_ID, profile, mock_session)

            assert all(isinstance(opt, BackstoryOption) for opt in result)
            assert result[0].venue == "Berghain"


# ---------------------------------------------------------------------------
# PortalOnboardingFacade.process() — cache miss path
# ---------------------------------------------------------------------------


class TestFacadeProcessCacheMiss:
    """Cache miss triggers venue research + backstory generation."""

    @pytest.fixture
    def mock_session(self):
        return AsyncMock()

    @pytest.fixture
    def mock_profile(self):
        return SimpleNamespace(
            city="berlin",
            social_scene="techno",
            darkness_level=3,
            life_stage="tech",
            interest="music",
            age=28,
            occupation="engineer",
            name="Anna",
        )

    @pytest.mark.asyncio
    async def test_cache_miss_calls_venue_research(self, mock_session, mock_profile):
        """Cache miss: VenueResearchService.research_venues called."""
        from nikita.services.venue_research import VenueResearchResult, Venue
        from nikita.services.backstory_generator import BackstoryScenariosResult, BackstoryScenario
        from nikita.services.portal_onboarding import PortalOnboardingFacade

        mock_venues = [Venue(name="Berghain", description="dark", vibe="underground")]
        venue_result = VenueResearchResult(venues=mock_venues, fallback_used=False)
        scenario = BackstoryScenario(
            venue="Berghain", context="ctx", the_moment="m", unresolved_hook="h", tone="romantic"
        )
        backstory_result = BackstoryScenariosResult(scenarios=[scenario])

        with (
            patch(
                "nikita.services.portal_onboarding.BackstoryCacheRepository"
            ) as MockCacheRepo,
            patch(
                "nikita.services.portal_onboarding.VenueResearchService"
            ) as MockVenueService,
            patch(
                "nikita.services.portal_onboarding.BackstoryGeneratorService"
            ) as MockBGService,
        ):
            mock_repo_inst = AsyncMock()
            mock_repo_inst.get.return_value = None  # cache miss
            MockCacheRepo.return_value = mock_repo_inst

            mock_venue_inst = AsyncMock()
            mock_venue_inst.research_venues.return_value = venue_result
            MockVenueService.return_value = mock_venue_inst

            mock_bg_inst = AsyncMock()
            mock_bg_inst.generate_scenarios.return_value = backstory_result
            MockBGService.return_value = mock_bg_inst

            facade = PortalOnboardingFacade()
            result = await facade.process(USER_ID, mock_profile, mock_session)

            assert len(result) == 1
            mock_venue_inst.research_venues.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_cache_miss_writes_cache_on_success(self, mock_session, mock_profile):
        """After successful generation, result is stored in cache."""
        from nikita.services.venue_research import VenueResearchResult, Venue
        from nikita.services.backstory_generator import BackstoryScenariosResult, BackstoryScenario
        from nikita.services.portal_onboarding import PortalOnboardingFacade

        venue_result = VenueResearchResult(
            venues=[Venue(name="Tresor", description="d", vibe="v")], fallback_used=False
        )
        scenario = BackstoryScenario(
            venue="Tresor", context="c", the_moment="m", unresolved_hook="h", tone="intellectual"
        )
        backstory_result = BackstoryScenariosResult(scenarios=[scenario])

        with (
            patch(
                "nikita.services.portal_onboarding.BackstoryCacheRepository"
            ) as MockCacheRepo,
            patch(
                "nikita.services.portal_onboarding.VenueResearchService"
            ) as MockVenueService,
            patch(
                "nikita.services.portal_onboarding.BackstoryGeneratorService"
            ) as MockBGService,
        ):
            mock_repo_inst = AsyncMock()
            mock_repo_inst.get.return_value = None
            MockCacheRepo.return_value = mock_repo_inst

            mock_venue_inst = AsyncMock()
            mock_venue_inst.research_venues.return_value = venue_result
            MockVenueService.return_value = mock_venue_inst

            mock_bg_inst = AsyncMock()
            mock_bg_inst.generate_scenarios.return_value = backstory_result
            MockBGService.return_value = mock_bg_inst

            facade = PortalOnboardingFacade()
            await facade.process(USER_ID, mock_profile, mock_session)

            mock_repo_inst.set.assert_awaited_once()
            set_args = mock_repo_inst.set.call_args
            assert set_args is not None
            # cache_repo.set(cache_key, envelope_scenarios, venue_names, ttl_days)
            positional = set_args.args
            assert positional[0] == SAMPLE_CACHE_KEY  # cache_key
            assert isinstance(positional[1], list) and len(positional[1]) > 0  # envelope_scenarios
            assert isinstance(positional[1][0], dict)  # each scenario is a dict
            assert positional[2] == ["Tresor"]  # venue_names from mock
            from nikita.onboarding.tuning import BACKSTORY_CACHE_TTL_DAYS
            assert positional[3] == BACKSTORY_CACHE_TTL_DAYS

    @pytest.mark.asyncio
    async def test_cache_miss_returns_list_of_backstory_options(self, mock_session, mock_profile):
        """Cache miss returns list[BackstoryOption] after conversion."""
        from nikita.onboarding.contracts import BackstoryOption
        from nikita.services.venue_research import VenueResearchResult, Venue
        from nikita.services.backstory_generator import BackstoryScenariosResult, BackstoryScenario
        from nikita.services.portal_onboarding import PortalOnboardingFacade

        venue_result = VenueResearchResult(
            venues=[Venue(name="KitKat", description="d", vibe="wild")], fallback_used=False
        )
        scenario = BackstoryScenario(
            venue="KitKat", context="ctx", the_moment="m", unresolved_hook="h", tone="chaotic"
        )
        backstory_result = BackstoryScenariosResult(scenarios=[scenario])

        with (
            patch(
                "nikita.services.portal_onboarding.BackstoryCacheRepository"
            ) as MockCacheRepo,
            patch(
                "nikita.services.portal_onboarding.VenueResearchService"
            ) as MockVenueService,
            patch(
                "nikita.services.portal_onboarding.BackstoryGeneratorService"
            ) as MockBGService,
        ):
            mock_repo_inst = AsyncMock()
            mock_repo_inst.get.return_value = None
            MockCacheRepo.return_value = mock_repo_inst

            mock_venue_inst = AsyncMock()
            mock_venue_inst.research_venues.return_value = venue_result
            MockVenueService.return_value = mock_venue_inst

            mock_bg_inst = AsyncMock()
            mock_bg_inst.generate_scenarios.return_value = backstory_result
            MockBGService.return_value = mock_bg_inst

            facade = PortalOnboardingFacade()
            result = await facade.process(USER_ID, mock_profile, mock_session)

            assert len(result) == 1
            assert isinstance(result[0], BackstoryOption)


# ---------------------------------------------------------------------------
# Timeout handling (US-3)
# ---------------------------------------------------------------------------


class TestFacadeTimeouts:
    """Venue timeout and backstory timeout → empty list (degraded path)."""

    @pytest.fixture
    def mock_session(self):
        return AsyncMock()

    @pytest.fixture
    def mock_profile(self):
        return SimpleNamespace(
            city="berlin",
            social_scene="techno",
            darkness_level=3,
            life_stage="tech",
            interest="music",
            age=28,
            occupation="engineer",
            name=None,
        )

    @pytest.mark.asyncio
    async def test_venue_timeout_returns_empty_list(self, mock_session, mock_profile, caplog):
        """AC-3.1: On venue timeout → return [], no cache write (degraded path)."""
        from nikita.services.portal_onboarding import PortalOnboardingFacade

        with (
            patch(
                "nikita.services.portal_onboarding.BackstoryCacheRepository"
            ) as MockCacheRepo,
            patch(
                "nikita.services.portal_onboarding.VenueResearchService"
            ) as MockVenueService,
            patch(
                "nikita.services.portal_onboarding.BackstoryGeneratorService"
            ),
            patch(
                "nikita.services.portal_onboarding.asyncio.wait_for",
                side_effect=asyncio.TimeoutError,
            ),
        ):
            mock_repo_inst = AsyncMock()
            mock_repo_inst.get.return_value = None
            MockCacheRepo.return_value = mock_repo_inst

            facade = PortalOnboardingFacade()
            result = await facade.process(USER_ID, mock_profile, mock_session)

            assert result == []
            mock_repo_inst.set.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_venue_timeout_logs_outcome(self, mock_session, mock_profile, caplog):
        """AC-3.2: Venue timeout emits structured log with outcome=timeout."""
        import logging

        from nikita.services.portal_onboarding import PortalOnboardingFacade

        with (
            patch(
                "nikita.services.portal_onboarding.BackstoryCacheRepository"
            ) as MockCacheRepo,
            patch("nikita.services.portal_onboarding.VenueResearchService"),
            patch("nikita.services.portal_onboarding.BackstoryGeneratorService"),
            patch(
                "nikita.services.portal_onboarding.asyncio.wait_for",
                side_effect=asyncio.TimeoutError,
            ),
        ):
            mock_repo_inst = AsyncMock()
            mock_repo_inst.get.return_value = None
            MockCacheRepo.return_value = mock_repo_inst

            with caplog.at_level(logging.WARNING, logger="nikita.services.portal_onboarding"):
                facade = PortalOnboardingFacade()
                await facade.process(USER_ID, mock_profile, mock_session)

            # At least one log record emitted on timeout
            assert len(caplog.records) > 0

    @pytest.mark.asyncio
    async def test_backstory_failure_returns_empty(self, mock_session, mock_profile):
        """AC-4.1: BackstoryGeneratorService exception → return [] (degraded path)."""
        from nikita.services.venue_research import VenueResearchResult, Venue
        from nikita.services.portal_onboarding import PortalOnboardingFacade

        venue_result = VenueResearchResult(
            venues=[Venue(name="Berghain", description="d", vibe="v")], fallback_used=False
        )

        with (
            patch(
                "nikita.services.portal_onboarding.BackstoryCacheRepository"
            ) as MockCacheRepo,
            patch(
                "nikita.services.portal_onboarding.VenueResearchService"
            ) as MockVenueService,
            patch(
                "nikita.services.portal_onboarding.BackstoryGeneratorService"
            ) as MockBGService,
        ):
            mock_repo_inst = AsyncMock()
            mock_repo_inst.get.return_value = None
            MockCacheRepo.return_value = mock_repo_inst

            mock_venue_inst = AsyncMock()
            mock_venue_inst.research_venues.return_value = venue_result
            MockVenueService.return_value = mock_venue_inst

            mock_bg_inst = AsyncMock()
            mock_bg_inst.generate_scenarios.side_effect = RuntimeError("LLM exploded")
            MockBGService.return_value = mock_bg_inst

            facade = PortalOnboardingFacade()
            result = await facade.process(USER_ID, mock_profile, mock_session)

            assert result == []
            mock_repo_inst.set.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_backstory_failure_log_no_pii(self, mock_session, caplog):
        """AC-4.3: On backstory failure, logs must NOT contain name/phone values."""
        import logging

        from nikita.services.venue_research import VenueResearchResult
        from nikita.services.portal_onboarding import PortalOnboardingFacade

        profile_with_pii = SimpleNamespace(
            city="berlin",
            social_scene="techno",
            darkness_level=3,
            life_stage="tech",
            interest="music",
            age=28,
            occupation="engineer",
            name="Anna Karenina",  # PII — must NOT appear in logs
        )

        venue_result = VenueResearchResult(venues=[], fallback_used=True)

        with (
            patch(
                "nikita.services.portal_onboarding.BackstoryCacheRepository"
            ) as MockCacheRepo,
            patch(
                "nikita.services.portal_onboarding.VenueResearchService"
            ) as MockVenueService,
            patch(
                "nikita.services.portal_onboarding.BackstoryGeneratorService"
            ) as MockBGService,
        ):
            mock_repo_inst = AsyncMock()
            mock_repo_inst.get.return_value = None
            MockCacheRepo.return_value = mock_repo_inst

            mock_venue_inst = AsyncMock()
            mock_venue_inst.research_venues.return_value = venue_result
            MockVenueService.return_value = mock_venue_inst

            mock_bg_inst = AsyncMock()
            mock_bg_inst.generate_scenarios.side_effect = RuntimeError("failure")
            MockBGService.return_value = mock_bg_inst

            with caplog.at_level(logging.DEBUG, logger="nikita.services.portal_onboarding"):
                facade = PortalOnboardingFacade()
                await facade.process(USER_ID, profile_with_pii, mock_session)

            # PII value "Anna Karenina" must not appear in any log message
            all_log_text = " ".join(r.getMessage() for r in caplog.records)
            assert "Anna Karenina" not in all_log_text
            # City is also PII-adjacent — must not appear in logs (FR-7/NFR-3)
            assert "berlin" not in all_log_text

    @pytest.mark.asyncio
    async def test_cache_hit_log_no_pii(self, mock_session, caplog):
        """F-03/F-06: Cache-hit log path must NOT emit raw city or cache_key.

        After F-03, cache_key is replaced with an 8-char sha256 hash.
        This test verifies that the hash IS present (falsifiable), and that
        the raw cache_key string (which contains city) is NOT present.
        """
        import hashlib
        import logging

        from nikita.services.portal_onboarding import PortalOnboardingFacade

        profile_with_pii = SimpleNamespace(
            city="berlin",
            social_scene="techno",
            darkness_level=3,
            life_stage="tech",
            interest="music",
            age=28,
            occupation="engineer",
            name="Anna Karenina",  # PII — must NOT appear in logs
        )

        with (
            patch(
                "nikita.services.portal_onboarding.BackstoryCacheRepository"
            ) as MockCacheRepo,
            patch("nikita.services.portal_onboarding.VenueResearchService"),
            patch("nikita.services.portal_onboarding.BackstoryGeneratorService"),
        ):
            mock_repo_inst = AsyncMock()
            # Return cached data so we exercise the cache-hit log path
            mock_repo_inst.get.return_value = [SAMPLE_SCENARIO_DICT]
            MockCacheRepo.return_value = mock_repo_inst

            with caplog.at_level(logging.DEBUG, logger="nikita.services.portal_onboarding"):
                facade = PortalOnboardingFacade()
                await facade.process(USER_ID, profile_with_pii, mock_session)

        all_log_text = " ".join(r.getMessage() for r in caplog.records)
        # Raw PII-adjacent values must be absent
        assert "berlin" not in all_log_text
        assert "Anna Karenina" not in all_log_text
        assert SAMPLE_CACHE_KEY not in all_log_text  # raw cache_key must not appear
        # Short hash MUST appear — proves the replacement is active (falsifiable)
        expected_hash = hashlib.sha256(SAMPLE_CACHE_KEY.encode()).hexdigest()[:8]
        assert expected_hash in all_log_text


# ---------------------------------------------------------------------------
# FR-11: Bootstrap idempotence
# ---------------------------------------------------------------------------


class TestFacadeIdempotence:
    """FR-11: process() is safe to call multiple times."""

    @pytest.fixture
    def mock_session(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_cache_hit_is_idempotent(self, mock_session):
        """Calling process() twice with same profile returns consistent results.

        On cache hit path, no side effects accumulate from repeated calls.
        """
        from nikita.services.portal_onboarding import PortalOnboardingFacade

        profile = SimpleNamespace(
            city="berlin",
            social_scene="techno",
            darkness_level=3,
            life_stage="tech",
            interest="music",
            age=28,
            occupation="engineer",
            name=None,
        )

        with (
            patch(
                "nikita.services.portal_onboarding.BackstoryCacheRepository"
            ) as MockCacheRepo,
            patch("nikita.services.portal_onboarding.VenueResearchService"),
            patch("nikita.services.portal_onboarding.BackstoryGeneratorService"),
        ):
            mock_repo_inst = AsyncMock()
            # Both calls hit the cache
            mock_repo_inst.get.return_value = [SAMPLE_SCENARIO_DICT]
            MockCacheRepo.return_value = mock_repo_inst

            facade = PortalOnboardingFacade()
            result_1 = await facade.process(USER_ID, profile, mock_session)
            result_2 = await facade.process(USER_ID, profile, mock_session)

            # Same number of options returned each time
            assert len(result_1) == len(result_2) == 1
            # Cache was queried twice, set never called (already cached)
            assert mock_repo_inst.get.await_count == 2
            mock_repo_inst.set.assert_not_awaited()


# ---------------------------------------------------------------------------
# generate_preview() — preview-specific path (called by endpoint)
# ---------------------------------------------------------------------------


class TestFacadeGeneratePreview:
    """Tests for PortalOnboardingFacade.generate_preview() — FR-4a path."""

    @pytest.fixture
    def mock_session(self):
        return AsyncMock()

    @pytest.fixture
    def preview_request(self):
        from nikita.onboarding.contracts import BackstoryPreviewRequest

        return BackstoryPreviewRequest(
            city="Berlin",
            social_scene="techno",
            darkness_level=3,
        )

    @pytest.mark.asyncio
    async def test_preview_cache_hit_returns_response(self, mock_session, preview_request):
        """Cache hit on preview path returns BackstoryPreviewResponse.

        Mocks get_envelope (the production contract) not get — get() is only
        used by process() and does NOT return venues_used.
        """
        from nikita.onboarding.contracts import BackstoryPreviewResponse
        from nikita.services.portal_onboarding import PortalOnboardingFacade

        with (
            patch(
                "nikita.services.portal_onboarding.BackstoryCacheRepository"
            ) as MockCacheRepo,
            patch("nikita.services.portal_onboarding.VenueResearchService"),
            patch("nikita.services.portal_onboarding.BackstoryGeneratorService"),
        ):
            mock_repo_inst = AsyncMock()
            # get_envelope returns full envelope dict (production contract)
            mock_repo_inst.get_envelope.return_value = SAMPLE_ENVELOPE
            MockCacheRepo.return_value = mock_repo_inst

            facade = PortalOnboardingFacade()
            result = await facade.generate_preview(USER_ID, preview_request, mock_session)

            assert isinstance(result, BackstoryPreviewResponse)
            assert result.degraded is False
            assert len(result.scenarios) == 1
            assert result.venues_used == ["Berghain"]
            mock_repo_inst.get_envelope.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_preview_cache_hit_preserves_venues_used(self, mock_session, preview_request):
        """venues_used from cache envelope is propagated to the response.

        Regression guard for F-01: the old code path used get() which discards
        venues_used, causing the cache-hit path to always return venues_used=[].
        This test is falsifiable: if get_envelope reverts to get() the assertion
        on venues_used would fail because get() never returns the envelope dict.
        """
        from nikita.services.portal_onboarding import PortalOnboardingFacade

        with (
            patch(
                "nikita.services.portal_onboarding.BackstoryCacheRepository"
            ) as MockCacheRepo,
            patch("nikita.services.portal_onboarding.VenueResearchService"),
            patch("nikita.services.portal_onboarding.BackstoryGeneratorService"),
        ):
            mock_repo_inst = AsyncMock()
            mock_repo_inst.get_envelope.return_value = {
                "scenarios": [SAMPLE_SCENARIO_DICT],
                "venues_used": ["Berghain"],
            }
            MockCacheRepo.return_value = mock_repo_inst

            facade = PortalOnboardingFacade()
            result = await facade.generate_preview(USER_ID, preview_request, mock_session)

            assert result.venues_used == ["Berghain"], (
                "Cache-hit path must propagate venues_used from get_envelope; "
                "was [] (bug F-01: old code used get() which discards venues_used)"
            )

    @pytest.mark.asyncio
    async def test_preview_cache_key_stable(self, mock_session):
        """Same profile inputs → same cache_key (deterministic)."""
        from nikita.onboarding.contracts import BackstoryPreviewRequest
        from nikita.services.portal_onboarding import PortalOnboardingFacade
        from nikita.onboarding.tuning import compute_backstory_cache_key

        req = BackstoryPreviewRequest(
            city="Berlin",
            social_scene="techno",
            darkness_level=3,
            life_stage="tech",
            interest="music",
            age=28,
            occupation="engineer",
        )

        from nikita.services.venue_research import VenueResearchResult
        from nikita.services.backstory_generator import BackstoryScenariosResult

        # Single patch context — no duplicate VenueResearchService/BackstoryGeneratorService
        # patches. VenueCacheRepository is patched because the cache-miss path instantiates it.
        with (
            patch(
                "nikita.services.portal_onboarding.BackstoryCacheRepository"
            ) as MockCacheRepo,
            patch(
                "nikita.services.portal_onboarding.VenueCacheRepository"
            ),
            patch(
                "nikita.services.portal_onboarding.VenueResearchService"
            ) as MockVS,
            patch(
                "nikita.services.portal_onboarding.BackstoryGeneratorService"
            ) as MockBG,
        ):
            mock_repo_inst = AsyncMock()
            mock_repo_inst.get_envelope.return_value = None  # force cache miss
            MockCacheRepo.return_value = mock_repo_inst

            MockVS.return_value.research_venues = AsyncMock(
                return_value=VenueResearchResult(venues=[], fallback_used=True)
            )
            MockBG.return_value.generate_scenarios = AsyncMock(
                return_value=BackstoryScenariosResult(scenarios=[])
            )

            facade = PortalOnboardingFacade()
            # Compute expected key directly via tuning module
            pseudo = SimpleNamespace(
                city=req.city,
                social_scene=req.social_scene,
                darkness_level=req.darkness_level,
                life_stage=req.life_stage,
                interest=req.interest,
                age=req.age,
                occupation=req.occupation,
            )
            expected_key = compute_backstory_cache_key(pseudo)
            result = await facade.generate_preview(USER_ID, req, mock_session)
            assert result.cache_key == expected_key

    @pytest.mark.asyncio
    async def test_preview_degraded_returns_empty_scenarios(self, mock_session, preview_request):
        """On backstory timeout/error, degraded=True, scenarios=[]."""
        from nikita.services.venue_research import VenueResearchResult
        from nikita.services.portal_onboarding import PortalOnboardingFacade

        with (
            patch(
                "nikita.services.portal_onboarding.BackstoryCacheRepository"
            ) as MockCacheRepo,
            patch(
                "nikita.services.portal_onboarding.VenueResearchService"
            ) as MockVenueService,
            patch(
                "nikita.services.portal_onboarding.BackstoryGeneratorService"
            ) as MockBGService,
        ):
            mock_repo_inst = AsyncMock()
            mock_repo_inst.get_envelope.return_value = None  # cache miss for generate_preview
            MockCacheRepo.return_value = mock_repo_inst

            mock_venue_inst = AsyncMock()
            mock_venue_inst.research_venues.return_value = VenueResearchResult(
                venues=[], fallback_used=True
            )
            MockVenueService.return_value = mock_venue_inst

            mock_bg_inst = AsyncMock()
            mock_bg_inst.generate_scenarios.side_effect = RuntimeError("LLM down")
            MockBGService.return_value = mock_bg_inst

            facade = PortalOnboardingFacade()
            result = await facade.generate_preview(USER_ID, preview_request, mock_session)

            assert result.degraded is True
            assert result.scenarios == []

    @pytest.mark.asyncio
    async def test_preview_does_not_write_jsonb(self, mock_session, preview_request):
        """Preview endpoint must NOT write to users.onboarding_profile (stateless)."""
        from nikita.services.portal_onboarding import PortalOnboardingFacade
        from nikita.services.venue_research import VenueResearchResult

        # UserRepository is NOT imported in portal_onboarding.py (removed in F-01).
        # Verify the module has no UserRepository attribute — proves no JSONB write path exists.
        import nikita.services.portal_onboarding as _facade_module
        assert not hasattr(_facade_module, "UserRepository"), (
            "UserRepository must not be imported by portal_onboarding — no JSONB writes in preview"
        )

        with (
            patch(
                "nikita.services.portal_onboarding.BackstoryCacheRepository"
            ) as MockCacheRepo,
            patch(
                "nikita.services.portal_onboarding.VenueResearchService"
            ) as MockVenueService,
            patch(
                "nikita.services.portal_onboarding.BackstoryGeneratorService"
            ) as MockBGService,
        ):
            mock_repo_inst = AsyncMock()
            mock_repo_inst.get_envelope.return_value = None  # cache miss for generate_preview
            MockCacheRepo.return_value = mock_repo_inst

            mock_venue_inst = AsyncMock()
            mock_venue_inst.research_venues.return_value = VenueResearchResult(
                venues=[], fallback_used=True
            )
            MockVenueService.return_value = mock_venue_inst

            from nikita.services.backstory_generator import BackstoryScenariosResult

            mock_bg_inst = AsyncMock()
            mock_bg_inst.generate_scenarios.return_value = BackstoryScenariosResult(scenarios=[])
            MockBGService.return_value = mock_bg_inst

            facade = PortalOnboardingFacade()
            await facade.generate_preview(USER_ID, preview_request, mock_session)
            # generate_preview returns without error — no JSONB write occurred
            # (UserRepository is not even importable from this module)
