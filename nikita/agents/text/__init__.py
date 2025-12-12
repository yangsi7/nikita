"""Nikita text agent - Pydantic AI powered conversational agent."""

from typing import TYPE_CHECKING
from uuid import UUID

from pydantic_ai import Agent

from nikita.agents.text.deps import NikitaDeps
from nikita.agents.text.agent import get_nikita_agent, build_system_prompt, generate_response
from nikita.config.settings import get_settings

if TYPE_CHECKING:
    from nikita.db.models.user import User
    from nikita.memory.graphiti_client import NikitaMemory


# Lazy import for memory client to avoid import errors during testing
async def get_memory_client(user_id: str) -> "NikitaMemory":
    """Lazy wrapper for get_memory_client to avoid import-time errors."""
    from nikita.memory.graphiti_client import get_memory_client as _get_memory_client
    return await _get_memory_client(user_id)


class UserNotFoundError(Exception):
    """Raised when a user is not found in the database."""

    def __init__(self, user_id: UUID):
        self.user_id = user_id
        super().__init__(f"User not found: {user_id}")


async def get_user_by_id(user_id: UUID) -> "User | None":
    """
    Get a user by their ID from the database.

    Uses the session maker to create a database session and fetches
    the user via UserRepository.

    Args:
        user_id: UUID of the user to fetch

    Returns:
        User model or None if not found
    """
    from nikita.db.database import get_session_maker
    from nikita.db.repositories.user_repository import UserRepository

    session_maker = get_session_maker()
    async with session_maker() as session:
        repo = UserRepository(session)
        return await repo.get(user_id)


async def get_nikita_agent_for_user(user_id: UUID) -> tuple[Agent[NikitaDeps, str], NikitaDeps]:
    """
    Factory function to get a configured Nikita agent for a specific user.

    Creates the agent singleton and builds NikitaDeps with the user's
    memory system, database record, and application settings.

    Args:
        user_id: UUID of the user to create agent for

    Returns:
        Tuple of (Agent, NikitaDeps) ready for conversation

    Raises:
        UserNotFoundError: If user doesn't exist in database
    """
    # Load user from database
    user = await get_user_by_id(user_id)
    if user is None:
        raise UserNotFoundError(user_id)

    # Initialize memory system for this user
    memory = await get_memory_client(str(user_id))

    # Get application settings
    settings = get_settings()

    # Build dependencies
    deps = NikitaDeps(
        memory=memory,
        user=user,
        settings=settings,
    )

    # Get the agent singleton
    agent = get_nikita_agent()

    return agent, deps


__all__ = [
    "NikitaDeps",
    "UserNotFoundError",
    "get_nikita_agent",
    "get_nikita_agent_for_user",
    "get_user_by_id",
    "get_memory_client",
    "get_settings",
    "build_system_prompt",
    "generate_response",
]
