"""Wizard agentic tools package (Spec 216-E).

Two surfaces:

- ``firecrawl_tools`` — 4 application-side ``@agent.tool`` decorators that
  fetch live signal via firecrawl with a 3s per-attempt timeout, cohort
  cache lookup, per-turn budget guard, and graceful static-fallback
  degradation.

- ``web_search`` — a ``prepared_web_search`` callable returning an
  Anthropic-native ``WebSearchTool`` builtin, scoped by the user's city
  + country once ``state.city`` is collected.
"""

from nikita.agents.onboarding.tools.firecrawl_tools import (
    fetch_city_context,
    fetch_occupation_signal,
    fetch_time_of_day_signal,
    fetch_topic_specific,
)
from nikita.agents.onboarding.tools.web_search import (
    detect_country,
    prepared_web_search,
)

__all__ = [
    "detect_country",
    "fetch_city_context",
    "fetch_occupation_signal",
    "fetch_time_of_day_signal",
    "fetch_topic_specific",
    "prepared_web_search",
]
