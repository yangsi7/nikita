"""Narrative Arc Manager for Life Simulation Engine (Spec 022, T011).

Manages multi-day narrative arcs (project deadlines, friend drama, etc.).

AC-T011.1: NarrativeArcManager class
AC-T011.2: create_arc() starts new narrative arc
AC-T011.3: progress_arc() advances arc state
AC-T011.4: resolve_arc() ends arc
AC-T011.5: Probabilistic resolution (70/20/10)
AC-T011.6: Unit tests for arc lifecycle
"""

import logging
import random
from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from nikita.life_simulation.models import (
    NarrativeArc,
    ArcStatus,
    EventDomain,
)
from nikita.life_simulation.store import EventStore, get_event_store

logger = logging.getLogger(__name__)


# Arc type definitions with typical outcomes
ARC_TYPES: dict[str, dict[str, Any]] = {
    # Work arcs
    "project_deadline": {
        "domain": EventDomain.WORK,
        "typical_duration_days": 14,
        "outcomes": ["completed_successfully", "missed_deadline", "scope_changed"],
        "outcome_weights": [0.7, 0.2, 0.1],  # 70% success, 20% miss, 10% change
    },
    "work_conflict": {
        "domain": EventDomain.WORK,
        "typical_duration_days": 7,
        "outcomes": ["resolved_positively", "unresolved", "escalated"],
        "outcome_weights": [0.6, 0.3, 0.1],
    },
    "promotion_opportunity": {
        "domain": EventDomain.WORK,
        "typical_duration_days": 21,
        "outcomes": ["got_promotion", "passed_over", "withdrew_application"],
        "outcome_weights": [0.5, 0.4, 0.1],
    },
    # Social arcs
    "friend_crisis": {
        "domain": EventDomain.SOCIAL,
        "typical_duration_days": 10,
        "outcomes": ["friend_recovered", "ongoing_support", "friendship_strained"],
        "outcome_weights": [0.6, 0.3, 0.1],
    },
    "dating_interest": {
        "domain": EventDomain.SOCIAL,
        "typical_duration_days": 14,
        "outcomes": ["became_official", "fizzled_out", "still_talking"],
        "outcome_weights": [0.3, 0.4, 0.3],
    },
    "family_visit": {
        "domain": EventDomain.SOCIAL,
        "typical_duration_days": 5,
        "outcomes": ["went_well", "drama_happened", "visit_cancelled"],
        "outcome_weights": [0.6, 0.3, 0.1],
    },
    # Personal arcs
    "health_goal": {
        "domain": EventDomain.PERSONAL,
        "typical_duration_days": 30,
        "outcomes": ["goal_achieved", "still_working", "gave_up"],
        "outcome_weights": [0.4, 0.4, 0.2],
    },
    "home_project": {
        "domain": EventDomain.PERSONAL,
        "typical_duration_days": 14,
        "outcomes": ["completed", "in_progress", "abandoned"],
        "outcome_weights": [0.5, 0.3, 0.2],
    },
    "personal_growth": {
        "domain": EventDomain.PERSONAL,
        "typical_duration_days": 21,
        "outcomes": ["breakthrough", "gradual_progress", "setback"],
        "outcome_weights": [0.3, 0.5, 0.2],
    },
}


class ArcProgressUpdate(BaseModel):
    """Schema for arc progress updates."""

    new_state: str = Field(description="Updated current state description")
    is_resolved: bool = Field(default=False, description="Whether the arc should be resolved")
    outcome: str | None = Field(default=None, description="Resolution outcome if resolved")


