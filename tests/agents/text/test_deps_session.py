"""Tests for NikitaDeps session field (Spec 038 T2.1).

Verifies that NikitaDeps includes an optional session field for
session propagation through the call chain.
"""

import pytest
from unittest.mock import MagicMock
from uuid import uuid4

from nikita.agents.text.deps import NikitaDeps


def test_nikita_deps_has_session_field():
    """Verify NikitaDeps includes session field.

    AC-2.1.1: NikitaDeps should have session: AsyncSession | None field.
    """
    # Create minimal deps with session
    user = MagicMock()
    user.chapter = 1
    settings = MagicMock()
    session = MagicMock()

    deps = NikitaDeps(
        memory=None,
        user=user,
        settings=settings,
        session=session,
    )

    assert deps.session is session


def test_deps_session_defaults_to_none():
    """Verify session has None default for backwards compatibility.

    AC-2.1.2: Session should default to None so existing code works.
    """
    user = MagicMock()
    user.chapter = 1
    settings = MagicMock()

    # Create deps without explicitly passing session
    deps = NikitaDeps(
        memory=None,
        user=user,
        settings=settings,
    )

    # Session should default to None
    assert deps.session is None


def test_deps_with_all_fields():
    """Verify NikitaDeps works with all fields populated."""
    user = MagicMock()
    user.chapter = 2
    settings = MagicMock()
    memory = MagicMock()
    session = MagicMock()
    conversation_id = uuid4()

    deps = NikitaDeps(
        memory=memory,
        user=user,
        settings=settings,
        generated_prompt="Test prompt",
        conversation_messages=[{"role": "user", "content": "Hi"}],
        conversation_id=conversation_id,
        session=session,
    )

    assert deps.memory is memory
    assert deps.user is user
    assert deps.settings is settings
    assert deps.generated_prompt == "Test prompt"
    assert deps.conversation_messages == [{"role": "user", "content": "Hi"}]
    assert deps.conversation_id == conversation_id
    assert deps.session is session


def test_deps_chapter_property():
    """Verify chapter property still works after adding session."""
    user = MagicMock()
    user.chapter = 3
    settings = MagicMock()

    deps = NikitaDeps(
        memory=None,
        user=user,
        settings=settings,
        session=None,
    )

    assert deps.chapter == 3
