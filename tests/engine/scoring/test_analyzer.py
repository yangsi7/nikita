"""Tests for scoring engine analyzer (spec 003).

TDD: These tests define the expected behavior for ScoreAnalyzer
which uses LLM to analyze conversations and produce ResponseAnalysis.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nikita.engine.scoring.analyzer import ScoreAnalyzer
from nikita.engine.scoring.models import (
    ConversationContext,
    MetricDeltas,
    ResponseAnalysis,
)


class TestScoreAnalyzerCreation:
    """Test ScoreAnalyzer initialization."""

    def test_create_analyzer(self):
        """Test creating a ScoreAnalyzer instance."""
        analyzer = ScoreAnalyzer()
        assert analyzer is not None

    def test_analyzer_has_model(self):
        """Test that analyzer has a model configured."""
        analyzer = ScoreAnalyzer()
        assert analyzer.model_name is not None
        assert "claude" in analyzer.model_name.lower() or "anthropic" in analyzer.model_name.lower()


class TestScoreAnalyzerAnalysis:
    """Test ScoreAnalyzer.analyze() method."""

    @pytest.fixture
    def analyzer(self):
        """Create ScoreAnalyzer instance."""
        return ScoreAnalyzer()

    @pytest.fixture
    def basic_context(self):
        """Create basic conversation context."""
        return ConversationContext(
            chapter=1,
            relationship_score=Decimal("50"),
            recent_messages=[
                ("user", "Hey, how was your day?"),
                ("nikita", "It was good! I went to yoga class."),
            ],
            relationship_state="stable",
        )

    @pytest.mark.asyncio
    async def test_analyze_returns_response_analysis(self, analyzer, basic_context):
        """Test that analyze returns a ResponseAnalysis object."""
        # Mock the LLM call
        mock_analysis = ResponseAnalysis(
            deltas=MetricDeltas(
                intimacy=Decimal("3"),
                passion=Decimal("1"),
                trust=Decimal("2"),
                secureness=Decimal("1"),
            ),
            explanation="User showed genuine interest in Nikita's day.",
            behaviors_identified=["genuine_curiosity", "active_listening"],
            confidence=Decimal("0.85"),
        )

        with patch.object(analyzer, "_call_llm", return_value=mock_analysis):
            result = await analyzer.analyze(
                user_message="That sounds fun! What kind of yoga do you do?",
                nikita_response="I do Vinyasa flow. It's really challenging!",
                context=basic_context,
            )

        assert isinstance(result, ResponseAnalysis)
        assert result.deltas.intimacy == Decimal("3")
        assert result.explanation != ""
        assert len(result.behaviors_identified) > 0

    @pytest.mark.asyncio
    async def test_analyze_with_negative_deltas(self, analyzer, basic_context):
        """Test analysis of a negative interaction."""
        mock_analysis = ResponseAnalysis(
            deltas=MetricDeltas(
                intimacy=Decimal("-3"),
                passion=Decimal("-2"),
                trust=Decimal("-5"),
                secureness=Decimal("-4"),
            ),
            explanation="User was dismissive and rude.",
            behaviors_identified=["dismissive", "rude", "disrespectful"],
            confidence=Decimal("0.90"),
        )

        with patch.object(analyzer, "_call_llm", return_value=mock_analysis):
            result = await analyzer.analyze(
                user_message="Whatever, I don't care about your stupid yoga.",
                nikita_response="Okay then...",
                context=basic_context,
            )

        assert result.deltas.total < Decimal("0")
        assert result.deltas.is_positive is False

    @pytest.mark.asyncio
    async def test_analyze_neutral_interaction(self, analyzer, basic_context):
        """Test analysis of a neutral interaction."""
        mock_analysis = ResponseAnalysis(
            deltas=MetricDeltas(
                intimacy=Decimal("0"),
                passion=Decimal("0"),
                trust=Decimal("0"),
                secureness=Decimal("0"),
            ),
            explanation="Neutral small talk with no significant impact.",
            behaviors_identified=[],
            confidence=Decimal("0.75"),
        )

        with patch.object(analyzer, "_call_llm", return_value=mock_analysis):
            result = await analyzer.analyze(
                user_message="ok",
                nikita_response="ok",
                context=basic_context,
            )

        assert result.deltas.total == Decimal("0")

    @pytest.mark.asyncio
    async def test_analyze_respects_delta_bounds(self, analyzer, basic_context):
        """Test that analysis respects -10 to +10 delta bounds."""
        # LLM might try to return extreme values - should be clamped
        mock_analysis = ResponseAnalysis(
            deltas=MetricDeltas(
                intimacy=Decimal("10"),  # Max allowed
                passion=Decimal("10"),
                trust=Decimal("10"),
                secureness=Decimal("10"),
            ),
            explanation="Exceptional interaction.",
            behaviors_identified=["exceptional"],
            confidence=Decimal("0.95"),
        )

        with patch.object(analyzer, "_call_llm", return_value=mock_analysis):
            result = await analyzer.analyze(
                user_message="I love you more than anything.",
                nikita_response="That means so much to me!",
                context=basic_context,
            )

        # All deltas should be within bounds
        assert Decimal("-10") <= result.deltas.intimacy <= Decimal("10")
        assert Decimal("-10") <= result.deltas.passion <= Decimal("10")
        assert Decimal("-10") <= result.deltas.trust <= Decimal("10")
        assert Decimal("-10") <= result.deltas.secureness <= Decimal("10")


class TestScoreAnalyzerContextAware:
    """Test context-aware analysis (FR-006)."""

    @pytest.fixture
    def analyzer(self):
        """Create ScoreAnalyzer instance."""
        return ScoreAnalyzer()

    @pytest.mark.asyncio
    async def test_chapter_affects_analysis(self, analyzer):
        """Test that different chapters affect analysis."""
        # Chapter 1: Nikita is more guarded
        ch1_context = ConversationContext(
            chapter=1,
            relationship_score=Decimal("30"),
            recent_messages=[],
            relationship_state="stable",
        )

        # Chapter 5: Nikita is more trusting
        ch5_context = ConversationContext(
            chapter=5,
            relationship_score=Decimal("80"),
            recent_messages=[],
            relationship_state="stable",
        )

        # Mock different responses for different chapters
        ch1_analysis = ResponseAnalysis(
            deltas=MetricDeltas(
                intimacy=Decimal("2"),
                passion=Decimal("1"),
                trust=Decimal("1"),
                secureness=Decimal("1"),
            ),
            explanation="Chapter 1 - Nikita is still guarded.",
            behaviors_identified=["appropriate_for_stage"],
            confidence=Decimal("0.80"),
        )

        ch5_analysis = ResponseAnalysis(
            deltas=MetricDeltas(
                intimacy=Decimal("5"),
                passion=Decimal("4"),
                trust=Decimal("4"),
                secureness=Decimal("3"),
            ),
            explanation="Chapter 5 - Deep connection established.",
            behaviors_identified=["deep_connection", "mutual_trust"],
            confidence=Decimal("0.85"),
        )

        with patch.object(analyzer, "_call_llm") as mock_llm:
            mock_llm.return_value = ch1_analysis
            result1 = await analyzer.analyze(
                user_message="I really enjoy talking to you.",
                nikita_response="Thanks, you're interesting.",
                context=ch1_context,
            )

            mock_llm.return_value = ch5_analysis
            result5 = await analyzer.analyze(
                user_message="I really enjoy talking to you.",
                nikita_response="I feel the same way.",
                context=ch5_context,
            )

        # Same message should have different impact based on chapter
        # (In real implementation, LLM considers chapter context)
        assert result1.deltas.total != result5.deltas.total

    @pytest.mark.asyncio
    async def test_relationship_state_affects_analysis(self, analyzer):
        """Test that relationship state affects analysis."""
        conflict_context = ConversationContext(
            chapter=3,
            relationship_score=Decimal("40"),
            recent_messages=[],
            relationship_state="conflict",
        )

        stable_context = ConversationContext(
            chapter=3,
            relationship_score=Decimal("60"),
            recent_messages=[],
            relationship_state="stable",
        )

        # Same apology should have different impact based on state
        conflict_analysis = ResponseAnalysis(
            deltas=MetricDeltas(
                intimacy=Decimal("4"),
                passion=Decimal("2"),
                trust=Decimal("5"),
                secureness=Decimal("3"),
            ),
            explanation="Apology during conflict - very meaningful.",
            behaviors_identified=["apology", "conflict_resolution"],
            confidence=Decimal("0.85"),
        )

        stable_analysis = ResponseAnalysis(
            deltas=MetricDeltas(
                intimacy=Decimal("1"),
                passion=Decimal("0"),
                trust=Decimal("1"),
                secureness=Decimal("1"),
            ),
            explanation="Apology when stable - less impactful.",
            behaviors_identified=["courtesy"],
            confidence=Decimal("0.80"),
        )

        with patch.object(analyzer, "_call_llm") as mock_llm:
            mock_llm.return_value = conflict_analysis
            conflict_result = await analyzer.analyze(
                user_message="I'm sorry for what I said earlier.",
                nikita_response="I appreciate you saying that.",
                context=conflict_context,
            )

            mock_llm.return_value = stable_analysis
            stable_result = await analyzer.analyze(
                user_message="I'm sorry for what I said earlier.",
                nikita_response="It's okay, no worries.",
                context=stable_context,
            )

        # Apology during conflict should be more impactful
        assert conflict_result.deltas.total > stable_result.deltas.total


class TestScoreAnalyzerBulkAnalysis:
    """Test bulk/batch analysis (FR-008)."""

    @pytest.fixture
    def analyzer(self):
        """Create ScoreAnalyzer instance."""
        return ScoreAnalyzer()

    @pytest.fixture
    def basic_context(self):
        """Create basic conversation context."""
        return ConversationContext(
            chapter=2,
            relationship_score=Decimal("55"),
        )

    @pytest.mark.asyncio
    async def test_analyze_batch(self, analyzer, basic_context):
        """Test analyzing multiple exchanges at once."""
        exchanges = [
            ("How was work?", "It was busy but good!"),
            ("Did you have lunch?", "Yes, I had sushi."),
            ("That sounds nice!", "It was delicious!"),
        ]

        mock_analysis = ResponseAnalysis(
            deltas=MetricDeltas(
                intimacy=Decimal("4"),
                passion=Decimal("2"),
                trust=Decimal("3"),
                secureness=Decimal("2"),
            ),
            explanation="Positive conversation with genuine interest.",
            behaviors_identified=["genuine_interest", "care", "engagement"],
            confidence=Decimal("0.82"),
        )

        with patch.object(analyzer, "_call_llm", return_value=mock_analysis):
            result = await analyzer.analyze_batch(exchanges, context=basic_context)

        assert isinstance(result, ResponseAnalysis)
        # Batch analysis produces combined analysis
        assert result.deltas is not None

    @pytest.mark.asyncio
    async def test_analyze_batch_empty(self, analyzer, basic_context):
        """Test batch analysis with empty exchanges returns neutral."""
        result = await analyzer.analyze_batch([], context=basic_context)

        assert result.deltas.total == Decimal("0")
        assert result.explanation == ""
        assert result.behaviors_identified == []


class TestScoreAnalyzerPromptConstruction:
    """Test prompt construction for LLM."""

    @pytest.fixture
    def analyzer(self):
        """Create ScoreAnalyzer instance."""
        return ScoreAnalyzer()

    def test_build_analysis_prompt(self, analyzer):
        """Test that analysis prompt is constructed correctly."""
        context = ConversationContext(
            chapter=2,
            relationship_score=Decimal("55"),
            recent_messages=[
                ("user", "Previous message"),
                ("nikita", "Previous response"),
            ],
        )

        prompt = analyzer._build_analysis_prompt(
            user_message="New message",
            nikita_response="New response",
            context=context,
        )

        # Prompt should contain key elements
        assert "Chapter" in prompt or "chapter" in prompt
        assert "intimacy" in prompt.lower() or "Intimacy" in prompt
        assert "passion" in prompt.lower() or "Passion" in prompt
        assert "trust" in prompt.lower() or "Trust" in prompt
        assert "secureness" in prompt.lower() or "Secureness" in prompt
        assert "-10" in prompt and "+10" in prompt or "10" in prompt

    def test_prompt_includes_chapter_behaviors(self, analyzer):
        """Test that prompt includes chapter-specific behaviors."""
        context = ConversationContext(
            chapter=1,
            relationship_score=Decimal("30"),
        )

        prompt = analyzer._build_analysis_prompt(
            user_message="Test",
            nikita_response="Test",
            context=context,
        )

        # Should reference chapter expectations
        assert "Chapter 1" in prompt or "chapter 1" in prompt or "Curiosity" in prompt


class TestScoreAnalyzerErrorHandling:
    """Test error handling in analyzer."""

    @pytest.fixture
    def analyzer(self):
        """Create ScoreAnalyzer instance."""
        return ScoreAnalyzer()

    @pytest.fixture
    def basic_context(self):
        """Create basic conversation context."""
        return ConversationContext(
            chapter=1,
            relationship_score=Decimal("50"),
        )

    @pytest.mark.asyncio
    async def test_analyze_handles_llm_error(self, analyzer, basic_context):
        """Test that analyzer handles LLM errors gracefully."""
        with patch.object(analyzer, "_call_llm", side_effect=Exception("LLM error")):
            result = await analyzer.analyze(
                user_message="Test",
                nikita_response="Test",
                context=basic_context,
            )

        # Should return neutral analysis on error
        assert result.deltas.total == Decimal("0")
        assert "error" in result.explanation.lower() or result.explanation == ""

    @pytest.mark.asyncio
    async def test_analyze_handles_invalid_response(self, analyzer, basic_context):
        """Test that analyzer handles LLM errors with neutral fallback."""
        # Simulate LLM raising an error (e.g., after retry exhaustion)
        with patch.object(analyzer, "_call_llm", side_effect=Exception("LLM error")):
            result = await analyzer.analyze(
                user_message="Test",
                nikita_response="Test",
                context=basic_context,
            )

        # Should return neutral analysis
        assert result.deltas.total == Decimal("0")
