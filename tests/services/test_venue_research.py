"""Tests for VenueResearchService.

TDD tests for T3.1, T3.2, T3.3 acceptance criteria.

T3.1: VenueResearchService
- AC-T3.1-001: VenueResearchService class with research_venues(city, scene) method
- AC-T3.1-002: Uses Firecrawl MCP firecrawl_search for "{city} best {scene} venues"
- AC-T3.1-003: Parses results to extract venue names, descriptions, vibes
- AC-T3.1-004: Caches results in VenueCache for 30 days
- AC-T3.1-005: Returns structured list of venues with name, description, vibe

T3.2: Venue Research Fallback
- AC-T3.2-001: On Firecrawl timeout/error, fallback to user prompt within 2 seconds
- AC-T3.2-002: Prompt: "What's your favorite spot in {city}?"
- AC-T3.2-003: Accept user-provided venue and use for scenarios
- AC-T3.2-004: Log fallback usage for monitoring

T3.3: Venue Cache Integration
- AC-T3.3-001: Check cache before calling Firecrawl
- AC-T3.3-002: If cache hit and not expired, return cached venues
- AC-T3.3-003: If cache miss or expired, fetch and update cache
- AC-T3.3-004: Cache key: (city.lower(), scene.lower())
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nikita.db.models.profile import VenueCache


class TestVenueResearchServiceClass:
    """Tests for VenueResearchService class structure (T3.1)."""

    def test_venue_research_service_exists(self):
        """AC-T3.1-001: VenueResearchService class exists."""
        from nikita.services.venue_research import VenueResearchService

        assert VenueResearchService is not None

    def test_has_research_venues_method(self):
        """AC-T3.1-001: Has research_venues(city, scene) method."""
        from nikita.services.venue_research import VenueResearchService

        assert hasattr(VenueResearchService, "research_venues")
        assert callable(getattr(VenueResearchService, "research_venues"))


class TestVenueModel:
    """Tests for Venue data class."""

    def test_venue_model_exists(self):
        """AC-T3.1-005: Venue model exists."""
        from nikita.services.venue_research import Venue

        assert Venue is not None

    def test_venue_has_required_fields(self):
        """AC-T3.1-005: Venue has name, description, vibe fields."""
        from nikita.services.venue_research import Venue

        venue = Venue(
            name="Berghain",
            description="Legendary techno club in Berlin",
            vibe="dark, industrial, underground",
        )

        assert venue.name == "Berghain"
        assert venue.description == "Legendary techno club in Berlin"
        assert venue.vibe == "dark, industrial, underground"


class TestVenueResearchResult:
    """Tests for VenueResearchResult data class."""

    def test_result_model_exists(self):
        """Result model exists with venues and fallback_used flag."""
        from nikita.services.venue_research import VenueResearchResult

        assert VenueResearchResult is not None

    def test_result_has_required_fields(self):
        """Result has venues list and fallback_used flag."""
        from nikita.services.venue_research import Venue, VenueResearchResult

        venues = [
            Venue(name="Test", description="Test venue", vibe="chill"),
        ]
        result = VenueResearchResult(venues=venues, fallback_used=False)

        assert result.venues == venues
        assert result.fallback_used is False


@pytest.mark.asyncio
class TestVenueResearchCacheHit:
    """Tests for cache hit behavior (T3.3)."""

    async def test_ac_t3_3_001_checks_cache_first(self):
        """AC-T3.3-001: Check cache before calling Firecrawl."""
        from nikita.services.venue_research import VenueResearchService

        cache_repo = MagicMock()
        cache_repo.get_or_none = AsyncMock(return_value=None)

        service = VenueResearchService(
            venue_cache_repository=cache_repo,
        )

        # Mock the actual search to avoid Firecrawl call
        with patch.object(service, "_search_firecrawl", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = []
            await service.research_venues("Berlin", "techno")

        # Verify cache was checked
        cache_repo.get_or_none.assert_called_once()

    async def test_ac_t3_3_002_returns_cached_if_not_expired(self):
        """AC-T3.3-002: If cache hit and not expired, return cached venues."""
        from nikita.services.venue_research import VenueResearchService

        cached_venues = [
            {"name": "Berghain", "description": "Techno temple", "vibe": "dark"},
            {"name": "Tresor", "description": "Underground classic", "vibe": "industrial"},
        ]

        cache_entry = MagicMock(spec=VenueCache)
        cache_entry.venues = cached_venues
        cache_entry.expires_at = datetime.now(timezone.utc) + timedelta(days=10)

        cache_repo = MagicMock()
        cache_repo.get_or_none = AsyncMock(return_value=cache_entry)

        service = VenueResearchService(
            venue_cache_repository=cache_repo,
        )

        result = await service.research_venues("Berlin", "techno")

        assert len(result.venues) == 2
        assert result.venues[0].name == "Berghain"
        assert result.fallback_used is False

    async def test_ac_t3_3_004_cache_key_normalized(self):
        """AC-T3.3-004: Cache key: (city.lower(), scene.lower())."""
        from nikita.services.venue_research import VenueResearchService

        cache_repo = MagicMock()
        cache_repo.get_or_none = AsyncMock(return_value=None)

        service = VenueResearchService(
            venue_cache_repository=cache_repo,
        )

        with patch.object(service, "_search_firecrawl", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = []
            await service.research_venues("BERLIN", "TECHNO")

        # Verify normalized keys were used
        cache_repo.get_or_none.assert_called_with("berlin", "techno")


@pytest.mark.asyncio
class TestVenueResearchCacheMiss:
    """Tests for cache miss and Firecrawl search (T3.1, T3.3)."""

    async def test_ac_t3_3_003_fetches_on_cache_miss(self):
        """AC-T3.3-003: If cache miss, fetch and update cache."""
        from nikita.services.venue_research import VenueResearchService

        cache_repo = MagicMock()
        cache_repo.get_or_none = AsyncMock(return_value=None)
        cache_repo.store = AsyncMock()

        service = VenueResearchService(
            venue_cache_repository=cache_repo,
        )

        # Raw Firecrawl results have 'title' not 'name'
        search_results = [
            {"title": "Berghain", "description": "Techno temple with industrial dark vibes"},
        ]

        with patch.object(service, "_search_firecrawl", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = search_results
            await service.research_venues("Berlin", "techno")

        # Verify Firecrawl was called and cache was updated
        mock_search.assert_called_once()
        cache_repo.store.assert_called_once()

    async def test_ac_t3_3_003_fetches_on_cache_expired(self):
        """AC-T3.3-003: If cache expired, fetch and update cache."""
        from nikita.services.venue_research import VenueResearchService

        expired_cache = MagicMock(spec=VenueCache)
        expired_cache.expires_at = datetime.now(timezone.utc) - timedelta(days=1)

        cache_repo = MagicMock()
        cache_repo.get_or_none = AsyncMock(return_value=expired_cache)
        cache_repo.store = AsyncMock()

        service = VenueResearchService(
            venue_cache_repository=cache_repo,
        )

        with patch.object(service, "_search_firecrawl", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = []
            await service.research_venues("Berlin", "techno")

        # Verify Firecrawl was called for expired cache
        mock_search.assert_called_once()


@pytest.mark.asyncio
class TestVenueResearchFallback:
    """Tests for fallback behavior (T3.2)."""

    async def test_ac_t3_2_001_fallback_on_firecrawl_error(self):
        """AC-T3.2-001: On Firecrawl error, fallback triggers."""
        from nikita.services.venue_research import VenueResearchService

        cache_repo = MagicMock()
        cache_repo.get_or_none = AsyncMock(return_value=None)

        service = VenueResearchService(
            venue_cache_repository=cache_repo,
        )

        with patch.object(service, "_search_firecrawl", new_callable=AsyncMock) as mock_search:
            mock_search.side_effect = Exception("Firecrawl API error")
            result = await service.research_venues("Berlin", "techno")

        # Fallback should be triggered
        assert result.fallback_used is True
        assert result.fallback_prompt is not None

    async def test_ac_t3_2_002_fallback_prompt_format(self):
        """AC-T3.2-002: Fallback prompt: 'What's your favorite spot in {city}?'"""
        from nikita.services.venue_research import VenueResearchService

        cache_repo = MagicMock()
        cache_repo.get_or_none = AsyncMock(return_value=None)

        service = VenueResearchService(
            venue_cache_repository=cache_repo,
        )

        with patch.object(service, "_search_firecrawl", new_callable=AsyncMock) as mock_search:
            mock_search.side_effect = Exception("Timeout")
            result = await service.research_venues("Berlin", "techno")

        assert "Berlin" in result.fallback_prompt
        assert "favorite" in result.fallback_prompt.lower()

    async def test_ac_t3_2_003_create_venue_from_user_input(self):
        """AC-T3.2-003: Accept user-provided venue and use for scenarios."""
        from nikita.services.venue_research import VenueResearchService

        cache_repo = MagicMock()

        service = VenueResearchService(
            venue_cache_repository=cache_repo,
        )

        result = service.create_venue_from_user_input(
            user_input="Club der Visionäre - it's this amazing outdoor spot by the canal",
            city="Berlin",
            scene="techno",
        )

        assert result.name == "Club der Visionäre"
        assert "canal" in result.description.lower() or "outdoor" in result.description.lower()


