"""Spec 218 Slice 218-3 — static city cohort for SingleSelectAsk.

The decorator agent emits SingleSelectAsk for the `city` target with
options drawn from this static list. Cohort selection is deliberately
8-cities-or-fewer (envelope.py SingleSelectAsk.options has max_length=8)
to fit in a single radio-group screen.

PR-218-6 (Phase-2 research_agent) will replace this static list with
firecrawl-driven extraction of the user's top-cohort cities based on
their primary_hobbies + occupation. For Slice 218-3 we keep it static
because: (a) hobbies/occupation are not yet collected when the city slot
fires, (b) the firecrawl cohort extension carries its own LOC budget
that should not bleed into a slot-extension slice.

Tuning constant regression: change to `CITY_OPTIONS` requires updating
``test_decorator_agent_slice3.py::test_cohort_cities_module_exports_options``.
"""

from __future__ import annotations

from typing import Final

from nikita.agents.onboarding.v2.envelope import Option


CITY_OPTIONS: Final[list[Option]] = [
    Option(value="berlin", label="Berlin"),
    Option(value="nyc", label="New York"),
    Option(value="sf", label="San Francisco"),
    Option(value="la", label="Los Angeles"),
    Option(value="london", label="London"),
    Option(value="paris", label="Paris"),
    Option(value="amsterdam", label="Amsterdam"),
    Option(value="tokyo", label="Tokyo"),
]
"""Static cohort cities for Slice 218-3 city SingleSelectAsk.

Current value: 8 cities (Slice 218-3 lock-in 2026-05-12).
Prior values: none (new in PR-218-3).
Rationale: 8 is the envelope max for SingleSelectAsk.options; covers the
top user cohort by current dogfood walks. Firecrawl extension (slice
218-6) supersedes.
"""


__all__ = ["CITY_OPTIONS"]
