"""Performance tests for HierarchicalPromptComposer (Spec 021, T018).

AC-T018.1: Test file tests/context/test_composer_performance.py
AC-T018.2: Context injection P99 < 150ms
AC-T018.3: Package load P99 < 50ms
AC-T018.4: Run with realistic data sizes
"""

import statistics
import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from nikita.context import HierarchicalPromptComposer, get_prompt_composer
from nikita.context.layers import get_layer5_injector, get_layer6_handler
from nikita.context.package import (
    ActiveThread,
    ContextPackage,
    EmotionalState,
)


def create_realistic_package(user_id) -> ContextPackage:
    """Create a realistic context package with typical data sizes."""
    return ContextPackage(
        user_id=user_id,
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        chapter_layer="Chapter 3: Building Trust - Focus on deeper conversations",
        emotional_state_layer="Valence: 0.7, Arousal: 0.5, Dominance: 0.5",
        situation_hints={
            "time_of_day": "evening",
            "gap_since_last": "4 hours",
            "conversation_style": "casual",
        },
        user_facts=[
            "Works as a software engineer at a tech startup",
            "Lives in San Francisco, originally from Portland",
            "Has a golden retriever named Max who is 3 years old",
            "Enjoys hiking, especially in Marin Headlands",
            "Favorite cuisine is Thai food",
            "Recently got promoted to senior engineer",
            "Plays guitar as a hobby, learning for 2 years",
            "Reads mostly science fiction and fantasy books",
        ],
        relationship_events=[
            "First date was at a coffee shop downtown",
            "Shared childhood memories last Tuesday",
            "Had a disagreement about communication styles",
            "Made up and established better boundaries",
        ],
        active_threads=[
            ActiveThread(
                topic="Planning weekend hiking trip to Point Reyes",
                status="open",
                last_mentioned=datetime.now(timezone.utc) - timedelta(hours=2),
            ),
            ActiveThread(
                topic="Work stress and deadline pressure",
                status="open",
                last_mentioned=datetime.now(timezone.utc) - timedelta(days=1),
            ),
            ActiveThread(
                topic="Learning to play a new song on guitar",
                status="resolved",
                last_mentioned=datetime.now(timezone.utc) - timedelta(days=3),
            ),
        ],
        today_summary="We discussed weekend hiking plans and Max's upcoming vet visit. Had a nice conversation about work-life balance.",
        week_summaries=[
            "Monday: Deep conversation about career goals and aspirations",
            "Wednesday: Light banter about favorite movies and TV shows",
        ],
        nikita_mood=EmotionalState(arousal=0.6, valence=0.7, dominance=0.5, intimacy=0.6),
        nikita_energy=0.75,
        life_events_today=[
            "Finished a challenging chapter in my new book",
            "Went to a yoga class in the morning",
            "Had coffee with a friend from college",
        ],
    )


class TestContextInjectionPerformance:
    """AC-T018.2: Context injection P99 < 150ms."""

    def test_composition_p99_under_150ms(self):
        """Full composition P99 should be under 150ms."""
        composer = get_prompt_composer()
        user_id = uuid4()
        package = create_realistic_package(user_id)

        timings = []

        # Run 100 iterations for statistical significance
        for _ in range(100):
            start = time.perf_counter()

            composer.compose(
                user_id=user_id,
                chapter=3,
                emotional_state=EmotionalState(arousal=0.6, valence=0.7),
                package=package,
                current_time=datetime.now(timezone.utc).replace(hour=20),
                last_interaction=datetime.now(timezone.utc) - timedelta(hours=4),
                conversation_active=False,
            )

            elapsed_ms = (time.perf_counter() - start) * 1000
            timings.append(elapsed_ms)

        # Calculate P99
        p99 = statistics.quantiles(timings, n=100)[98]  # 99th percentile

        print(f"\nComposition Performance:")
        print(f"  Min: {min(timings):.2f}ms")
        print(f"  Mean: {statistics.mean(timings):.2f}ms")
        print(f"  P50: {statistics.median(timings):.2f}ms")
        print(f"  P99: {p99:.2f}ms")
        print(f"  Max: {max(timings):.2f}ms")

        # P99 should be under 150ms
        assert p99 < 150, f"P99 ({p99:.2f}ms) exceeds 150ms target"

    def test_layer5_injection_p99_under_50ms(self):
        """Layer 5 injection P99 should be under 50ms."""
        injector = get_layer5_injector()
        user_id = uuid4()
        package = create_realistic_package(user_id)

        timings = []

        for _ in range(100):
            start = time.perf_counter()

            injector.inject(package)

            elapsed_ms = (time.perf_counter() - start) * 1000
            timings.append(elapsed_ms)

        p99 = statistics.quantiles(timings, n=100)[98]

        print(f"\nLayer 5 Injection Performance:")
        print(f"  Min: {min(timings):.2f}ms")
        print(f"  Mean: {statistics.mean(timings):.2f}ms")
        print(f"  P99: {p99:.2f}ms")

        assert p99 < 50, f"Layer 5 P99 ({p99:.2f}ms) exceeds 50ms target"


