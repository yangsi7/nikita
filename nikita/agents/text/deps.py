"""Dependency container for NikitaTextAgent.

This module defines the NikitaDeps dataclass used by Pydantic AI
for dependency injection into the agent and its tools.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nikita.config.settings import Settings
    from nikita.db.models.user import User
    from nikita.memory.graphiti_client import NikitaMemory


@dataclass
class NikitaDeps:
    """
    Dependency container for Nikita text agent.

    Contains all dependencies needed by the agent and its tools:
    - memory: NikitaMemory instance for knowledge graph access (optional)
    - user: User model with game state
    - settings: Application settings
    - generated_prompt: Personalized system prompt (injected before agent run)

    Attributes:
        memory: Graphiti-based memory system for the user (None if Neo4j unavailable)
        user: Database user model with current game state
        settings: Application configuration settings
        generated_prompt: Dynamic personalized prompt from MetaPromptService (None = use static)
    """

    memory: "NikitaMemory | None"
    user: "User"
    settings: "Settings"
    generated_prompt: str | None = None  # Personalized prompt from MetaPromptService

    @property
    def chapter(self) -> int:
        """
        Get the user's current chapter.

        Returns:
            Current chapter number (1-5)
        """
        return self.user.chapter
