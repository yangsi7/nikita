"""
Vice Scorer Module (T012, T016, T017)

Processes vice signals to update user intensity scores.
Manages vice profile persistence and retrieval.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from nikita.config.enums import ViceCategory
from nikita.engine.vice.models import ViceProfile, ViceSignal

if TYPE_CHECKING:
    from nikita.db.repositories.vice_repository import VicePreferenceRepository


# Scoring constants
POSITIVE_SIGNAL_MULTIPLIER = Decimal("1.0")  # How much positive signals add
NEGATIVE_SIGNAL_MULTIPLIER = Decimal("0.5")  # How much rejections subtract
MIN_CONFIDENCE_THRESHOLD = Decimal("0.50")  # Minimum confidence to process

# Spec 106 I13: Chapter-adaptive vice discovery sensitivity
# Higher multiplier = more sensitive to vice signals (discover faster)
CHAPTER_SENSITIVITY_MULTIPLIERS: dict[int, Decimal] = {
    1: Decimal("1.5"),   # New relationship: heightened discovery
    2: Decimal("1.25"),  # Still learning
    3: Decimal("1.0"),   # Baseline
    4: Decimal("0.75"),  # Established — less aggressive discovery
    5: Decimal("0.5"),   # Mature — vices well-known
}


class ViceScorer:
    """T012, T016, T017: Vice score processor.

    Handles:
    - Processing vice signals to update intensities
    - Retrieving user vice profiles
    - Getting top vices for prompt injection

    Spec 037 T1.2: Supports async close for resource safety.
    """

    def __init__(self):
        """Initialize scorer."""
        self._session = None
        self._closed = False

    async def close(self) -> None:
        """Close the database session.

        Spec 037 T1.2 AC-T1.2.2: Commits or rollbacks session on close.
        """
        if self._closed:
            return

        if self._session is not None:
            try:
                await self._session.commit()
            except Exception:
                await self._session.rollback()
            finally:
                await self._session.close()
                self._session = None

        self._closed = True

    async def _get_vice_repo(self) -> "VicePreferenceRepository":
        """Get vice preference repository with session.

        Returns:
            VicePreferenceRepository instance
        """
        from nikita.db.database import get_session_maker
        from nikita.db.repositories.vice_repository import VicePreferenceRepository

        if self._session is None:
            session_maker = get_session_maker()
            self._session = session_maker()

        return VicePreferenceRepository(self._session)

    async def process_signals(
        self,
        user_id: UUID,
        signals: list[ViceSignal],
        chapter: int = 3,
    ) -> dict:
        """Process vice signals to update user intensities.

        AC-T012.1: process_signals(user_id, signals) updates intensities
        AC-T012.2: Intensity = confidence × frequency × recency
        AC-T012.3: Uses VicePreferenceRepository.discover() for new vices
        AC-T012.4: Uses VicePreferenceRepository.update_intensity() for updates
        Spec 106 I13: Chapter-adaptive sensitivity multiplier

        Args:
            user_id: User's UUID
            signals: List of detected ViceSignal objects
            chapter: Current chapter (1-5) for sensitivity scaling

        Returns:
            Dict with processing results
        """
        repo = await self._get_vice_repo()
        results = {"processed": 0, "discovered": 0, "updated": 0}

        # Spec 106 I13: Chapter sensitivity multiplier
        sensitivity = CHAPTER_SENSITIVITY_MULTIPLIERS.get(chapter, Decimal("1.0"))

        for signal in signals:
            # Skip low confidence signals
            if signal.confidence < MIN_CONFIDENCE_THRESHOLD:
                continue

            category = signal.category.value

            # Check if vice exists
            pref = await repo.get_by_category(user_id, category)

            if pref is None:
                # AC-T012.3: Discover new vice
                pref = await repo.discover(
                    user_id,
                    category,
                    initial_intensity=1,
                )
                results["discovered"] += 1

            # Calculate engagement delta with chapter sensitivity
            # Positive signals add, negative signals subtract
            if signal.is_positive:
                delta = signal.confidence * POSITIVE_SIGNAL_MULTIPLIER * sensitivity
            else:
                delta = -signal.confidence * NEGATIVE_SIGNAL_MULTIPLIER * sensitivity

            # AC-T012.4: Update engagement score
            await repo.update_engagement(pref.id, delta)
            results["updated"] += 1
            results["processed"] += 1

        # Commit changes
        if self._session:
            await self._session.commit()

        return results

    async def get_profile(self, user_id: UUID) -> ViceProfile:
        """Get user's complete vice profile.

        AC-T016.1: Returns ViceProfile with all 8 category intensities
        AC-T016.2: Categories without data return intensity 0.0
        AC-T016.3: top_vices ordered by intensity (descending)

        Args:
            user_id: User's UUID

        Returns:
            ViceProfile with all categories
        """
        repo = await self._get_vice_repo()

        # Get all active preferences
        prefs = await repo.get_active(user_id)

        # Build intensities dict for all 8 categories
        intensities: dict[str, Decimal] = {}
        for vc in ViceCategory:
            intensities[vc.value] = Decimal("0.0")

        # Fill in discovered vices
        for pref in prefs:
            # Normalize engagement score to 0-1 intensity
            # engagement_score accumulates, so we need to cap it
            intensity = min(pref.engagement_score / Decimal("5.0"), Decimal("1.0"))
            intensities[pref.category] = intensity

        # Build top_vices list (sorted by intensity descending)
        sorted_vices = sorted(
            intensities.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        top_vices = [cat for cat, intensity in sorted_vices if intensity > Decimal("0")]

        return ViceProfile(
            user_id=user_id,
            intensities=intensities,
            top_vices=top_vices,
            updated_at=datetime.now(timezone.utc),
        )

    async def get_top_vices(
        self,
        user_id: UUID,
        n: int = 3,
        min_threshold: Decimal = Decimal("0.20"),
    ) -> list[tuple[str, Decimal]]:
        """Get top N vices by intensity.

        AC-T017.1: Returns top N vices by intensity (default 3)
        AC-T017.2: Returns (category, intensity) tuples
        AC-T017.3: Filters vices below minimum threshold

        Args:
            user_id: User's UUID
            n: Number of top vices to return
            min_threshold: Minimum intensity to include

        Returns:
            List of (category, intensity) tuples
        """
        profile = await self.get_profile(user_id)

        # Filter and sort
        filtered = [
            (cat, intensity)
            for cat, intensity in profile.intensities.items()
            if intensity >= min_threshold
        ]

        # Sort by intensity descending
        sorted_vices = sorted(filtered, key=lambda x: x[1], reverse=True)

        return sorted_vices[:n]