class TestPackageLoadPerformance:
    """AC-T018.3: Package load P99 < 50ms."""

    def test_package_creation_p99_under_50ms(self):
        """Package creation (in-memory) P99 should be under 50ms."""
        user_id = uuid4()

        timings = []

        for _ in range(100):
            start = time.perf_counter()

            # Create a realistic package
            create_realistic_package(user_id)

            elapsed_ms = (time.perf_counter() - start) * 1000
            timings.append(elapsed_ms)

        p99 = statistics.quantiles(timings, n=100)[98]

        print(f"\nPackage Creation Performance:")
        print(f"  Min: {min(timings):.2f}ms")
        print(f"  Mean: {statistics.mean(timings):.2f}ms")
        print(f"  P99: {p99:.2f}ms")

        assert p99 < 50, f"Package creation P99 ({p99:.2f}ms) exceeds 50ms target"

    def test_package_serialization_p99_under_20ms(self):
        """Package JSON serialization P99 should be under 20ms."""
        user_id = uuid4()
        package = create_realistic_package(user_id)

        timings = []

        for _ in range(100):
            start = time.perf_counter()

            # Serialize to JSON
            package.model_dump_json()

            elapsed_ms = (time.perf_counter() - start) * 1000
            timings.append(elapsed_ms)

        p99 = statistics.quantiles(timings, n=100)[98]

        print(f"\nPackage Serialization Performance:")
        print(f"  Min: {min(timings):.2f}ms")
        print(f"  Mean: {statistics.mean(timings):.2f}ms")
        print(f"  P99: {p99:.2f}ms")

        assert p99 < 20, f"Serialization P99 ({p99:.2f}ms) exceeds 20ms target"


