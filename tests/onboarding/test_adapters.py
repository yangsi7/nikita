"""Tests for Spec 213 Pydantic↔ORM adapter (FR-3.1).

Validates that `ProfileFromOnboardingProfile.from_pydantic` returns a
`BackstoryPromptProfile` dataclass with DUCK-TYPED attribute names matching
what `BackstoryGeneratorService._build_scenario_prompt` actually reads
(NOT the `UserProfile` ORM column names).

Load-bearing: the generator reads `.city` (NOT `.location_city`) and
`.primary_passion` (NOT `.primary_interest`).
"""

from __future__ import annotations

from dataclasses import is_dataclass
from types import SimpleNamespace
from uuid import uuid4

import pytest

from nikita.onboarding.adapters import BackstoryPromptProfile, ProfileFromOnboardingProfile


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def rich_profile():
    """SimpleNamespace standing in for a UserOnboardingProfile with all fields set."""
    return SimpleNamespace(
        city="Berlin",
        social_scene="techno",
        life_stage="tech",
        interest="underground music",
        darkness_level=4,
        name="Alex",
        age=29,
        occupation="Software Engineer",
    )


@pytest.fixture
def sparse_profile():
    """Profile with only required fields (city + scene + darkness_level + all optionals None)."""
    return SimpleNamespace(
        city="Paris",
        social_scene="art",
        life_stage=None,
        interest=None,
        darkness_level=2,
        name=None,
        age=None,
        occupation=None,
    )


# ---------------------------------------------------------------------------
# BackstoryPromptProfile dataclass shape
# ---------------------------------------------------------------------------


class TestBackstoryPromptProfileDataclass:
    """Confirm the duck-typed shape matches BackstoryGeneratorService reads."""

    def test_is_dataclass(self):
        assert is_dataclass(BackstoryPromptProfile)

    def test_has_city_not_location_city(self):
        """CRITICAL: generator reads profile.city (NOT profile.location_city)."""
        fields = {f.name for f in BackstoryPromptProfile.__dataclass_fields__.values()}
        assert "city" in fields
        assert "location_city" not in fields

    def test_has_primary_passion_not_primary_interest(self):
        """CRITICAL: generator reads profile.primary_passion (NOT profile.primary_interest)."""
        fields = {f.name for f in BackstoryPromptProfile.__dataclass_fields__.values()}
        assert "primary_passion" in fields
        assert "primary_interest" not in fields

    def test_has_drug_tolerance_not_darkness_level(self):
        """Generator legacy field name is drug_tolerance (ORM-adjacent)."""
        fields = {f.name for f in BackstoryPromptProfile.__dataclass_fields__.values()}
        assert "drug_tolerance" in fields

    def test_has_all_required_fields(self):
        """Full attribute inventory per spec FR-3.1 table."""
        fields = {f.name for f in BackstoryPromptProfile.__dataclass_fields__.values()}
        expected = {
            "city",
            "social_scene",
            "life_stage",
            "primary_passion",
            "drug_tolerance",
            "name",
            "age",
            "occupation",
        }
        assert expected.issubset(fields)


# ---------------------------------------------------------------------------
# from_pydantic: field mapping
# ---------------------------------------------------------------------------


class TestFromPydanticFieldMapping:
    """Validates the Pydantic→duck-typed-dataclass mapping per spec FR-3.1 table."""

    def test_city_passes_through(self, rich_profile):
        result = ProfileFromOnboardingProfile.from_pydantic(uuid4(), rich_profile)
        assert result.city == "Berlin"

    def test_social_scene_passes_through(self, rich_profile):
        result = ProfileFromOnboardingProfile.from_pydantic(uuid4(), rich_profile)
        assert result.social_scene == "techno"

    def test_life_stage_passes_through(self, rich_profile):
        result = ProfileFromOnboardingProfile.from_pydantic(uuid4(), rich_profile)
        assert result.life_stage == "tech"

    def test_interest_maps_to_primary_passion(self, rich_profile):
        """NAME-COLLISION mapping: Pydantic.interest → dataclass.primary_passion."""
        result = ProfileFromOnboardingProfile.from_pydantic(uuid4(), rich_profile)
        assert result.primary_passion == "underground music"

    def test_darkness_level_maps_to_drug_tolerance(self, rich_profile):
        """Legacy name mapping: Pydantic.darkness_level → dataclass.drug_tolerance."""
        result = ProfileFromOnboardingProfile.from_pydantic(uuid4(), rich_profile)
        assert result.drug_tolerance == 4

    def test_name_passes_through(self, rich_profile):
        result = ProfileFromOnboardingProfile.from_pydantic(uuid4(), rich_profile)
        assert result.name == "Alex"

    def test_age_passes_through(self, rich_profile):
        result = ProfileFromOnboardingProfile.from_pydantic(uuid4(), rich_profile)
        assert result.age == 29

    def test_occupation_passes_through(self, rich_profile):
        result = ProfileFromOnboardingProfile.from_pydantic(uuid4(), rich_profile)
        assert result.occupation == "Software Engineer"

    def test_returns_dataclass_instance(self, rich_profile):
        result = ProfileFromOnboardingProfile.from_pydantic(uuid4(), rich_profile)
        assert isinstance(result, BackstoryPromptProfile)


