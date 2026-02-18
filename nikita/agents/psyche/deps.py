"""Dependency container for Psyche Agent (Spec 056 T6).

Provides input context for psyche state generation including
recent score history, emotional states, life events, and NPC interactions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID


@dataclass
class PsycheDeps:
    """Dependency container for the psyche agent.

    Contains all context needed for psyche state generation:
    - user_id: Target user
    - score_history: Last 48h of score changes
    - emotional_states: Recent emotional state snapshots
    - life_events: Recent life simulation events
    - npc_interactions: Recent NPC interaction summaries
    - current_chapter: User's current game chapter (1-5)
    - message: Optional triggering message (for Tier 2/3 analysis)
    """

    user_id: UUID
    score_history: list[dict] = field(default_factory=list)
    emotional_states: list[dict] = field(default_factory=list)
    life_events: list[dict] = field(default_factory=list)
    npc_interactions: list[dict] = field(default_factory=list)
    current_chapter: int = 1
    message: str | None = None