class TestRealisticDataSizes:
    """AC-T018.4: Run with realistic data sizes."""

    def test_with_maximum_expected_data(self):
        """Test with maximum expected data sizes."""
        user_id = uuid4()

        # Maximum expected data
        package = ContextPackage(
            user_id=user_id,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            user_facts=[f"Detailed fact about user #{i} with some context" for i in range(15)],
            relationship_events=[f"Relationship event #{i} with details" for i in range(10)],
            active_threads=[
                ActiveThread(
                    topic=f"Conversation thread #{i} about some topic",
                    status="open",
                    last_mentioned=datetime.now(timezone.utc) - timedelta(hours=i),
                )
                for i in range(8)
            ],
            today_summary="A comprehensive summary of today's conversations covering multiple topics and emotional states " * 3,
            week_summaries=[f"Week summary #{i}: Detailed overview of interactions" for i in range(5)],
            life_events_today=[f"Life event #{i} with some narrative" for i in range(5)],
        )

        composer = get_prompt_composer()

        start = time.perf_counter()
        result = composer.compose(
            user_id=user_id,
            chapter=4,
            emotional_state=EmotionalState(arousal=0.8, valence=0.3, dominance=0.6),
            package=package,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        print(f"\nMax Data Composition:")
        print(f"  Time: {elapsed_ms:.2f}ms")
        print(f"  Total tokens: {result.total_tokens}")
        print(f"  Full text length: {len(result.full_text)}")

        # Should still be fast
        assert elapsed_ms < 150, f"Max data took {elapsed_ms:.2f}ms (exceeds 150ms)"

    def test_with_empty_data(self):
        """Test with minimal/empty data (worst case for missing context)."""
        composer = get_prompt_composer()
        user_id = uuid4()

        start = time.perf_counter()
        result = composer.compose(
            user_id=user_id,
            chapter=1,
            emotional_state=None,
            package=None,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        print(f"\nEmpty Data Composition:")
        print(f"  Time: {elapsed_ms:.2f}ms")
        print(f"  Total tokens: {result.total_tokens}")

        # Empty data should be very fast
        assert elapsed_ms < 50, f"Empty data took {elapsed_ms:.2f}ms (exceeds 50ms)"


class TestLayerPerformance:
    """Individual layer performance tests."""

    def test_layer1_cached_access(self):
        """Layer 1 (base personality) should be cached and fast."""
        from nikita.context.layers import get_layer1_loader

        loader = get_layer1_loader()

        timings = []
        for _ in range(100):
            start = time.perf_counter()
            _ = loader.prompt
            elapsed_ms = (time.perf_counter() - start) * 1000
            timings.append(elapsed_ms)

        p99 = statistics.quantiles(timings, n=100)[98]

        print(f"\nLayer 1 Access Performance:")
        print(f"  P99: {p99:.2f}ms")

        # Should be essentially instant (cached)
        assert p99 < 5, f"Layer 1 P99 ({p99:.2f}ms) exceeds 5ms (should be cached)"

    def test_layer2_composition(self):
        """Layer 2 (chapter) composition performance."""
        from nikita.context.layers import get_layer2_composer

        composer = get_layer2_composer()

        timings = []
        for _ in range(100):
            start = time.perf_counter()
            composer.compose(chapter=3)
            elapsed_ms = (time.perf_counter() - start) * 1000
            timings.append(elapsed_ms)

        p99 = statistics.quantiles(timings, n=100)[98]

        print(f"\nLayer 2 Composition Performance:")
        print(f"  P99: {p99:.2f}ms")

        assert p99 < 10, f"Layer 2 P99 ({p99:.2f}ms) exceeds 10ms"

    def test_layer3_composition(self):
        """Layer 3 (emotional state) composition performance."""
        from nikita.context.layers import get_layer3_composer

        composer = get_layer3_composer()
        state = EmotionalState(arousal=0.7, valence=0.6, dominance=0.5, intimacy=0.4)

        timings = []
        for _ in range(100):
            start = time.perf_counter()
            composer.compose(state)
            elapsed_ms = (time.perf_counter() - start) * 1000
            timings.append(elapsed_ms)

        p99 = statistics.quantiles(timings, n=100)[98]

        print(f"\nLayer 3 Composition Performance:")
        print(f"  P99: {p99:.2f}ms")

        assert p99 < 10, f"Layer 3 P99 ({p99:.2f}ms) exceeds 10ms"

    def test_layer4_detection_and_composition(self):
        """Layer 4 (situation) detection and composition performance."""
        from nikita.context.layers import get_layer4_computer

        computer = get_layer4_computer()
        now = datetime.now(timezone.utc)

        timings = []
        for _ in range(100):
            start = time.perf_counter()
            computer.detect_and_compose(
                current_time=now,
                last_interaction=now - timedelta(hours=2),
                conversation_active=False,
            )
            elapsed_ms = (time.perf_counter() - start) * 1000
            timings.append(elapsed_ms)

        p99 = statistics.quantiles(timings, n=100)[98]

        print(f"\nLayer 4 Detection+Composition Performance:")
        print(f"  P99: {p99:.2f}ms")

        assert p99 < 10, f"Layer 4 P99 ({p99:.2f}ms) exceeds 10ms"

    def test_layer6_trigger_detection(self):
        """Layer 6 trigger detection performance."""
        handler = get_layer6_handler()

        messages = [
            "I just got promoted at work!",
            "Remember when I told you about my sister?",
            "How was your day?",
            "I'm feeling really stressed about the deadline",
            "Let's talk about something fun",
        ]

        timings = []
        for _ in range(100):
            for msg in messages:
                start = time.perf_counter()
                handler.detect_triggers(message=msg, current_mood="neutral")
                elapsed_ms = (time.perf_counter() - start) * 1000
                timings.append(elapsed_ms)

        p99 = statistics.quantiles(timings, n=100)[98]

        print(f"\nLayer 6 Trigger Detection Performance:")
        print(f"  P99: {p99:.2f}ms")

        assert p99 < 10, f"Layer 6 detection P99 ({p99:.2f}ms) exceeds 10ms"
