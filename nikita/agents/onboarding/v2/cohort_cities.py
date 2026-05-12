"""Spec 218 Slice 218-3/218-4 — static cohort options for city, hobby, and hangout chips.

City cohort: used by SingleSelectAsk for the `city` target.
Hobby cohort: used by ChipMultiAsk for the `primary_hobbies` target.
Hangout cohort: used by ChipMultiAsk for the `hangouts_personalized` target.

PR-218-6 (Phase-2 research_agent) will replace these static lists with
firecrawl-driven extraction based on the user's primary_hobbies + occupation
+ city. For Slice 218-4 we keep them static because:
(a) hobbies/hangouts are not yet collected when the city slot fires,
(b) the firecrawl cohort extension carries its own LOC budget that should
    not bleed into a slot-extension slice.

Tuning constant regressions:
- Change to ``CITY_OPTIONS`` requires updating
  ``test_decorator_agent_slice3.py::test_cohort_cities_module_exports_options``.
- Change to ``HOBBY_OPTIONS`` requires updating
  ``test_decorator_agent_slice4.py::test_hobby_options_exported_with_reasonable_count``.
- Change to ``HANGOUT_OPTIONS`` requires updating
  ``test_decorator_agent_slice4.py::test_hangout_options_exported_with_reasonable_count``.
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


HOBBY_OPTIONS: Final[list[Option]] = [
    Option(value="music", label="Music"),
    Option(value="sports", label="Sports"),
    Option(value="travel", label="Travel"),
    Option(value="gaming", label="Gaming"),
    Option(value="cooking", label="Cooking"),
    Option(value="reading", label="Reading"),
    Option(value="art", label="Art & Design"),
    Option(value="outdoors", label="Outdoors"),
]
"""Static hobby cohort for Slice 218-4 primary_hobbies ChipMultiAsk.

Current value: 8 hobbies (Slice 218-4 lock-in 2026-05-12).
Prior values: none (new in PR-218-4).
Rationale: 8 covers the dominant dogfood-walk hobby mentions; small enough
to fit comfortably on one chip-row screen. Firecrawl extension (slice 218-6)
supersedes with personalised hobby suggestions derived from occupation + city.
"""


HANGOUT_OPTIONS: Final[list[Option]] = [
    Option(value="bars", label="Bars & Cocktail Lounges"),
    Option(value="live_music", label="Live Music Venues"),
    Option(value="restaurants", label="Restaurants & Food Markets"),
    Option(value="parks", label="Parks & Outdoor Spaces"),
    Option(value="gyms", label="Gyms & Fitness Studios"),
    Option(value="coffee_shops", label="Coffee Shops"),
    Option(value="galleries", label="Galleries & Museums"),
    Option(value="clubs", label="Clubs & Late-Night Spots"),
]
"""Static hangout cohort for Slice 218-4 hangouts_personalized ChipMultiAsk.

Current value: 8 hangout venue types (Slice 218-4 lock-in 2026-05-12).
Prior values: none (new in PR-218-4).
Rationale: generic venue types that work across all cohort cities; matches
the city-agnostic slice-218-4 constraint (firecrawl city-specific extension
in slice 218-6 personalises this per city).
"""


__all__ = ["CITY_OPTIONS", "HANGOUT_OPTIONS", "HOBBY_OPTIONS"]
