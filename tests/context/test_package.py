"""Tests for ContextPackage model (Spec 021, T002).

AC-T002.1: ContextPackage Pydantic model with all fields from spec
AC-T002.2: Serialization to/from JSON working
AC-T002.3: Validation for required fields
AC-T002.4: Unit tests for model
"""

import json
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from nikita.context.package import (
    ActiveThread,
    ComposedPrompt,
    ContextPackage,
    EmotionalState,
    ProcessingResult,
)


class TestEmotionalState:
    """Tests for EmotionalState model."""

    def test_default_values(self):
        """All dimensions default to 0.5 (neutral)."""
        state = EmotionalState()
        assert state.arousal == 0.5
        assert state.valence == 0.5
        assert state.dominance == 0.5
        assert state.intimacy == 0.5

    def test_valid_range(self):
        """Dimensions must be between 0.0 and 1.0."""
        state = EmotionalState(arousal=0.0, valence=1.0, dominance=0.3, intimacy=0.7)
        assert state.arousal == 0.0
        assert state.valence == 1.0

    def test_invalid_range_raises(self):
        """Values outside 0-1 range should raise validation error."""
        with pytest.raises(ValueError):
            EmotionalState(arousal=1.5)
        with pytest.raises(ValueError):
            EmotionalState(valence=-0.1)

    def test_to_description_high_energy(self):
        """High arousal generates 'energetic' description."""
        state = EmotionalState(arousal=0.8, valence=0.8, dominance=0.8, intimacy=0.8)
        desc = state.to_description()
        assert "energetic" in desc
        assert "happy" in desc
        assert "confident" in desc
        assert "open" in desc

    def test_to_description_low_energy(self):
        """Low arousal generates 'tired' description."""
        state = EmotionalState(arousal=0.2, valence=0.2, dominance=0.2, intimacy=0.2)
        desc = state.to_description()
        assert "tired" in desc
        assert "down" in desc


class TestActiveThread:
    """Tests for ActiveThread model."""

    def test_basic_thread(self):
        """Create a basic active thread."""
        thread = ActiveThread(topic="User's job interview")
        assert thread.topic == "User's job interview"
        assert thread.status == "open"
        assert thread.last_mentioned is None

    def test_thread_with_all_fields(self):
        """Create thread with all fields populated."""
        now = datetime.utcnow()
        thread = ActiveThread(
            topic="Plans for the weekend",
            status="pending",
            last_mentioned=now,
            notes="User mentioned hiking",
        )
        assert thread.status == "pending"
        assert thread.last_mentioned == now
        assert "hiking" in thread.notes


