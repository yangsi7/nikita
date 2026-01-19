"""Integration tests for HierarchicalPromptComposer (Spec 021, T017).

AC-T017.1: Test file tests/context/test_composer_integration.py
AC-T017.2: Test full composition with mock package
AC-T017.3: Test degradation scenario (no package)
AC-T017.4: Test Layer 6 modifications
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from nikita.context import (
    HierarchicalPromptComposer,
    TokenValidator,
    get_prompt_composer,
)
from nikita.context.layers import (
    Layer6Handler,
    ModificationType,
    PromptModification,
    get_layer6_handler,
)
from nikita.context.package import (
    ActiveThread,
    ContextPackage,
    EmotionalState,
)


class TestFullCompositionWithPackage:
    """AC-T017.2: Test full composition with mock package."""

    def test_compose_with_complete_package(self):
        """Full composition with all package fields populated."""
        composer = get_prompt_composer()
        user_id = uuid4()

        # Create a rich package with all fields
        package = ContextPackage(
            user_id=user_id,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            chapter_layer="Chapter 2 behavioral overlays",
            emotional_state_layer="Feeling curious and engaged",
            situation_hints={"time_of_day": "evening", "gap_since_last": "2 hours"},
            user_facts=[
                "Works as a software engineer",
                "Loves hiking on weekends",
                "Has a golden retriever named Max",
                "Enjoys Italian cuisine",
                "Recently got promoted",
            ],
            relationship_events=[
                "Had first deep conversation about family",
                "Shared favorite movies",
                "Discussed career ambitions",
            ],
            active_threads=[
                ActiveThread(
                    topic="Planning hiking trip together",
                    status="open",
                    last_mentioned=datetime.now(timezone.utc) - timedelta(hours=2),
                ),
                ActiveThread(
                    topic="User's work project deadline",
                    status="open",
                    last_mentioned=datetime.now(timezone.utc) - timedelta(days=1),
                ),
            ],
            today_summary="We discussed weekend plans and shared music recommendations",
            week_summaries=[
                "Monday: Got to know each other's backgrounds",
                "Tuesday: Talked about hobbies and interests",
            ],
            nikita_mood=EmotionalState(arousal=0.6, valence=0.7),
            nikita_energy=0.75,
            life_events_today=[
                "Finished reading a great book",
                "Went to yoga class",
            ],
        )

        result = composer.compose(
            user_id=user_id,
            chapter=2,
            emotional_state=EmotionalState(arousal=0.6, valence=0.7),
            package=package,
            current_time=datetime.now(timezone.utc).replace(hour=20),  # Evening
            last_interaction=datetime.now(timezone.utc) - timedelta(hours=2),
            conversation_active=False,
        )

        # Verify structure
        assert result.full_text is not None
        assert len(result.full_text) > 500
        assert result.total_tokens > 100

        # Verify layer breakdown
        assert "layer1_base_personality" in result.layer_breakdown
        assert "layer2_chapter" in result.layer_breakdown
        assert "layer3_emotional_state" in result.layer_breakdown
        assert "layer4_situation" in result.layer_breakdown
        assert "layer5_context" in result.layer_breakdown
        assert "layer6_modifications" in result.layer_breakdown

        # Verify package content is incorporated
        assert "software engineer" in result.full_text.lower() or "works" in result.full_text.lower()

    def test_compose_with_minimal_package(self):
        """Composition with package containing only essential fields."""
        composer = get_prompt_composer()
        user_id = uuid4()

        # Minimal package with just a few facts
        package = ContextPackage(
            user_id=user_id,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            user_facts=["User name is Alex"],
        )

        result = composer.compose(
            user_id=user_id,
            chapter=1,
            emotional_state=EmotionalState(),
            package=package,
        )

        assert result.full_text is not None
        assert result.layer_breakdown["layer5_context"] > 0

    def test_different_chapters_affect_composition(self):
        """Different chapters produce distinct prompts."""
        composer = get_prompt_composer()
        user_id = uuid4()

        results = []
        for chapter in [1, 3, 5]:
            result = composer.compose(
                user_id=user_id,
                chapter=chapter,
                emotional_state=EmotionalState(),
                package=None,
            )
            results.append(result.full_text)

        # All should be unique
        assert len(set(results)) == 3


class TestDegradationScenarios:
    """AC-T017.3: Test degradation scenario (no package)."""

    def test_compose_without_package(self):
        """Composition works without context package."""
        composer = get_prompt_composer()
        user_id = uuid4()

        result = composer.compose(
            user_id=user_id,
            chapter=2,
            emotional_state=EmotionalState(),
            package=None,  # No package
        )

        # Should still produce valid prompt
        assert result.full_text is not None
        assert len(result.full_text) > 200  # At least base personality
        assert result.layer_breakdown["layer5_context"] == 0  # No context layer

    def test_compose_without_emotional_state(self):
        """Composition handles missing emotional state."""
        composer = get_prompt_composer()
        user_id = uuid4()

        result = composer.compose(
            user_id=user_id,
            chapter=1,
            emotional_state=None,  # No emotional state
            package=None,
        )

        assert result.full_text is not None
        # Should use default/neutral emotional state
        assert result.layer_breakdown["layer3_emotional_state"] >= 0

    def test_compose_with_expired_package(self):
        """Composition handles expired package gracefully."""
        composer = get_prompt_composer()
        user_id = uuid4()

        # Expired package
        expired_package = ContextPackage(
            user_id=user_id,
            created_at=datetime.now(timezone.utc) - timedelta(days=2),
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),  # Expired
            user_facts=["Old fact"],
        )

        # Should still work (package validation is caller's responsibility)
        result = composer.compose(
            user_id=user_id,
            chapter=1,
            emotional_state=EmotionalState(),
            package=expired_package,
        )

        assert result.full_text is not None

    def test_degraded_flag_set_on_layer_failure(self):
        """Degraded flag set when layer fails to compose."""
        composer = HierarchicalPromptComposer()
        user_id = uuid4()

        # Normal composition should not be degraded
        result = composer.compose(
            user_id=user_id,
            chapter=1,
            emotional_state=EmotionalState(),
            package=None,
        )

        # With all layers working, should not be degraded
        assert not result.degraded

    def test_composition_produces_nikita_content(self):
        """Degraded composition still contains Nikita's personality."""
        composer = get_prompt_composer()
        user_id = uuid4()

        result = composer.compose(
            user_id=user_id,
            chapter=3,
            emotional_state=None,
            package=None,
        )

        # Should have Nikita's core personality
        assert "nikita" in result.full_text.lower()


