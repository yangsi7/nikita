"""TDD: Walk #117 - turn-1 personalization via _build_system_prompt_legacy.

Root cause: new users hit _build_system_prompt_legacy (no ready_prompts row).
Legacy path was missing UserProfile injection. Nikita replied "hey :)" with no
personalization despite 6 seeded memory facts and a full user profile.

These tests MUST FAIL before the fix and PASS after.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from nikita.agents.text.agent import _build_system_prompt_legacy


class TestLegacyPromptProfileInjection:
    """Turn-1 legacy path injects UserProfile fields into system prompt."""

    def _make_profile(self, **kwargs):
        """Build a mock UserProfile with controllable field values."""
        profile = MagicMock()
        profile.name = kwargs.get("name", "Alice")
        profile.age = kwargs.get("age", 27)
        profile.location_city = kwargs.get("location_city", "Paris")
        profile.occupation = kwargs.get("occupation", "designer")
        profile.primary_interest = kwargs.get("primary_interest", "film")
        return profile

    def _make_user(self, chapter=1, profile=None):
        user = MagicMock()
        user.chapter = chapter
        user.id = "4c8b9114-0000-0000-0000-000000000001"
        return user

    @pytest.mark.asyncio
    async def test_profile_name_in_legacy_prompt(self):
        """User's name surfaces in legacy-path prompt."""
        memory = MagicMock()
        memory.get_context_for_prompt = AsyncMock(return_value="User's name is Alice")
        user = self._make_user()
        profile = self._make_profile(name="Alice")

        with patch(
            "nikita.agents.text.agent._load_user_profile_for_legacy",
            new=AsyncMock(return_value=profile),
        ):
            prompt = await _build_system_prompt_legacy(memory, user, "hey nikita")

        assert "Alice" in prompt, "User name must appear in legacy prompt"

    @pytest.mark.asyncio
    async def test_profile_age_in_legacy_prompt(self):
        """User's age surfaces in legacy-path prompt."""
        memory = MagicMock()
        memory.get_context_for_prompt = AsyncMock(return_value="")
        user = self._make_user()
        profile = self._make_profile(age=27)

        with patch(
            "nikita.agents.text.agent._load_user_profile_for_legacy",
            new=AsyncMock(return_value=profile),
        ):
            prompt = await _build_system_prompt_legacy(memory, user, "hey")

        assert "27" in prompt, "User age must appear in legacy prompt"

    @pytest.mark.asyncio
    async def test_profile_city_in_legacy_prompt(self):
        """User's city surfaces in legacy-path prompt."""
        memory = MagicMock()
        memory.get_context_for_prompt = AsyncMock(return_value="User lives in Paris")
        user = self._make_user()
        profile = self._make_profile(location_city="Paris")

        with patch(
            "nikita.agents.text.agent._load_user_profile_for_legacy",
            new=AsyncMock(return_value=profile),
        ):
            prompt = await _build_system_prompt_legacy(memory, user, "hey")

        assert "Paris" in prompt, "User city must appear in legacy prompt"

    @pytest.mark.asyncio
    async def test_profile_occupation_in_legacy_prompt(self):
        """User's occupation surfaces in legacy-path prompt."""
        memory = MagicMock()
        memory.get_context_for_prompt = AsyncMock(return_value="")
        user = self._make_user()
        profile = self._make_profile(occupation="designer")

        with patch(
            "nikita.agents.text.agent._load_user_profile_for_legacy",
            new=AsyncMock(return_value=profile),
        ):
            prompt = await _build_system_prompt_legacy(memory, user, "hey")

        assert "designer" in prompt, "User occupation must appear in legacy prompt"

    @pytest.mark.asyncio
    async def test_profile_interest_in_legacy_prompt(self):
        """User's primary interest surfaces in legacy-path prompt."""
        memory = MagicMock()
        memory.get_context_for_prompt = AsyncMock(return_value="")
        user = self._make_user()
        profile = self._make_profile(primary_interest="film")

        with patch(
            "nikita.agents.text.agent._load_user_profile_for_legacy",
            new=AsyncMock(return_value=profile),
        ):
            prompt = await _build_system_prompt_legacy(memory, user, "hey")

        assert "film" in prompt, "User primary interest must appear in legacy prompt"

    @pytest.mark.asyncio
    async def test_seeded_memory_facts_in_legacy_prompt(self):
        """Seeded memory facts (from onboarding) appear in legacy prompt."""
        seeded_facts = "User's name is Alice. User lives in Paris."
        memory = MagicMock()
        memory.get_context_for_prompt = AsyncMock(return_value=seeded_facts)
        user = self._make_user()
        profile = self._make_profile()

        with patch(
            "nikita.agents.text.agent._load_user_profile_for_legacy",
            new=AsyncMock(return_value=profile),
        ):
            prompt = await _build_system_prompt_legacy(memory, user, "hey nikita")

        # At least one seeded fact should appear
        assert "User's name is Alice" in prompt or "User lives in Paris" in prompt, (
            "Seeded memory facts must appear in legacy prompt"
        )

    @pytest.mark.asyncio
    async def test_all_profile_fields_in_prompt_comprehensive(self):
        """Combined: all 5 key profile fields + seeded facts present together."""
        seeded = "User's name is Alice. User lives in Paris."
        memory = MagicMock()
        memory.get_context_for_prompt = AsyncMock(return_value=seeded)
        user = self._make_user()
        profile = self._make_profile(
            name="Alice",
            age=27,
            location_city="Paris",
            occupation="designer",
            primary_interest="film",
        )

        with patch(
            "nikita.agents.text.agent._load_user_profile_for_legacy",
            new=AsyncMock(return_value=profile),
        ):
            prompt = await _build_system_prompt_legacy(memory, user, "hey nikita")

        assert "Alice" in prompt
        assert "27" in prompt
        assert "Paris" in prompt
        assert "designer" in prompt
        assert "film" in prompt
        # At least one seeded memory fact
        assert "User's name is Alice" in prompt or "User lives in Paris" in prompt

    @pytest.mark.asyncio
    async def test_no_profile_row_does_not_crash(self):
        """When UserProfile doesn't exist (None), legacy path still works."""
        memory = MagicMock()
        memory.get_context_for_prompt = AsyncMock(return_value="")
        user = self._make_user()

        with patch(
            "nikita.agents.text.agent._load_user_profile_for_legacy",
            new=AsyncMock(return_value=None),
        ):
            prompt = await _build_system_prompt_legacy(memory, user, "hey")

        # Should still produce a valid prompt with persona
        assert "Nikita" in prompt or len(prompt) > 100

    @pytest.mark.asyncio
    async def test_profile_none_fields_skipped(self):
        """None fields in UserProfile are gracefully omitted (no 'None' literal in prompt)."""
        memory = MagicMock()
        memory.get_context_for_prompt = AsyncMock(return_value="")
        user = self._make_user()

        profile = MagicMock()
        profile.name = "Bob"
        profile.age = None       # No age collected
        profile.location_city = None   # No city collected
        profile.occupation = None
        profile.primary_interest = "music"

        with patch(
            "nikita.agents.text.agent._load_user_profile_for_legacy",
            new=AsyncMock(return_value=profile),
        ):
            prompt = await _build_system_prompt_legacy(memory, user, "hey")

        assert "Bob" in prompt
        assert "music" in prompt
        # None literal must not appear
        assert ": None" not in prompt
        assert "None." not in prompt
