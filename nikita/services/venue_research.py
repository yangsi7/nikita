"""Venue research service using Firecrawl MCP.

Part of 017-enhanced-onboarding feature.
Researches real venues in user's city for backstory generation.

T3.1: VenueResearchService
T3.2: Fallback logic
T3.3: Cache integration
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nikita.db.repositories.profile_repository import VenueCacheRepository

logger = logging.getLogger(__name__)


@dataclass
class Venue:
    """Represents a venue for backstory generation.

    AC-T3.1-005: Structured venue with name, description, vibe.
    """

    name: str
    description: str
    vibe: str


@dataclass
class VenueResearchResult:
    """Result of venue research operation.

    Contains venues list and fallback status.
    """

    venues: list[Venue] = field(default_factory=list)
    fallback_used: bool = False
    fallback_prompt: str | None = None


class VenueResearchService:
    """Service for researching venues using Firecrawl MCP.

    AC-T3.1-001: VenueResearchService class with research_venues(city, scene) method
    AC-T3.1-002: Uses Firecrawl MCP firecrawl_search for "{city} best {scene} venues"
    AC-T3.1-003: Parses results to extract venue names, descriptions, vibes
    AC-T3.1-004: Caches results in VenueCache for 30 days
    AC-T3.1-005: Returns structured list of venues with name, description, vibe

    AC-T3.2-001: On Firecrawl timeout/error, fallback to user prompt
    AC-T3.2-002: Prompt: "What's your favorite spot in {city}?"
    AC-T3.2-004: Log fallback usage for monitoring

    AC-T3.3-001: Check cache before calling Firecrawl
    AC-T3.3-002: If cache hit and not expired, return cached venues
    AC-T3.3-003: If cache miss or expired, fetch and update cache
    AC-T3.3-004: Cache key: (city.lower(), scene.lower())
    """

    # Default cache duration: 30 days
    CACHE_DURATION_DAYS = 30

    def __init__(
        self,
        venue_cache_repository: "VenueCacheRepository",
    ):
        """Initialize VenueResearchService.

        Args:
            venue_cache_repository: Repository for venue cache operations.
        """
        self.cache_repo = venue_cache_repository

    async def research_venues(
        self,
        city: str,
        scene: str,
    ) -> VenueResearchResult:
        """Research venues for a city and scene.

        AC-T3.1-001: Main research method.
        AC-T3.3-001: Check cache first.
        AC-T3.3-004: Normalize cache keys.

        Args:
            city: City name (e.g., "Berlin").
            scene: Social scene (e.g., "techno").

        Returns:
            VenueResearchResult with venues or fallback prompt.
        """
        # AC-T3.3-004: Normalize cache keys
        city_normalized = city.lower()
        scene_normalized = scene.lower()

        # AC-T3.3-001: Check cache first
        cached = await self.cache_repo.get_or_none(
            city_normalized, scene_normalized
        )

        # AC-T3.3-002: Return cached if not expired
        if cached and not self._is_expired(cached.expires_at):
            logger.info(
                f"Cache hit: city={city_normalized}, scene={scene_normalized}"
            )
            venues = [
                Venue(
                    name=v["name"],
                    description=v["description"],
                    vibe=v.get("vibe", ""),
                )
                for v in cached.venues
            ]
            return VenueResearchResult(venues=venues, fallback_used=False)

        # AC-T3.3-003: Cache miss or expired - fetch from Firecrawl
        logger.info(
            f"Cache miss: city={city_normalized}, scene={scene_normalized}"
        )

        try:
            # AC-T3.1-002: Call Firecrawl search
            raw_results = await self._search_firecrawl(city, scene)

            # AC-T3.1-003: Parse results
            venue_dicts = self._parse_search_results(raw_results)

            if venue_dicts:
                # AC-T3.1-004: Cache results
                await self.cache_repo.store(
                    city=city_normalized,
                    scene=scene_normalized,
                    venues=venue_dicts,
                    ttl_days=self.CACHE_DURATION_DAYS,
                )

                # AC-T3.1-005: Return structured venues
                venues = [
                    Venue(
                        name=v["name"],
                        description=v["description"],
                        vibe=v.get("vibe", ""),
                    )
                    for v in venue_dicts
                ]
                return VenueResearchResult(venues=venues, fallback_used=False)
            else:
                # No results - trigger fallback
                return self._create_fallback_result(city)

        except Exception as e:
            # AC-T3.2-001: Fallback on error
            # AC-T3.2-004: Log fallback usage
            logger.warning(
                f"Firecrawl search failed, using fallback: city={city}, "
                f"scene={scene}, error={e}"
            )
            return self._create_fallback_result(city)

    async def _search_firecrawl(
        self,
        city: str,
        scene: str,
    ) -> list[dict]:
        """Search venues using Firecrawl API.

        AC-T3.1-002: Uses firecrawl_search for "{city} best {scene} venues".

        This method is designed to be mocked in tests.
        In production, it calls the Firecrawl SDK.

        Args:
            city: City name.
            scene: Social scene.

        Returns:
            List of raw search results with title, description, url keys.
        """
        from nikita.config.settings import get_settings

        settings = get_settings()
        if not settings.firecrawl_api_key:
            logger.warning("FIRECRAWL_API_KEY not configured, returning empty")
            return []

        # Lazy import to avoid startup dependency
        from firecrawl import AsyncFirecrawl

        firecrawl = AsyncFirecrawl(api_key=settings.firecrawl_api_key)
        query = f"{city} best {scene} venues nightlife bars clubs"
        logger.info(f"Firecrawl search: {query}")

        try:
            results = await firecrawl.search(query, limit=10)
            # Results is a SearchData Pydantic model with .web attribute (firecrawl-py 4.x)
            # Each item is SearchResultWeb with title, description, url attributes
            web_results = results.web or []
            logger.info(f"Firecrawl returned {len(web_results)} results for {city}/{scene}")
            # Convert SearchResultWeb objects to dicts for downstream parsing
            return [
                {"title": r.title, "description": r.description or "", "url": r.url}
                for r in web_results
            ]
        except Exception as e:
            logger.error(f"Firecrawl search failed: {e}")
            return []

    def _parse_search_results(
        self,
        raw_results: list[dict],
    ) -> list[dict]:
        """Parse Firecrawl search results into venue dictionaries.

        AC-T3.1-003: Extract venue names, descriptions, vibes.

        Args:
            raw_results: Raw results from Firecrawl search.

        Returns:
            List of venue dictionaries with name, description, vibe.
        """
        venues = []

        for result in raw_results:
            name = result.get("title", "").strip()
            description = result.get("description", "").strip()

            if not name:
                continue

            # Extract vibe from description keywords
            vibe = self._extract_vibe(description)

            venues.append({
                "name": name,
                "description": description,
                "vibe": vibe,
            })

        return venues

    def _extract_vibe(self, description: str) -> str:
        """Extract vibe keywords from venue description.

        Args:
            description: Venue description text.

        Returns:
            Comma-separated vibe keywords.
        """
        # Keywords that indicate venue vibe
        vibe_keywords = {
            "underground": "underground",
            "industrial": "industrial",
            "dark": "dark",
            "intimate": "intimate",
            "energetic": "energetic",
            "chill": "chill",
            "romantic": "romantic",
            "sophisticated": "sophisticated",
            "wild": "wild",
            "artsy": "artsy",
            "hipster": "hipster",
            "mainstream": "mainstream",
            "exclusive": "exclusive",
            "friendly": "friendly",
            "legendary": "legendary",
        }

        description_lower = description.lower()
        found_vibes = []

        for keyword, vibe in vibe_keywords.items():
            if keyword in description_lower:
                found_vibes.append(vibe)

        return ", ".join(found_vibes[:3]) if found_vibes else "vibrant"

    def _is_expired(self, expires_at: datetime) -> bool:
        """Check if cache entry is expired.

        Args:
            expires_at: Expiration timestamp.

        Returns:
            True if expired, False otherwise.
        """
        now = datetime.now(timezone.utc)
        return expires_at < now

    def _create_fallback_result(self, city: str) -> VenueResearchResult:
        """Create fallback result with user prompt.

        AC-T3.2-002: Prompt: "What's your favorite spot in {city}?"

        Args:
            city: City name for prompt.

        Returns:
            VenueResearchResult with fallback prompt.
        """
        return VenueResearchResult(
            venues=[],
            fallback_used=True,
            fallback_prompt=f"What's your favorite spot in {city}? 📍",
        )

    def create_venue_from_user_input(
        self,
        user_input: str,
        city: str,
        scene: str,
    ) -> Venue:
        """Create venue from user-provided input.

        AC-T3.2-003: Accept user-provided venue and use for scenarios.

        Args:
            user_input: User's description of their favorite spot.
            city: City name.
            scene: Social scene.

        Returns:
            Venue created from user input.
        """
        # Extract venue name (first part before dash or hyphen)
        parts = user_input.split("-", 1)
        if len(parts) > 1:
            name = parts[0].strip()
            description = parts[1].strip()
        else:
            # No separator - use first few words as name
            words = user_input.split()
            if len(words) > 3:
                name = " ".join(words[:3])
                description = user_input
            else:
                name = user_input
                description = f"A special {scene} spot in {city}"

        vibe = self._extract_vibe(user_input) or f"{scene} vibes"

        return Venue(
            name=name,
            description=description,
            vibe=vibe,
        )