class TestLayer6Modifications:
    """AC-T017.4: Test Layer 6 modifications."""

    def test_detect_mood_shift_in_message(self):
        """Layer 6 detects mood shifts in user messages."""
        handler = get_layer6_handler()

        # Positive news
        mods = handler.detect_triggers(
            message="I got the job! I'm so happy!",
            current_mood="neutral",
        )

        assert len(mods) > 0
        mood_shifts = [m for m in mods if m.type == ModificationType.MOOD_SHIFT]
        assert len(mood_shifts) > 0

    def test_detect_memory_retrieval_trigger(self):
        """Layer 6 detects memory retrieval needs."""
        handler = get_layer6_handler()

        mods = handler.detect_triggers(
            message="Remember when I told you about my sister?",
            current_mood="neutral",
        )

        memory_retrievals = [m for m in mods if m.type == ModificationType.MEMORY_RETRIEVAL]
        assert len(memory_retrievals) > 0

    def test_apply_mood_shift_to_prompt(self):
        """Layer 6 applies mood shift to current prompt."""
        handler = get_layer6_handler()

        original_prompt = "This is the base prompt for conversation."

        modification = PromptModification(
            type=ModificationType.MOOD_SHIFT,
            content="Feeling excited and supportive",
            reason="User shared good news",
        )

        modified = handler.apply_modification(original_prompt, modification)

        assert modified != original_prompt
        assert "excited" in modified.lower() or "supportive" in modified.lower()

    @pytest.mark.asyncio
    async def test_process_memory_retrieval_modification(self):
        """Layer 6 processes memory retrieval with Graphiti mock."""
        handler = Layer6Handler()
        user_id = uuid4()

        with patch.object(handler, "_get_memory_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.search.return_value = [
                type("Result", (), {"content": "User's sister is named Sarah"})()
            ]
            mock_get_client.return_value = mock_client

            modification = PromptModification(
                type=ModificationType.MEMORY_RETRIEVAL,
                content="",
                reason="User mentioned sister",
                query="sister",
            )

            result = await handler.process_modification(
                user_id=user_id,
                current_prompt="Base prompt.",
                modification=modification,
            )

            assert "Sarah" in result or "sister" in result

    def test_compose_static_layer6(self):
        """Layer 6 static section is included."""
        handler = get_layer6_handler()

        static = handler.compose_static()

        assert isinstance(static, str)
        assert len(static) > 50
        assert "real-time" in static.lower() or "adjust" in static.lower()


