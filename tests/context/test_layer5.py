"""Tests for Layer5Injector (Spec 021, T014).

AC-T014.1: Layer5Injector class injects context from package
AC-T014.2: Formats user_facts, relationship_events, active_threads, summaries
AC-T014.3: Token count within budget (~500)
AC-T014.4: Unit tests for injector
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from nikita.context.layers.context_injection import (
    Layer5Injector,
    get_layer5_injector,
)
from nikita.context.package import (
    ActiveThread,
    ContextPackage,
    EmotionalState,
)


class TestLayer5Injector:
    """Tests for Layer5Injector class."""

    def test_init_default(self):
        """AC-T014.1: Injector initializes properly."""
        injector = Layer5Injector()
        assert injector is not None

    def test_inject_with_full_package(self):
        """AC-T014.1, AC-T014.2: Injects all context from package."""
        injector = Layer5Injector()
        user_id = uuid4()

        package = ContextPackage(
            user_id=user_id,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            user_facts=["User works in finance", "User likes coffee", "User has a dog"],
            relationship_events=["First date last week", "Had a deep conversation"],
            active_threads=[
                ActiveThread(
                    topic="Career discussion",
                    status="open",
                    last_mentioned=datetime.now(timezone.utc),
                ),
                ActiveThread(
                    topic="Weekend plans",
                    status="open",
                    last_mentioned=datetime.now(timezone.utc) - timedelta(days=1),
                ),
            ],
            today_summary="Had a great chat about movies",
            week_summaries=["Week started well", "Deep conversations about life"],
            life_events_today=["Finished a security audit", "Went to yoga"],
        )

        result = injector.inject(package)

        assert isinstance(result, str)
        assert len(result) > 100
        # Verify key content is included
        assert "finance" in result.lower()
        assert "coffee" in result.lower()
        assert "career" in result.lower() or "discussion" in result.lower()

    def test_inject_with_empty_package(self):
        """AC-T014.1: Handles package with minimal content."""
        injector = Layer5Injector()
        user_id = uuid4()

        package = ContextPackage(
            user_id=user_id,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )

        result = injector.inject(package)

        # Should return minimal or empty prompt
        assert result is None or len(result) < 100

    def test_inject_returns_none_when_no_package(self):
        """AC-T014.1: Returns None when package is None."""
        injector = Layer5Injector()

        result = injector.inject(None)

        assert result is None

    def test_formats_user_facts(self):
        """AC-T014.2: Formats user_facts correctly."""
        injector = Layer5Injector()
        user_id = uuid4()

        package = ContextPackage(
            user_id=user_id,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            user_facts=["Fact 1", "Fact 2", "Fact 3"],
        )

        result = injector.inject(package)

        assert result is not None
        assert "Fact 1" in result
        assert "Fact 2" in result
        assert "Fact 3" in result

    def test_formats_relationship_events(self):
        """AC-T014.2: Formats relationship_events correctly."""
        injector = Layer5Injector()
        user_id = uuid4()

        package = ContextPackage(
            user_id=user_id,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            relationship_events=["Event A", "Event B"],
        )

        result = injector.inject(package)

        assert result is not None
        assert "Event A" in result
        assert "Event B" in result

    def test_formats_active_threads(self):
        """AC-T014.2: Formats active_threads correctly."""
        injector = Layer5Injector()
        user_id = uuid4()

        package = ContextPackage(
            user_id=user_id,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            active_threads=[
                ActiveThread(
                    topic="Open topic",
                    status="open",
                    last_mentioned=datetime.now(timezone.utc),
                ),
                ActiveThread(
                    topic="Resolved topic",
                    status="resolved",
                    last_mentioned=datetime.now(timezone.utc),
                ),
            ],
        )

        result = injector.inject(package)

        assert result is not None
        assert "Open topic" in result
        # Resolved topics might be excluded or marked differently
        # The implementation decides the exact format

    def test_formats_summaries(self):
        """AC-T014.2: Formats today_summary and week_summaries."""
        injector = Layer5Injector()
        user_id = uuid4()

        package = ContextPackage(
            user_id=user_id,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            today_summary="Today we discussed work",
            week_summaries=["Monday was productive", "Tuesday had challenges"],
        )

        result = injector.inject(package)

        assert result is not None
        assert "work" in result.lower() or "today" in result.lower()
        assert "monday" in result.lower() or "productive" in result.lower()

    def test_formats_life_events(self):
        """AC-T014.2: Formats life_events_today."""
        injector = Layer5Injector()
        user_id = uuid4()

        package = ContextPackage(
            user_id=user_id,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            life_events_today=["Had coffee with friend", "Finished project"],
        )

        result = injector.inject(package)

        assert result is not None
        assert "coffee" in result.lower() or "friend" in result.lower()

    def test_token_count_within_budget(self):
        """AC-T014.3: Token count within budget (~500)."""
        injector = Layer5Injector()
        user_id = uuid4()

        # Create a rich package
        package = ContextPackage(
            user_id=user_id,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            user_facts=[f"Fact {i}" for i in range(15)],  # Many facts
            relationship_events=[f"Event {i}" for i in range(10)],
            active_threads=[
                ActiveThread(
                    topic=f"Thread {i}",
                    status="open",
                    last_mentioned=datetime.now(timezone.utc),
                )
                for i in range(8)
            ],
            today_summary="A very detailed summary of today's conversation" * 3,
            week_summaries=["Week summary " * 10 for _ in range(5)],
            life_events_today=[f"Life event {i}" for i in range(5)],
        )

        result = injector.inject(package)

        # Rough estimate: 1 token ≈ 4 characters
        if result:
            estimated_tokens = len(result) // 4
            # Budget is ~500, allow some margin
            assert estimated_tokens <= 600, f"Token estimate {estimated_tokens} exceeds budget"

    def test_limits_user_facts(self):
        """AC-T014.2: Limits user_facts to reasonable count."""
        injector = Layer5Injector()
        user_id = uuid4()

        package = ContextPackage(
            user_id=user_id,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            user_facts=[f"Fact number {i}" for i in range(50)],  # Many facts
        )

        result = injector.inject(package)

        # Should limit facts to keep within budget
        if result:
            fact_count = result.lower().count("fact number")
            assert fact_count <= 15  # Should limit, not include all 50

    def test_limits_active_threads(self):
        """AC-T014.2: Limits active_threads to reasonable count."""
        injector = Layer5Injector()
        user_id = uuid4()

        package = ContextPackage(
            user_id=user_id,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            active_threads=[
                ActiveThread(
                    topic=f"Topic {i}",
                    status="open",
                    last_mentioned=datetime.now(timezone.utc),
                )
                for i in range(20)
            ],
        )

        result = injector.inject(package)

        # Should limit threads
        if result:
            thread_count = result.lower().count("topic ")
            assert thread_count <= 8  # Should limit


class TestLayer5ModuleFunctions:
    """Tests for module-level convenience functions."""

    def test_get_layer5_injector_singleton(self):
        """AC-T014.1: get_layer5_injector returns singleton."""
        injector1 = get_layer5_injector()
        injector2 = get_layer5_injector()

        assert injector1 is injector2

    def test_injector_has_token_estimate(self):
        """AC-T014.3: Injector provides token estimate property."""
        injector = get_layer5_injector()

        # Should have a token_estimate property
        assert hasattr(injector, "token_estimate")
        assert injector.token_estimate == 500  # Target budget