class NarrativeArcManager:
    """Manages narrative arcs for Nikita's life story.

    Narrative arcs are multi-day story threads that give continuity
    and stakes to Nikita's life. Examples:
    - Work deadline approaching
    - Friend going through breakup
    - Personal fitness goal

    Arcs have three phases:
    1. Creation (start_arc) - new arc begins
    2. Progression (progress_arc) - state updates over days
    3. Resolution (resolve_arc) - arc ends with outcome

    Example:
        manager = NarrativeArcManager()
        arc = await manager.create_arc(
            user_id, "project_deadline", ["the redesign"]
        )
        # Later...
        await manager.progress_arc(arc.arc_id, "Lisa extended the deadline")
        # Eventually...
        await manager.resolve_arc(arc.arc_id, "completed_successfully")
    """

    def __init__(self, store: EventStore | None = None) -> None:
        """Initialize NarrativeArcManager.

        Args:
            store: Optional EventStore. Defaults to singleton.
        """
        self._store = store or get_event_store()

    async def create_arc(
        self,
        user_id: UUID,
        arc_type: str,
        entities: list[str] | None = None,
        initial_state: str | None = None,
    ) -> NarrativeArc:
        """Create a new narrative arc.

        Args:
            user_id: User ID.
            arc_type: Type of arc (e.g., "project_deadline", "friend_crisis").
            entities: Entities involved (people, projects, places).
            initial_state: Initial state description. Auto-generated if not provided.

        Returns:
            Created NarrativeArc.
        """
        arc_config = ARC_TYPES.get(arc_type, {})
        domain = arc_config.get("domain", EventDomain.PERSONAL)

        # Generate initial state if not provided
        if not initial_state:
            initial_state = self._generate_initial_state(arc_type, entities or [])

        # Generate possible outcomes
        possible_outcomes = arc_config.get("outcomes", ["resolved", "ongoing", "abandoned"])

        arc = NarrativeArc(
            user_id=user_id,
            domain=domain,
            arc_type=arc_type,
            start_date=date.today(),
            entities=entities or [],
            current_state=initial_state,
            possible_outcomes=possible_outcomes,
        )

        await self._store.save_arc(arc)
        logger.info(f"Created arc {arc.arc_id}: {arc_type} for user {user_id}")

        return arc

    async def progress_arc(
        self,
        arc_id: UUID,
        new_state: str,
    ) -> bool:
        """Progress an arc's state.

        Updates the current state without resolving the arc.

        Args:
            arc_id: Arc ID.
            new_state: New state description.

        Returns:
            True if updated successfully.
        """
        success = await self._store.update_arc_state(arc_id, new_state)
        if success:
            logger.info(f"Progressed arc {arc_id}: {new_state[:50]}...")
        return success

    async def resolve_arc(
        self,
        arc_id: UUID,
        outcome: str,
        final_state: str | None = None,
    ) -> bool:
        """Resolve a narrative arc.

        Ends the arc with a specific outcome.

        Args:
            arc_id: Arc ID.
            outcome: Resolution outcome (e.g., "completed_successfully").
            final_state: Optional final state description.

        Returns:
            True if resolved successfully.
        """
        # Update state if provided
        if final_state:
            await self._store.update_arc_state(arc_id, final_state)

        # Update status to resolved
        success = await self._store.update_arc_status(
            arc_id,
            ArcStatus.RESOLVED,
            resolved_at=datetime.now(timezone.utc),
        )

        if success:
            logger.info(f"Resolved arc {arc_id} with outcome: {outcome}")

        return success

    async def get_active_arcs(self, user_id: UUID) -> list[NarrativeArc]:
        """Get all active arcs for a user.

        Args:
            user_id: User ID.

        Returns:
            List of active narrative arcs.
        """
        return await self._store.get_active_arcs(user_id)

    async def check_arc_resolution(
        self, arc: NarrativeArc, days_active: int | None = None
    ) -> tuple[bool, str | None]:
        """Check if an arc should be resolved.

        Uses probabilistic resolution based on arc type and duration.

        Args:
            arc: The narrative arc to check.
            days_active: Override for days since arc started.

        Returns:
            Tuple of (should_resolve, outcome if resolving).
        """
        arc_config = ARC_TYPES.get(arc.arc_type, {})
        typical_duration = arc_config.get("typical_duration_days", 14)

        if days_active is None:
            days_active = (date.today() - arc.start_date).days

        # Probability of resolution increases with time
        # At typical_duration, 50% chance; at 2x typical, 90% chance
        resolution_probability = min(0.9, days_active / (typical_duration * 2))

        # Roll for resolution
        if random.random() < resolution_probability:
            # Select outcome based on weights
            outcomes = arc_config.get("outcomes", ["resolved"])
            weights = arc_config.get("outcome_weights", [1.0])

            # Normalize weights
            if len(weights) != len(outcomes):
                weights = [1.0 / len(outcomes)] * len(outcomes)

            outcome = random.choices(outcomes, weights=weights)[0]
            return True, outcome

        return False, None

    async def maybe_resolve_arcs(self, user_id: UUID) -> list[tuple[NarrativeArc, str]]:
        """Check all active arcs for potential resolution.

        Args:
            user_id: User ID.

        Returns:
            List of (arc, outcome) tuples for arcs that were resolved.
        """
        arcs = await self.get_active_arcs(user_id)
        resolved = []

        for arc in arcs:
            should_resolve, outcome = await self.check_arc_resolution(arc)
            if should_resolve and outcome:
                await self.resolve_arc(arc.arc_id, outcome)
                resolved.append((arc, outcome))

        return resolved

    async def maybe_create_arc(
        self,
        user_id: UUID,
        domain: EventDomain | None = None,
    ) -> NarrativeArc | None:
        """Potentially create a new arc if conditions are right.

        Checks if user has room for a new arc and randomly decides.

        Args:
            user_id: User ID.
            domain: Optional domain to create arc for.

        Returns:
            Created arc if one was made, None otherwise.
        """
        # Check current active arcs
        active_arcs = await self.get_active_arcs(user_id)

        # Limit to 3 active arcs per user
        if len(active_arcs) >= 3:
            return None

        # 20% chance of creating a new arc on any given day
        if random.random() > 0.2:
            return None

        # Select arc type (filter by domain if specified)
        available_types = list(ARC_TYPES.keys())
        if domain:
            available_types = [
                t for t, config in ARC_TYPES.items()
                if config.get("domain") == domain
            ]

        if not available_types:
            return None

        arc_type = random.choice(available_types)

        # Create the arc with generic entities (will be personalized later)
        arc = await self.create_arc(user_id, arc_type)
        return arc

    def _generate_initial_state(self, arc_type: str, entities: list[str]) -> str:
        """Generate initial state description for an arc.

        Args:
            arc_type: Type of arc.
            entities: Involved entities.

        Returns:
            Initial state string.
        """
        entity_str = ", ".join(entities) if entities else "related people"

        initial_states = {
            "project_deadline": f"The deadline is approaching. Involves: {entity_str}",
            "work_conflict": f"Tension is building at work with {entity_str}",
            "promotion_opportunity": "There's a potential promotion on the horizon",
            "friend_crisis": f"{entities[0] if entities else 'A friend'} is going through a tough time",
            "dating_interest": "There might be something developing with someone new",
            "family_visit": "Family is planning to visit soon",
            "health_goal": "Started a new health goal this week",
            "home_project": "Started working on a home project",
            "personal_growth": "Reflecting on personal growth and direction",
        }

        return initial_states.get(arc_type, f"Something is developing with {entity_str}")


# Module-level singleton
_default_manager: NarrativeArcManager | None = None


def get_narrative_manager() -> NarrativeArcManager:
    """Get the singleton NarrativeArcManager instance.

    Returns:
        Cached NarrativeArcManager instance.
    """
    global _default_manager
    if _default_manager is None:
        _default_manager = NarrativeArcManager()
    return _default_manager