class TestFromPydanticNoneFields:
    """Optional fields pass through as None without errors."""

    def test_all_optionals_none(self, sparse_profile):
        result = ProfileFromOnboardingProfile.from_pydantic(uuid4(), sparse_profile)
        assert result.life_stage is None
        assert result.primary_passion is None
        assert result.name is None
        assert result.age is None
        assert result.occupation is None
        # Required fields still populated
        assert result.city == "Paris"
        assert result.social_scene == "art"
        assert result.drug_tolerance == 2


# ---------------------------------------------------------------------------
# Duck-typing compatibility with BackstoryGeneratorService
# ---------------------------------------------------------------------------


class TestDuckTypeCompatibility:
    """Ensure the returned object exposes EXACTLY the attributes the generator reads."""

    def test_not_a_user_profile_orm(self, rich_profile):
        """CRITICAL: result is a dataclass, NOT a UserProfile ORM object.

        UserProfile has `location_city` and `primary_interest` — attempting to
        construct one would require a DB session + SQLAlchemy machinery. The
        adapter deliberately returns a lightweight dataclass instead.
        """
        result = ProfileFromOnboardingProfile.from_pydantic(uuid4(), rich_profile)
        # Confirm it's NOT any SQLAlchemy model
        cls = type(result)
        # No `__tablename__` (SQLAlchemy models have it), no `_sa_instance_state`
        assert not hasattr(cls, "__tablename__")
        assert not hasattr(result, "_sa_instance_state")

    def test_all_generator_reads_succeed(self, rich_profile):
        """Simulate what BackstoryGeneratorService does: attribute access.

        Covers the COMPLETE set of attributes the generator reads on the
        profile passed into ``generate_scenarios``. Missing any of these at
        runtime would raise ``AttributeError`` deep inside the service — the
        adapter must guarantee all reads succeed AND return the expected
        mapped values. Keep this list in sync with
        ``nikita/services/backstory_generator.py``.
        """
        result = ProfileFromOnboardingProfile.from_pydantic(uuid4(), rich_profile)
        # Complete set of reads made inside BackstoryGeneratorService
        # (backstory_generator.py:{180,183,185,220} and related sites). Each
        # assertion pins the VALUE to catch silent field-mapping regressions,
        # not just AttributeError absence.
        assert result.city == "Berlin"
        assert result.primary_passion == "underground music"
        assert result.social_scene == "techno"
        assert result.life_stage == "tech"
        assert result.drug_tolerance == 4
        assert result.name == "Alex"
        assert result.age == 29
        assert result.occupation == "Software Engineer"


# ---------------------------------------------------------------------------
# Forward-compat (name field is net-new per FR-1c; adapter handles absence)
# ---------------------------------------------------------------------------


class TestForwardCompatNameField:
    """Per spec constraints: `name` is net-new in PR 213-2. Adapter must not crash
    on profiles that predate the field (forward-compat with existing Pydantic models)."""

    def test_name_missing_from_profile_yields_none(self):
        """A profile without a `name` attribute produces `name=None`, not AttributeError."""
        profile_no_name = SimpleNamespace(
            city="Tokyo",
            social_scene="nature",
            life_stage=None,
            interest=None,
            darkness_level=1,
            age=None,
            occupation=None,
        )
        # no `name` attribute at all
        result = ProfileFromOnboardingProfile.from_pydantic(uuid4(), profile_no_name)
        assert result.name is None


# ---------------------------------------------------------------------------
# Module isolation guard
# ---------------------------------------------------------------------------


def test_module_isolation_imports():
    """FR-3.1 isolation: adapters.py is a lightweight bridge.

    It MUST NOT import from:
      - nikita.engine.*           (different domain)
      - nikita.db.*               (no persistence — returns plain dataclass)

    The adapter MAY import from ``nikita.onboarding.models`` (the Pydantic
    domain) since it explicitly bridges that surface to the duck-typed
    dataclass. Current implementation uses ``getattr`` + ``object`` typing
    and does not import the Pydantic class — the guard here preserves that
    freedom while still forbidding engine/db coupling.

    Inspects the AST rather than source text (docstring mentions the
    forbidden paths as a negation — 'MUST NOT import' — which would produce
    a false positive on a text-substring match).
    """
    import ast
    import inspect

    from nikita.onboarding import adapters

    forbidden_prefixes = ("nikita.engine", "nikita.db")

    src = inspect.getsource(adapters)
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for prefix in forbidden_prefixes:
                    assert not alias.name.startswith(prefix), (
                        f"adapters.py imports {alias.name} (forbids {prefix}.*)"
                    )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for prefix in forbidden_prefixes:
                assert not module.startswith(prefix), (
                    f"adapters.py imports from {module} (forbids {prefix}.*)"
                )
