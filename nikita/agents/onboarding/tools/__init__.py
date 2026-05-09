"""Wizard agentic tools package (Spec 216-E).

Single surface:

- ``firecrawl_tools`` — 4 application-side ``@agent.tool`` decorators that
  fetch live signal via firecrawl with a 3s per-attempt timeout, cohort
  cache lookup, per-turn budget guard, and graceful static-fallback
  degradation.

WebSearchTool builtin removed in Spec 218 PR-218-PREREQ-A — firecrawl-only
architecture going forward (per Spec 218 brief §23.2).
"""

from nikita.agents.onboarding.tools.firecrawl_tools import (
    fetch_city_context,
    fetch_occupation_signal,
    fetch_time_of_day_signal,
    fetch_topic_specific,
)

__all__ = [
    "fetch_city_context",
    "fetch_occupation_signal",
    "fetch_time_of_day_signal",
    "fetch_topic_specific",
]
