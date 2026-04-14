"""Pydantic↔ORM adapters for Spec 213 onboarding backend (FR-3.1).

Promoted from the Telegram-specific `_ProfileFromAnswers` at
`nikita/platforms/telegram/onboarding/handler.py:41-56` to a shared module.
Used by BOTH the Telegram onboarding path AND the portal facade
(`nikita/services/portal_onboarding.py`) to bridge the Pydantic-validated
`UserOnboardingProfile` onto the duck-typed shape that
`BackstoryGeneratorService.generate_scenarios` expects.

CRITICAL — DUCK TYPING (load-bearing per Architecture validator iter-3):
  `BackstoryGeneratorService._build_scenario_prompt` at
  `nikita/services/backstory_generator.py:{180,183,220}` accesses:
    - `profile.city`            (NOT `profile.location_city`)
    - `profile.primary_passion` (NOT `profile.primary_interest`)
    - `profile.drug_tolerance`  (NOT `profile.darkness_level`)

  These attribute names do NOT match the `UserProfile` ORM column names.
  The adapter therefore returns a lightweight dataclass, NOT a real ORM row.

  Constructing a real `UserProfile` would fail because the ORM columns
  (`location_city`, `primary_interest`) do not match the generator's reads.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass
class BackstoryPromptProfile:
    """Duck-typed adapter matching attribute names BackstoryGeneratorService reads.

    NOT a real UserProfile ORM object. Required attributes:
      city, social_scene, life_stage, primary_passion, drug_tolerance, name,
      age, occupation.

    Field-mapping table (canonical per spec FR-3.1):
      UserOnboardingProfile (Pydantic)  →  BackstoryPromptProfile (duck-typed)
      -------------------------------------  -----------------------------------
      city                                   city
      social_scene                           social_scene
      life_stage                             life_stage
      interest                               primary_passion   (name collision)
      darkness_level                         drug_tolerance    (legacy name)
      name                                   name
      age                                    age
      occupation                             occupation
    """

    city: str | None
    social_scene: str | None
    life_stage: str | None
    primary_passion: str | None  # mapped from profile.interest
    # Spec FR-3.1 declares this non-nullable (`drug_tolerance: int`). The
    # ``BackstoryGeneratorService`` reads the field without a None-guard, so
    # upstream callers must ensure a concrete value. ``from_pydantic`` enforces
    # this with an ``or 3`` guard on missing/None inputs.
    drug_tolerance: int
    name: str | None
    age: int | None
    occupation: str | None


class ProfileFromOnboardingProfile:
    """Bridges `UserOnboardingProfile` (Pydantic) → duck-typed `BackstoryPromptProfile`.

    The `BackstoryGeneratorService.generate_scenarios(profile, venues)` signature
    accepts any object with the required attributes (duck typing). DO NOT try to
    construct a real `UserProfile` — its columns do not match the reads.

    Both Telegram (`handler.py`) and portal (`portal_onboarding.py`) paths
    import from THIS module. Keeping a single adapter prevents the two paths
    from drifting into two unsynchronized implementations.
    """

    @staticmethod
    def from_pydantic(user_id: UUID, profile: object) -> BackstoryPromptProfile:
        """Convert a `UserOnboardingProfile`-shaped object into a prompt-ready dataclass.

        Uses ``getattr(profile, attr, None)`` for optional/net-new fields so the
        adapter stays forward-compatible with Pydantic models that do not yet
        carry every attribute (e.g., ``name`` is introduced in PR 213-2, while
        this adapter ships in PR 213-1).

        Args:
          user_id: User UUID. Not currently used by the generator but retained
            in the signature for future observability (e.g., per-user prompt
            trace IDs).
          profile: A `UserOnboardingProfile` Pydantic model (typed loosely as
            `object` because the method accesses fields via ``getattr`` — duck
            typing. Test suites pass ``SimpleNamespace`` stand-ins; production
            passes real Pydantic instances. Typing as `object` keeps that
            flexibility explicit and avoids a hard import of the Pydantic class
            from this adapter module).

        Returns:
          A `BackstoryPromptProfile` dataclass ready to pass to
          `BackstoryGeneratorService.generate_scenarios`.
        """
        # Spec FR-3.1 requires drug_tolerance to be a concrete int. The
        # Pydantic UserOnboardingProfile validates darkness_level as
        # non-null with default=3, so ``darkness_level`` is always int
        # in production. The None-coalesce below covers duck-typed test
        # stubs (SimpleNamespace) that omit the attribute or explicitly
        # pass None. Use explicit ``is None`` check (NOT ``or``) so a
        # legitimate ``darkness_level=0`` is preserved rather than
        # silently coerced to 3 (falsy-zero footgun).
        darkness = getattr(profile, "darkness_level", None)
        return BackstoryPromptProfile(
            city=getattr(profile, "city", None),
            social_scene=getattr(profile, "social_scene", None),
            life_stage=getattr(profile, "life_stage", None),
            primary_passion=getattr(profile, "interest", None),  # name-collision
            drug_tolerance=darkness if darkness is not None else 3,
            name=getattr(profile, "name", None),  # net-new in PR 213-2
            age=getattr(profile, "age", None),
            occupation=getattr(profile, "occupation", None),
        )