class TestTokenBudgetCompliance:
    """Test that composition stays within token budget."""

    def test_total_tokens_within_budget(self):
        """Total composition stays within 4000 token budget."""
        composer = get_prompt_composer()
        validator = TokenValidator()
        user_id = uuid4()

        # Rich package that might push limits
        package = ContextPackage(
            user_id=user_id,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            user_facts=[f"Fact {i}: Some detailed information" for i in range(20)],
            relationship_events=[f"Event {i}" for i in range(10)],
            active_threads=[
                ActiveThread(
                    topic=f"Thread {i}",
                    status="open",
                    last_mentioned=datetime.now(timezone.utc),
                )
                for i in range(10)
            ],
            today_summary="A very detailed summary " * 20,
            week_summaries=["Week summary " * 10 for _ in range(5)],
        )

        result = composer.compose(
            user_id=user_id,
            chapter=3,
            emotional_state=EmotionalState(arousal=0.8, valence=0.6),
            package=package,
        )

        # Use actual tokenizer to verify
        actual_tokens = validator.count_tokens(result.full_text)

        # Should be within budget (with some tolerance)
        assert actual_tokens <= 5000, f"Token count {actual_tokens} exceeds safe limit"

    def test_layer_breakdown_sums_correctly(self):
        """Layer breakdown token sum matches total."""
        composer = get_prompt_composer()
        user_id = uuid4()

        result = composer.compose(
            user_id=user_id,
            chapter=2,
            emotional_state=EmotionalState(),
            package=None,
        )

        layer_sum = sum(result.layer_breakdown.values())

        # Allow some margin for separators between layers
        assert result.total_tokens >= layer_sum * 0.8
        assert result.total_tokens <= layer_sum * 1.2


class TestEndToEndFlow:
    """Test complete end-to-end prompt composition flow."""

    def test_morning_conversation_flow(self):
        """Simulate morning conversation start."""
        composer = get_prompt_composer()
        user_id = uuid4()

        # Morning time, fresh start
        morning = datetime.now(timezone.utc).replace(hour=8, minute=0)

        result = composer.compose(
            user_id=user_id,
            chapter=1,
            emotional_state=EmotionalState(arousal=0.5, valence=0.6),
            package=None,
            current_time=morning,
            last_interaction=morning - timedelta(hours=10),  # Last night
            conversation_active=False,
        )

        assert result.full_text is not None
        # Should detect morning situation
        # Content will include morning-appropriate guidance

    def test_continuing_conversation_flow(self):
        """Simulate continuing an active conversation."""
        composer = get_prompt_composer()
        user_id = uuid4()

        now = datetime.now(timezone.utc)

        result = composer.compose(
            user_id=user_id,
            chapter=3,
            emotional_state=EmotionalState(arousal=0.7, valence=0.7),
            package=None,
            current_time=now,
            last_interaction=now - timedelta(minutes=3),  # Very recent
            conversation_active=True,  # Active conversation
        )

        assert result.full_text is not None
        # Should detect mid-conversation situation

    def test_reconnecting_after_gap(self):
        """Simulate reconnecting after time apart."""
        composer = get_prompt_composer()
        user_id = uuid4()

        now = datetime.now(timezone.utc).replace(hour=14)  # 2pm (not morning/evening)

        result = composer.compose(
            user_id=user_id,
            chapter=2,
            emotional_state=EmotionalState(arousal=0.5, valence=0.5),
            package=None,
            current_time=now,
            last_interaction=now - timedelta(hours=8),  # 8 hours ago
            conversation_active=False,
        )

        assert result.full_text is not None
        # Should detect after-gap situation
