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
from unittest.mock import AsyncMock, MagicMock, call, patch, ANY
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

    @pytest.fixture
    def mock_user_no_profile(self):
        """User fixture with no onboarding_profile (fresh user, no pipeline_state)."""
        user = MagicMock()
        user.onboarding_profile = None
        return user

    @pytest.mark.asyncio
    async def test_cache_miss_calls_venue_research(
        self, mock_session, mock_profile, mock_user_no_profile
    ):
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
                "nikita.services.portal_onboarding.VenueCacheRepository"
            ),
            patch(
                "nikita.services.portal_onboarding.VenueResearchService"
            ) as MockVenueService,
            patch(
                "nikita.services.portal_onboarding.BackstoryGeneratorService"
            ) as MockBGService,
            patch(
                "nikita.db.repositories.user_repository.UserRepository"
            ) as MockUserRepo,
        ):
            mock_repo_inst = AsyncMock()
            mock_repo_inst.get.return_value = None  # cache miss
            MockCacheRepo.return_value = mock_repo_inst

            mock_user_repo_inst = AsyncMock()
            mock_user_repo_inst.get.return_value = mock_user_no_profile
            MockUserRepo.return_value = mock_user_repo_inst

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
    async def test_cache_miss_writes_cache_on_success(
        self, mock_session, mock_profile, mock_user_no_profile
    ):
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
                "nikita.services.portal_onboarding.VenueCacheRepository"
            ),
            patch(
                "nikita.services.portal_onboarding.VenueResearchService"
            ) as MockVenueService,
            patch(
                "nikita.services.portal_onboarding.BackstoryGeneratorService"
            ) as MockBGService,
            patch(
                "nikita.db.repositories.user_repository.UserRepository"
            ) as MockUserRepo,
        ):
            mock_repo_inst = AsyncMock()
            mock_repo_inst.get.return_value = None
            MockCacheRepo.return_value = mock_repo_inst

            mock_user_repo_inst = AsyncMock()
            mock_user_repo_inst.get.return_value = mock_user_no_profile
            MockUserRepo.return_value = mock_user_repo_inst

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
    async def test_cache_miss_returns_list_of_backstory_options(
        self, mock_session, mock_profile, mock_user_no_profile
    ):
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
                "nikita.services.portal_onboarding.VenueCacheRepository"
            ),
            patch(
                "nikita.services.portal_onboarding.VenueResearchService"
            ) as MockVenueService,
            patch(
                "nikita.services.portal_onboarding.BackstoryGeneratorService"
            ) as MockBGService,
            patch(
                "nikita.db.repositories.user_repository.UserRepository"
            ) as MockUserRepo,
        ):
            mock_repo_inst = AsyncMock()
            mock_repo_inst.get.return_value = None
            MockCacheRepo.return_value = mock_repo_inst

            mock_user_repo_inst = AsyncMock()
            mock_user_repo_inst.get.return_value = mock_user_no_profile
            MockUserRepo.return_value = mock_user_repo_inst

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

    @pytest.mark.asyncio
    async def test_process_cache_miss_writes_pipeline_state_ready(
        self, mock_session, mock_profile, mock_user_no_profile
    ):
        """N-01 regression: process() on cache miss writes pending then ready (falsifiable).

        This is the end-to-end regression that proves _bootstrap_pipeline is live in
        the process() call path.  If pipeline_state writes are ever removed from
        process(), this test will fail.
        """
        from nikita.services.venue_research import VenueResearchResult, Venue
        from nikita.services.backstory_generator import BackstoryScenariosResult, BackstoryScenario
        from nikita.services.portal_onboarding import PortalOnboardingFacade

        venue_result = VenueResearchResult(
            venues=[Venue(name="Watergate", description="d", vibe="v")], fallback_used=False
        )
        scenario = BackstoryScenario(
            venue="Watergate", context="ctx", the_moment="m", unresolved_hook="h", tone="romantic"
        )
        backstory_result = BackstoryScenariosResult(scenarios=[scenario])

        mock_update_key = AsyncMock()

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
            patch(
                "nikita.db.repositories.user_repository.UserRepository"
            ) as MockUserRepo,
        ):
            mock_cache_inst = AsyncMock()
            mock_cache_inst.get.return_value = None  # cache miss
            MockCacheRepo.return_value = mock_cache_inst

            mock_user_repo_inst = AsyncMock()
            mock_user_repo_inst.get.return_value = mock_user_no_profile
            mock_user_repo_inst.update_onboarding_profile_key = mock_update_key
            MockUserRepo.return_value = mock_user_repo_inst

            MockVS.return_value.research_venues = AsyncMock(return_value=venue_result)
            MockBG.return_value.generate_scenarios = AsyncMock(return_value=backstory_result)

            facade = PortalOnboardingFacade()
            result = await facade.process(USER_ID, mock_profile, mock_session)

        # The result list must be non-empty (happy path)
        assert len(result) == 1

        # pipeline_state transitions: pending → ready (in order)
        mock_update_key.assert_has_calls(
            [
                call(USER_ID, "pipeline_state", "pending"),
                call(USER_ID, "pipeline_state", "ready"),
            ],
            any_order=False,
        )


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

    @pytest.fixture
    def mock_user_no_profile(self):
        """User fixture with no onboarding_profile (fresh user, no pipeline_state)."""
        user = MagicMock()
        user.onboarding_profile = None
        return user

    @pytest.mark.asyncio
    async def test_venue_timeout_returns_empty_list(
        self, mock_session, mock_profile, mock_user_no_profile, caplog
    ):
        """AC-3.1: On venue timeout → return [], no cache write (degraded path)."""
        from nikita.services.portal_onboarding import PortalOnboardingFacade

        with (
            patch(
                "nikita.services.portal_onboarding.BackstoryCacheRepository"
            ) as MockCacheRepo,
            patch(
                "nikita.services.portal_onboarding.VenueCacheRepository"
            ),
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
            patch(
                "nikita.db.repositories.user_repository.UserRepository"
            ) as MockUserRepo,
        ):
            mock_repo_inst = AsyncMock()
            mock_repo_inst.get.return_value = None
            MockCacheRepo.return_value = mock_repo_inst

            mock_user_repo_inst = AsyncMock()
            mock_user_repo_inst.get.return_value = mock_user_no_profile
            MockUserRepo.return_value = mock_user_repo_inst

            facade = PortalOnboardingFacade()
            result = await facade.process(USER_ID, mock_profile, mock_session)

            assert result == []
            mock_repo_inst.set.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_venue_timeout_logs_outcome(
        self, mock_session, mock_profile, mock_user_no_profile, caplog
    ):
        """AC-3.2: Venue timeout emits structured log with outcome=timeout."""
        import logging

        from nikita.services.portal_onboarding import PortalOnboardingFacade

        with (
            patch(
                "nikita.services.portal_onboarding.BackstoryCacheRepository"
            ) as MockCacheRepo,
            patch(
                "nikita.services.portal_onboarding.VenueCacheRepository"
            ),
            patch("nikita.services.portal_onboarding.VenueResearchService"),
            patch("nikita.services.portal_onboarding.BackstoryGeneratorService"),
            patch(
                "nikita.services.portal_onboarding.asyncio.wait_for",
                side_effect=asyncio.TimeoutError,
            ),
            patch(
                "nikita.db.repositories.user_repository.UserRepository"
            ) as MockUserRepo,
        ):
            mock_repo_inst = AsyncMock()
            mock_repo_inst.get.return_value = None
            MockCacheRepo.return_value = mock_repo_inst

            mock_user_repo_inst = AsyncMock()
            mock_user_repo_inst.get.return_value = mock_user_no_profile
            MockUserRepo.return_value = mock_user_repo_inst

            with caplog.at_level(logging.WARNING, logger="nikita.services.portal_onboarding"):
                facade = PortalOnboardingFacade()
                await facade.process(USER_ID, mock_profile, mock_session)

            # At least one log record emitted on timeout
            assert len(caplog.records) > 0

    @pytest.mark.asyncio
    async def test_backstory_failure_returns_empty(
        self, mock_session, mock_profile, mock_user_no_profile
    ):
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
                "nikita.services.portal_onboarding.VenueCacheRepository"
            ),
            patch(
                "nikita.services.portal_onboarding.VenueResearchService"
            ) as MockVenueService,
            patch(
                "nikita.services.portal_onboarding.BackstoryGeneratorService"
            ) as MockBGService,
            patch(
                "nikita.db.repositories.user_repository.UserRepository"
            ) as MockUserRepo,
        ):
            mock_repo_inst = AsyncMock()
            mock_repo_inst.get.return_value = None
            MockCacheRepo.return_value = mock_repo_inst

            mock_user_repo_inst = AsyncMock()
            mock_user_repo_inst.get.return_value = mock_user_no_profile
            MockUserRepo.return_value = mock_user_repo_inst

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

        mock_user_no_profile = MagicMock()
        mock_user_no_profile.onboarding_profile = None

        with (
            patch(
                "nikita.services.portal_onboarding.BackstoryCacheRepository"
            ) as MockCacheRepo,
            patch(
                "nikita.services.portal_onboarding.VenueCacheRepository"
            ),
            patch(
                "nikita.services.portal_onboarding.VenueResearchService"
            ) as MockVenueService,
            patch(
                "nikita.services.portal_onboarding.BackstoryGeneratorService"
            ) as MockBGService,
            patch(
                "nikita.db.repositories.user_repository.UserRepository"
            ) as MockUserRepo,
        ):
            mock_repo_inst = AsyncMock()
            mock_repo_inst.get.return_value = None
            MockCacheRepo.return_value = mock_repo_inst

            mock_user_repo_inst = AsyncMock()
            mock_user_repo_inst.get.return_value = mock_user_no_profile
            MockUserRepo.return_value = mock_user_repo_inst

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
        """Cache hit on preview path returns BackstoryPreviewResponse."""
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
            # Cached envelope with both scenarios and venues_used
            mock_repo_inst.get_envelope.return_value = SAMPLE_ENVELOPE
            MockCacheRepo.return_value = mock_repo_inst

            facade = PortalOnboardingFacade()
            result = await facade.generate_preview(USER_ID, preview_request, mock_session)

            assert isinstance(result, BackstoryPreviewResponse)
            assert result.degraded is False
            assert len(result.scenarios) == 1
            assert result.venues_used == ["Berghain"]

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
            mock_repo_inst.get_envelope.return_value = None
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
        """Preview endpoint must NOT write to users.onboarding_profile (stateless).

        Behavioral assertion: UserRepository is never instantiated or called during
        generate_preview(). This catches both module-level imports AND function-local
        imports that would reach UserRepository regardless of namespace presence.

        Per .claude/rules/testing.md: patch source module, not importer.
        """
        from nikita.services.portal_onboarding import PortalOnboardingFacade
        from nikita.services.venue_research import VenueResearchResult

        with (
            patch(
                "nikita.db.repositories.user_repository.UserRepository"
            ) as MockUserRepo,
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
            mock_repo_inst.get_envelope.return_value = None
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
            result = await facade.generate_preview(USER_ID, preview_request, mock_session)

            # Empirical proof: UserRepository was never instantiated during generate_preview.
            # This enforces the "no JSONB writes" contract regardless of import arrangement.
            MockUserRepo.assert_not_called()
            # Sanity: the call returned a valid response (not an error path)
            assert result is not None


# ---------------------------------------------------------------------------
# FR-5.1 + FR-5.2 + FR-11: _bootstrap_pipeline state transitions + idempotence
# ---------------------------------------------------------------------------


class TestFacadeBootstrap:
    """Tests for PortalOnboardingFacade._bootstrap_pipeline.

    Covers FR-5.1 (pipeline_state machine), FR-5.2 (update_onboarding_profile_key),
    and FR-11 (idempotence: skip if state already 'ready').

    Per spec tasks.md T3.2, T3.4, T4.3, TB.1, TB.2.
    """

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

    @pytest.fixture
    def mock_user_not_ready(self):
        """Non-empty user fixture with pipeline_state != 'ready'."""
        user = MagicMock()
        user.onboarding_profile = {"pipeline_state": "pending"}
        return user

    @pytest.fixture
    def mock_user_already_ready(self):
        """User fixture where pipeline_state is already 'ready' (idempotence case)."""
        user = MagicMock()
        user.onboarding_profile = {"pipeline_state": "ready"}
        return user

    @pytest.fixture
    def mock_user_no_profile(self):
        """User fixture with no onboarding_profile (fresh user)."""
        user = MagicMock()
        user.onboarding_profile = None
        return user

    # ------------------------------------------------------------------
    # T3.2 / T3.4: success path — writes pending → ready
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_pipeline_state_transitions_success(
        self, mock_session, mock_profile, mock_user_no_profile
    ):
        """Happy path: _bootstrap_pipeline writes pending then ready (T3.2).

        Verifies update_onboarding_profile_key called with "pending" first,
        then "ready" on full success.  Uses assert_has_calls to verify order.

        Patches UserRepository at its source module (per testing.md rule:
        patch source module for function-local imports).
        """
        from nikita.services.venue_research import VenueResearchResult, Venue
        from nikita.services.backstory_generator import BackstoryScenariosResult, BackstoryScenario
        from nikita.services.portal_onboarding import PortalOnboardingFacade

        mock_venues = [Venue(name="Berghain", description="dark", vibe="underground")]
        venue_result = VenueResearchResult(venues=mock_venues, fallback_used=False)
        scenario = BackstoryScenario(
            venue="Berghain", context="ctx", the_moment="m", unresolved_hook="h", tone="romantic"
        )
        backstory_result = BackstoryScenariosResult(scenarios=[scenario])

        mock_update_key = AsyncMock()

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
            # Patch at source module — function-local import resolves through sys.modules
            patch(
                "nikita.db.repositories.user_repository.UserRepository"
            ) as MockUserRepo,
        ):
            mock_cache_inst = AsyncMock()
            mock_cache_inst.get.return_value = None
            MockCacheRepo.return_value = mock_cache_inst

            # UserRepository.get returns a user with no pipeline_state set yet
            mock_user_repo_inst = AsyncMock()
            mock_user_repo_inst.get.return_value = mock_user_no_profile
            mock_user_repo_inst.update_onboarding_profile_key = mock_update_key
            MockUserRepo.return_value = mock_user_repo_inst

            MockVS.return_value.research_venues = AsyncMock(return_value=venue_result)
            MockBG.return_value.generate_scenarios = AsyncMock(return_value=backstory_result)

            facade = PortalOnboardingFacade()
            result = await facade._bootstrap_pipeline(USER_ID, mock_profile, mock_session)

        # Must have been called with pending then ready (in that order)
        mock_update_key.assert_has_calls(
            [
                call(USER_ID, "pipeline_state", "pending"),
                call(USER_ID, "pipeline_state", "ready"),
            ],
            any_order=False,
        )
        assert isinstance(result, list)

    # ------------------------------------------------------------------
    # T3.4: venue timeout → degraded
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_pipeline_state_transitions_venue_timeout(
        self, mock_session, mock_profile, mock_user_no_profile
    ):
        """AC-3.4: On venue timeout, pipeline_state written as 'degraded' (T3.4)."""
        from nikita.services.portal_onboarding import PortalOnboardingFacade

        mock_update_key = AsyncMock()

        with (
            patch(
                "nikita.services.portal_onboarding.BackstoryCacheRepository"
            ) as MockCacheRepo,
            patch(
                "nikita.services.portal_onboarding.VenueCacheRepository"
            ),
            patch(
                "nikita.services.portal_onboarding.VenueResearchService"
            ),
            patch(
                "nikita.services.portal_onboarding.BackstoryGeneratorService"
            ),
            patch(
                "nikita.services.portal_onboarding.asyncio.wait_for",
                side_effect=asyncio.TimeoutError,
            ),
            patch(
                "nikita.db.repositories.user_repository.UserRepository"
            ) as MockUserRepo,
        ):
            mock_cache_inst = AsyncMock()
            mock_cache_inst.get.return_value = None
            MockCacheRepo.return_value = mock_cache_inst

            mock_user_repo_inst = AsyncMock()
            mock_user_repo_inst.get.return_value = mock_user_no_profile
            mock_user_repo_inst.update_onboarding_profile_key = mock_update_key
            MockUserRepo.return_value = mock_user_repo_inst

            facade = PortalOnboardingFacade()
            result = await facade._bootstrap_pipeline(USER_ID, mock_profile, mock_session)

        assert result == []
        # Must have written pending (entry) then degraded (timeout)
        mock_update_key.assert_has_calls(
            [
                call(USER_ID, "pipeline_state", "pending"),
                call(USER_ID, "pipeline_state", "degraded"),
            ],
            any_order=False,
        )

    # ------------------------------------------------------------------
    # T4.3: backstory failure → degraded
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_pipeline_state_transitions_backstory_fail(
        self, mock_session, mock_profile, mock_user_no_profile
    ):
        """AC-4.4: On backstory generator failure, pipeline_state='degraded' (T4.3)."""
        from nikita.services.venue_research import VenueResearchResult, Venue
        from nikita.services.portal_onboarding import PortalOnboardingFacade

        venue_result = VenueResearchResult(
            venues=[Venue(name="Tresor", description="d", vibe="v")], fallback_used=False
        )

        mock_update_key = AsyncMock()

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
            patch(
                "nikita.db.repositories.user_repository.UserRepository"
            ) as MockUserRepo,
        ):
            mock_cache_inst = AsyncMock()
            mock_cache_inst.get.return_value = None
            MockCacheRepo.return_value = mock_cache_inst

            mock_user_repo_inst = AsyncMock()
            mock_user_repo_inst.get.return_value = mock_user_no_profile
            mock_user_repo_inst.update_onboarding_profile_key = mock_update_key
            MockUserRepo.return_value = mock_user_repo_inst

            MockVS.return_value.research_venues = AsyncMock(return_value=venue_result)
            MockBG.return_value.generate_scenarios = AsyncMock(
                side_effect=RuntimeError("LLM down")
            )

            facade = PortalOnboardingFacade()
            result = await facade._bootstrap_pipeline(USER_ID, mock_profile, mock_session)

        assert result == []
        mock_update_key.assert_has_calls(
            [
                call(USER_ID, "pipeline_state", "pending"),
                call(USER_ID, "pipeline_state", "degraded"),
            ],
            any_order=False,
        )

    # ------------------------------------------------------------------
    # TB.1: idempotence — skip if state already 'ready'
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_pipeline_state_idempotent_skip(
        self, mock_session, mock_profile, mock_user_already_ready
    ):
        """TB.1: Second call when state='ready' skips VenueResearch + Backstory (FR-11).

        Verifies VenueResearchService and BackstoryGeneratorService are NOT
        called when pipeline_state is already 'ready'.
        """
        from nikita.services.portal_onboarding import PortalOnboardingFacade

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
            patch(
                "nikita.db.repositories.user_repository.UserRepository"
            ) as MockUserRepo,
        ):
            mock_cache_inst = AsyncMock()
            MockCacheRepo.return_value = mock_cache_inst

            mock_user_repo_inst = AsyncMock()
            # Returns ready-state user → idempotence skip
            mock_user_repo_inst.get.return_value = mock_user_already_ready
            MockUserRepo.return_value = mock_user_repo_inst

            facade = PortalOnboardingFacade()
            result = await facade._bootstrap_pipeline(USER_ID, mock_profile, mock_session)

        # Must not have called services
        MockVS.return_value.research_venues.assert_not_called()
        MockBG.return_value.generate_scenarios.assert_not_called()
        # Returns empty list (no-op path)
        assert result == []

    # ------------------------------------------------------------------
    # TB.1b: idempotence — skip if state already 'pending' (FR-11)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_pipeline_state_idempotent_skip_when_pending(
        self, mock_session, mock_profile, mock_user_not_ready, caplog
    ):
        """TB.1b: Concurrent call when state='pending' returns immediately (FR-11).

        Verifies VenueResearchService and BackstoryGeneratorService are NOT
        called when pipeline_state is already 'pending', and outcome=already_pending
        is logged.
        """
        import logging
        from nikita.services.portal_onboarding import PortalOnboardingFacade

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
            patch(
                "nikita.db.repositories.user_repository.UserRepository"
            ) as MockUserRepo,
        ):
            mock_cache_inst = AsyncMock()
            MockCacheRepo.return_value = mock_cache_inst

            mock_user_repo_inst = AsyncMock()
            # Returns a user with pipeline_state='pending' → concurrent bootstrap
            mock_user_repo_inst.get.return_value = mock_user_not_ready
            MockUserRepo.return_value = mock_user_repo_inst

            facade = PortalOnboardingFacade()
            with caplog.at_level(logging.INFO, logger="nikita.services.portal_onboarding"):
                result = await facade._bootstrap_pipeline(USER_ID, mock_profile, mock_session)

        # Must not have called venue/backstory services
        MockVS.return_value.research_venues.assert_not_called()
        MockBG.return_value.generate_scenarios.assert_not_called()
        # Returns empty list (no-op path)
        assert result == []
        # outcome=already_pending must be logged
        assert any("already_pending" in r.message for r in caplog.records)

    # ------------------------------------------------------------------
    # Uncaught exception → 'failed' + re-raise
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_pipeline_state_transitions_on_uncaught_exception(
        self, mock_session, mock_profile, mock_user_no_profile
    ):
        """Uncaught Exception writes 'failed' to pipeline_state then re-raises."""
        from nikita.services.portal_onboarding import PortalOnboardingFacade

        mock_update_key = AsyncMock()

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
            ),
            patch(
                "nikita.db.repositories.user_repository.UserRepository"
            ) as MockUserRepo,
        ):
            mock_cache_inst = AsyncMock()
            mock_cache_inst.get.return_value = None
            MockCacheRepo.return_value = mock_cache_inst

            mock_user_repo_inst = AsyncMock()
            mock_user_repo_inst.get.return_value = mock_user_no_profile
            mock_user_repo_inst.update_onboarding_profile_key = mock_update_key
            MockUserRepo.return_value = mock_user_repo_inst

            # Cause an unexpected error inside venue research (not TimeoutError)
            class _UnexpectedError(Exception):
                pass

            MockVS.return_value.research_venues = AsyncMock(
                side_effect=_UnexpectedError("disk full")
            )

            facade = PortalOnboardingFacade()
            with pytest.raises(_UnexpectedError):
                await facade._bootstrap_pipeline(USER_ID, mock_profile, mock_session)

        # Must have written pending then failed
        mock_update_key.assert_has_calls(
            [
                call(USER_ID, "pipeline_state", "pending"),
                call(USER_ID, "pipeline_state", "failed"),
            ],
            any_order=False,
        )
