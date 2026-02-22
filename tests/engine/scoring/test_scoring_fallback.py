"""Tests for LLM scoring fallback — Spec 105 Story 3.

Graceful degradation when LLM scoring fails.
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, patch, MagicMock
from nikita.engine.scoring.models import ConversationContext


def _make_context() -> ConversationContext:
    """Create a test conversation context."""
    return ConversationContext(
        chapter=2,
        relationship_score=Decimal("55.0"),
        relationship_state="invested",
        recent_messages=[],
    )


@pytest.mark.asyncio
async def test_zero_delta_on_llm_error():
    """analyze() returns zero deltas on LLM exception."""
    from nikita.engine.scoring.analyzer import ScoreAnalyzer

    analyzer = ScoreAnalyzer()

    # Make _call_llm raise an exception
    with patch.object(analyzer, "_call_llm", side_effect=Exception("API timeout")):
        result = await analyzer.analyze("hello", "hi there", _make_context())

    # All deltas should be zero
    assert result.deltas.intimacy == Decimal("0")
    assert result.deltas.passion == Decimal("0")
    assert result.deltas.trust == Decimal("0")
    assert result.deltas.secureness == Decimal("0")


@pytest.mark.asyncio
async def test_fallback_confidence_zero():
    """Fallback result has confidence=0.0 and warning logged."""
    from nikita.engine.scoring.analyzer import ScoreAnalyzer

    analyzer = ScoreAnalyzer()

    with patch.object(analyzer, "_call_llm", side_effect=Exception("LLM down")):
        with patch("nikita.engine.scoring.analyzer.logger") as mock_logger:
            result = await analyzer.analyze("hello", "hi there", _make_context())

    assert result.confidence == Decimal("0.0")
    # Warning should be logged
    mock_logger.warning.assert_called()


@pytest.mark.asyncio
async def test_error_counter_increments():
    """Error counter increments on LLM failure."""
    from nikita.engine.scoring.analyzer import ScoreAnalyzer, get_scoring_error_count, _scoring_errors

    # Reset counter
    _scoring_errors["count"] = 0

    analyzer = ScoreAnalyzer()

    with patch.object(analyzer, "_call_llm", side_effect=Exception("fail")):
        await analyzer.analyze("a", "b", _make_context())
        await analyzer.analyze("c", "d", _make_context())

    assert get_scoring_error_count() >= 2
