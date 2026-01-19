"""Layer 5: Context Injection (Spec 021, T014).

Injects pre-computed context from ContextPackage into the prompt.
This layer provides:
- User facts (knowledge about the user)
- Relationship events (milestones, conflicts, resolutions)
- Active conversation threads (unresolved topics)
- Summaries (today, this week)
- Nikita's life events (what happened in her day)

Token budget: ~500 tokens
"""

import logging
from typing import Any

from nikita.context.package import ContextPackage

logger = logging.getLogger(__name__)


# Limits for each content type to stay within token budget
MAX_USER_FACTS = 10
MAX_RELATIONSHIP_EVENTS = 5
MAX_ACTIVE_THREADS = 5
MAX_WEEK_SUMMARIES = 3
MAX_LIFE_EVENTS = 3


class Layer5Injector:
    """Injector for Layer 5: Context from pre-computed package.

    Takes a ContextPackage and formats its contents into a prompt
    section that provides Nikita with relevant context about:
    - What she knows about the user
    - Recent relationship events
    - Open conversation threads
    - Summaries of past conversations
    - Her own life events

    Attributes:
        _max_user_facts: Maximum user facts to include.
        _max_relationship_events: Maximum relationship events.
        _max_active_threads: Maximum active threads.
        _max_week_summaries: Maximum week summaries.
        _max_life_events: Maximum life events.
    """

    def __init__(
        self,
        max_user_facts: int = MAX_USER_FACTS,
        max_relationship_events: int = MAX_RELATIONSHIP_EVENTS,
        max_active_threads: int = MAX_ACTIVE_THREADS,
        max_week_summaries: int = MAX_WEEK_SUMMARIES,
        max_life_events: int = MAX_LIFE_EVENTS,
    ) -> None:
        """Initialize Layer5Injector.

        Args:
            max_user_facts: Maximum number of user facts to include.
            max_relationship_events: Maximum relationship events.
            max_active_threads: Maximum active threads.
            max_week_summaries: Maximum week summaries.
            max_life_events: Maximum life events.
        """
        self._max_user_facts = max_user_facts
        self._max_relationship_events = max_relationship_events
        self._max_active_threads = max_active_threads
        self._max_week_summaries = max_week_summaries
        self._max_life_events = max_life_events

    def inject(self, package: ContextPackage | None) -> str | None:
        """Inject context from package into prompt.

        Args:
            package: Pre-computed context package, or None.

        Returns:
            Formatted context prompt section, or None if no package
            or package has no meaningful content.
        """
        if package is None:
            return None

        sections: list[str] = []

        # User facts
        if package.user_facts:
            facts_section = self._format_user_facts(package.user_facts)
            if facts_section:
                sections.append(facts_section)

        # Active threads
        if package.active_threads:
            threads_section = self._format_active_threads(package.active_threads)
            if threads_section:
                sections.append(threads_section)

        # Relationship events
        if package.relationship_events:
            events_section = self._format_relationship_events(package.relationship_events)
            if events_section:
                sections.append(events_section)

        # Today's summary
        if package.today_summary:
            sections.append(f"**Earlier today**: {package.today_summary}")

        # Week summaries
        if package.week_summaries:
            week_section = self._format_week_summaries(package.week_summaries)
            if week_section:
                sections.append(week_section)

        # Nikita's life events
        if package.life_events_today:
            life_section = self._format_life_events(package.life_events_today)
            if life_section:
                sections.append(life_section)

        if not sections:
            return None

        # Combine with header
        header = "## Context from Memory"
        return header + "\n\n" + "\n\n".join(sections)

    def _format_user_facts(self, facts: list[str]) -> str | None:
        """Format user facts section.

        Args:
            facts: List of user facts.

        Returns:
            Formatted section or None if empty.
        """
        if not facts:
            return None

        limited = facts[: self._max_user_facts]
        formatted = "\n".join(f"- {fact}" for fact in limited)
        return f"**What you know about them**:\n{formatted}"

    def _format_active_threads(self, threads: list[Any]) -> str | None:
        """Format active threads section.

        Args:
            threads: List of ActiveThread objects.

        Returns:
            Formatted section or None if empty.
        """
        if not threads:
            return None

        # Filter to open threads and limit
        open_threads = [t for t in threads if t.status != "resolved"]
        limited = open_threads[: self._max_active_threads]

        if not limited:
            return None

        formatted_items = []
        for thread in limited:
            if thread.status == "open":
                formatted_items.append(f"- {thread.topic}")
            else:
                formatted_items.append(f"- {thread.topic} ({thread.status})")

        formatted = "\n".join(formatted_items)
        return f"**Open conversation threads**:\n{formatted}"

    def _format_relationship_events(self, events: list[str]) -> str | None:
        """Format relationship events section.

        Args:
            events: List of relationship events.

        Returns:
            Formatted section or None if empty.
        """
        if not events:
            return None

        limited = events[: self._max_relationship_events]
        formatted = "\n".join(f"- {event}" for event in limited)
        return f"**Recent relationship moments**:\n{formatted}"

    def _format_week_summaries(self, summaries: list[str]) -> str | None:
        """Format week summaries section.

        Args:
            summaries: List of week summaries.

        Returns:
            Formatted section or None if empty.
        """
        if not summaries:
            return None

        limited = summaries[: self._max_week_summaries]
        formatted = "; ".join(limited)
        return f"**This week**: {formatted}"

    def _format_life_events(self, events: list[str]) -> str | None:
        """Format Nikita's life events section.

        Args:
            events: List of life events.

        Returns:
            Formatted section or None if empty.
        """
        if not events:
            return None

        limited = events[: self._max_life_events]
        formatted = "\n".join(f"- {event}" for event in limited)
        return f"**Your day so far**:\n{formatted}"

    @property
    def token_estimate(self) -> int:
        """Estimate token count for context injection layer.

        Returns:
            Target token budget (500).
        """
        return 500


# Module-level singleton for efficiency
_default_injector: Layer5Injector | None = None


def get_layer5_injector() -> Layer5Injector:
    """Get the singleton Layer5Injector instance.

    Returns:
        Cached Layer5Injector instance.
    """
    global _default_injector
    if _default_injector is None:
        _default_injector = Layer5Injector()
    return _default_injector


def inject_context(package: ContextPackage | None) -> str | None:
    """Convenience function to inject context from package.

    Args:
        package: Pre-computed context package, or None.

    Returns:
        Formatted context prompt section.
    """
    return get_layer5_injector().inject(package)
