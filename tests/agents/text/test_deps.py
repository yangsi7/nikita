"""Tests for NikitaDeps dataclass - TDD for T1.2.

Acceptance Criteria:
- AC-1.2.1: NikitaDeps contains memory: NikitaMemory
- AC-1.2.2: NikitaDeps contains user: User
- AC-1.2.3: NikitaDeps contains settings: Settings
- AC-1.2.4: chapter property returns user.chapter
- AC-1.2.5: Type hints complete for Pydantic AI compatibility
"""

import pytest
from dataclasses import fields, is_dataclass
from unittest.mock import MagicMock


class TestNikitaDepsStructure:
    """Tests for NikitaDeps dataclass structure."""

    def test_is_dataclass(self):
        """NikitaDeps should be a dataclass."""
        from nikita.agents.text.deps import NikitaDeps

        assert is_dataclass(NikitaDeps)

    def test_ac_1_2_1_has_memory_field(self):
        """AC-1.2.1: NikitaDeps contains memory: NikitaMemory."""
        from nikita.agents.text.deps import NikitaDeps

        field_names = [f.name for f in fields(NikitaDeps)]
        assert "memory" in field_names

    def test_ac_1_2_2_has_user_field(self):
        """AC-1.2.2: NikitaDeps contains user: User."""
        from nikita.agents.text.deps import NikitaDeps

        field_names = [f.name for f in fields(NikitaDeps)]
        assert "user" in field_names

    def test_ac_1_2_3_has_settings_field(self):
        """AC-1.2.3: NikitaDeps contains settings: Settings."""
        from nikita.agents.text.deps import NikitaDeps

        field_names = [f.name for f in fields(NikitaDeps)]
        assert "settings" in field_names

    def test_ac_1_2_5_type_hints_complete(self):
        """AC-1.2.5: Type hints complete for Pydantic AI compatibility."""
        from nikita.agents.text.deps import NikitaDeps

        for field in fields(NikitaDeps):
            assert field.type is not type(None), f"Field {field.name} must have a type hint"


class TestNikitaDepsProperties:
    """Tests for NikitaDeps property access."""

    def test_ac_1_2_4_chapter_property(self):
        """AC-1.2.4: chapter property returns user.chapter."""
        from nikita.agents.text.deps import NikitaDeps

        # Create mock objects
        mock_memory = MagicMock()
        mock_user = MagicMock()
        mock_user.chapter = 3
        mock_settings = MagicMock()

        deps = NikitaDeps(
            memory=mock_memory,
            user=mock_user,
            settings=mock_settings,
        )

        assert deps.chapter == 3

    def test_chapter_property_follows_user_changes(self):
        """Chapter property should reflect user.chapter changes."""
        from nikita.agents.text.deps import NikitaDeps

        mock_memory = MagicMock()
        mock_user = MagicMock()
        mock_settings = MagicMock()

        deps = NikitaDeps(
            memory=mock_memory,
            user=mock_user,
            settings=mock_settings,
        )

        mock_user.chapter = 1
        assert deps.chapter == 1

        mock_user.chapter = 5
        assert deps.chapter == 5


class TestNikitaDepsInstantiation:
    """Tests for creating NikitaDeps instances."""

    def test_can_instantiate_with_mocks(self):
        """Should be able to create NikitaDeps with mock objects."""
        from nikita.agents.text.deps import NikitaDeps

        mock_memory = MagicMock()
        mock_user = MagicMock()
        mock_settings = MagicMock()

        deps = NikitaDeps(
            memory=mock_memory,
            user=mock_user,
            settings=mock_settings,
        )

        assert deps.memory is mock_memory
        assert deps.user is mock_user
        assert deps.settings is mock_settings

    def test_requires_all_fields(self):
        """Should require all fields to instantiate."""
        from nikita.agents.text.deps import NikitaDeps

        with pytest.raises(TypeError):
            NikitaDeps()  # type: ignore

        with pytest.raises(TypeError):
            NikitaDeps(memory=MagicMock())  # type: ignore