class TestContextPackage:
    """Tests for ContextPackage model (AC-T002.1-4)."""

    def test_required_fields_only(self):
        """AC-T002.1: Create package with only user_id."""
        user_id = uuid4()
        package = ContextPackage(user_id=user_id)

        assert package.user_id == user_id
        assert package.chapter_layer == ""
        assert package.user_facts == []
        assert package.version == "1.0.0"

    def test_all_spec_fields_present(self):
        """AC-T002.1: All fields from spec are present."""
        user_id = uuid4()
        now = datetime.utcnow()
        expires = now + timedelta(hours=24)

        package = ContextPackage(
            user_id=user_id,
            created_at=now,
            expires_at=expires,
            chapter_layer="Chapter 2 behavioral overlay...",
            emotional_state_layer="Feeling tired but content...",
            situation_hints={"last_gap_hours": 4.5, "time_pattern": "evening"},
            user_facts=["Works in finance", "Lives in NYC"],
            relationship_events=["First kiss on day 5"],
            active_threads=[ActiveThread(topic="Job interview")],
            today_summary="Had a deep conversation about fears",
            week_summaries=["Monday: light banter", "Tuesday: emotional exchange"],
            nikita_mood=EmotionalState(arousal=0.3, valence=0.6),
            nikita_energy=0.4,
            life_events_today=["Had a tough day at work", "Got coffee with friend"],
            version="1.0.0",
        )

        # Verify all fields
        assert package.chapter_layer == "Chapter 2 behavioral overlay..."
        assert package.emotional_state_layer == "Feeling tired but content..."
        assert package.situation_hints["last_gap_hours"] == 4.5
        assert len(package.user_facts) == 2
        assert len(package.relationship_events) == 1
        assert len(package.active_threads) == 1
        assert package.today_summary is not None
        assert len(package.week_summaries) == 2
        assert package.nikita_mood.arousal == 0.3
        assert package.nikita_energy == 0.4
        assert len(package.life_events_today) == 2

    def test_json_serialization(self):
        """AC-T002.2: Serialization to JSON."""
        user_id = uuid4()
        package = ContextPackage(
            user_id=user_id,
            chapter_layer="Test layer",
            user_facts=["Fact 1", "Fact 2"],
            nikita_mood=EmotionalState(arousal=0.7),
        )

        # Serialize to JSON
        json_str = package.model_dump_json()
        assert isinstance(json_str, str)
        assert "Test layer" in json_str

        # Parse JSON
        data = json.loads(json_str)
        assert data["chapter_layer"] == "Test layer"
        assert len(data["user_facts"]) == 2

    def test_json_deserialization(self):
        """AC-T002.2: Deserialization from JSON."""
        user_id = uuid4()
        original = ContextPackage(
            user_id=user_id,
            chapter_layer="Original layer",
            user_facts=["Important fact"],
            nikita_mood=EmotionalState(valence=0.8),
        )

        # Round-trip through JSON
        json_str = original.model_dump_json()
        restored = ContextPackage.model_validate_json(json_str)

        assert restored.user_id == original.user_id
        assert restored.chapter_layer == original.chapter_layer
        assert restored.user_facts == original.user_facts
        assert restored.nikita_mood.valence == 0.8

    def test_required_user_id(self):
        """AC-T002.3: user_id is required."""
        with pytest.raises(ValueError):
            ContextPackage()  # Missing user_id

    def test_user_facts_limit(self):
        """AC-T002.3: user_facts limited to 20 items."""
        user_id = uuid4()
        facts = [f"Fact {i}" for i in range(30)]  # 30 facts

        package = ContextPackage(user_id=user_id, user_facts=facts)
        assert len(package.user_facts) == 20  # Truncated to 20

    def test_relationship_events_limit(self):
        """AC-T002.3: relationship_events limited to 10 items."""
        user_id = uuid4()
        events = [f"Event {i}" for i in range(15)]  # 15 events

        package = ContextPackage(user_id=user_id, relationship_events=events)
        assert len(package.relationship_events) == 10  # Truncated to 10

    def test_week_summaries_limit(self):
        """AC-T002.3: week_summaries limited to 7 items."""
        user_id = uuid4()
        summaries = [f"Day {i} summary" for i in range(10)]  # 10 summaries

        package = ContextPackage(user_id=user_id, week_summaries=summaries)
        assert len(package.week_summaries) == 7  # Truncated to 7

    def test_life_events_today_limit(self):
        """AC-T015.3: life_events_today limited to 3 items (top by importance)."""
        user_id = uuid4()
        events = [f"Event {i}" for i in range(10)]  # 10 events

        package = ContextPackage(user_id=user_id, life_events_today=events)
        assert len(package.life_events_today) == 3  # Truncated to 3
        # Verify first 3 are kept
        assert package.life_events_today == ["Event 0", "Event 1", "Event 2"]

    def test_is_expired(self):
        """Test expiration check."""
        user_id = uuid4()

        # Not expired (default 24h TTL)
        package = ContextPackage(user_id=user_id)
        assert not package.is_expired()

        # Expired
        expired = ContextPackage(
            user_id=user_id, expires_at=datetime.utcnow() - timedelta(hours=1)
        )
        assert expired.is_expired()

    def test_token_estimate(self):
        """Test token estimation."""
        user_id = uuid4()
        package = ContextPackage(
            user_id=user_id,
            chapter_layer="A" * 400,  # ~100 tokens
            user_facts=["B" * 80] * 5,  # ~100 tokens
        )

        estimate = package.get_token_estimate()
        # 400 + 400 = 800 chars / 4 = 200 tokens
        assert estimate == 200


class TestComposedPrompt:
    """Tests for ComposedPrompt model."""

    def test_basic_prompt(self):
        """Create a basic composed prompt."""
        prompt = ComposedPrompt(
            full_text="You are Nikita...",
            total_tokens=1500,
            layer_breakdown={"layer1": 500, "layer2": 300, "layer5": 700},
        )

        assert "Nikita" in prompt.full_text
        assert prompt.total_tokens == 1500
        assert prompt.layer_breakdown["layer1"] == 500
        assert not prompt.degraded

    def test_degraded_prompt(self):
        """Create a degraded prompt (fallback mode)."""
        prompt = ComposedPrompt(
            full_text="Minimal prompt...",
            total_tokens=500,
            degraded=True,
        )

        assert prompt.degraded
        assert prompt.package_version is None


class TestProcessingResult:
    """Tests for ProcessingResult model."""

    def test_successful_result(self):
        """Create a successful processing result."""
        result = ProcessingResult(
            user_id=uuid4(),
            conversation_id=uuid4(),
            success=True,
            steps_completed=["graph_update", "summary_generation"],
            duration_ms=1500,
            package_stored=True,
        )

        assert result.success
        assert len(result.steps_completed) == 2
        assert result.package_stored

    def test_add_step(self):
        """Test adding steps."""
        result = ProcessingResult(user_id=uuid4(), conversation_id=uuid4())
        result.add_step("step1")
        result.add_step("step2")

        assert result.steps_completed == ["step1", "step2"]

    def test_add_error(self):
        """Test adding errors."""
        result = ProcessingResult(user_id=uuid4(), conversation_id=uuid4(), success=True)
        result.add_error("Connection failed")

        assert not result.success  # Changed to False
        assert "Connection failed" in result.errors