class TestVenueResultParsing:
    """Tests for parsing Firecrawl results (T3.1)."""

    def test_ac_t3_1_003_parses_search_results(self):
        """AC-T3.1-003: Parses results to extract venue names, descriptions, vibes."""
        from nikita.services.venue_research import VenueResearchService

        cache_repo = MagicMock()
        service = VenueResearchService(venue_cache_repository=cache_repo)

        # Simulate raw Firecrawl search result
        raw_results = [
            {
                "title": "Berghain",
                "url": "https://berghain.de",
                "description": "Berlin's most famous techno club known for its strict door policy",
            },
            {
                "title": "Tresor",
                "url": "https://tresorberlin.com",
                "description": "Underground techno institution since 1991",
            },
        ]

        venues = service._parse_search_results(raw_results)

        assert len(venues) == 2
        assert venues[0]["name"] == "Berghain"
        assert "techno" in venues[0]["description"].lower()

    def test_ac_t3_1_005_returns_structured_venues(self):
        """AC-T3.1-005: Returns structured list of venues."""
        from nikita.services.venue_research import VenueResearchService

        cache_repo = MagicMock()
        service = VenueResearchService(venue_cache_repository=cache_repo)

        raw_results = [
            {
                "title": "Watergate",
                "description": "Club on the Spree river with view of Oberbaum bridge",
            },
        ]

        venues = service._parse_search_results(raw_results)

        assert len(venues) == 1
        assert "name" in venues[0]
        assert "description" in venues[0]
        assert "vibe" in venues[0]


@pytest.mark.asyncio
class TestVenueResearchLogging:
    """Tests for logging behavior (T3.2)."""

    async def test_ac_t3_2_004_logs_fallback_usage(self, caplog):
        """AC-T3.2-004: Log fallback usage for monitoring."""
        import logging

        from nikita.services.venue_research import VenueResearchService

        cache_repo = MagicMock()
        cache_repo.get_or_none = AsyncMock(return_value=None)

        service = VenueResearchService(
            venue_cache_repository=cache_repo,
        )

        with patch.object(service, "_search_firecrawl", new_callable=AsyncMock) as mock_search:
            mock_search.side_effect = Exception("API error")
            with caplog.at_level(logging.WARNING):
                await service.research_venues("Berlin", "techno")

        # Check that fallback was logged
        assert any("fallback" in record.message.lower() for record in caplog.records)
