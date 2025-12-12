"""
Unit Tests for ViceAnalyzer (T008, T011)

Tests for:
- AC-FR001-001: Given user makes dark joke, When analyzed, Then dark_humor detected
- AC-FR002-001: Given user writes long enthusiastic reply about risk, Then risk_taking signal logged

TDD: Write tests FIRST, verify they fail, then implement.
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


class TestViceAnalyzerAnalyzeExchange:
    """T008, T011: ViceAnalyzer.analyze_exchange() tests."""

    @pytest.mark.asyncio
    async def test_ac_fr001_001_dark_humor_detection(self):
        """AC-FR001-001: Given user makes dark joke, When analyzed, Then dark_humor detected."""
        from nikita.engine.vice.analyzer import ViceAnalyzer
        from nikita.config.enums import ViceCategory

        analyzer = ViceAnalyzer()

        # Mock LLM response
        with patch.object(analyzer, '_analyze_with_llm') as mock_llm:
            mock_llm.return_value = {
                "signals": [
                    {
                        "category": "dark_humor",
                        "confidence": 0.85,
                        "evidence": "User made self-deprecating joke about death",
                        "is_positive": True,
                    }
                ]
            }

            result = await analyzer.analyze_exchange(
                user_message="At least when I die, I won't have to pay rent anymore lol",
                nikita_response="That's... morbidly funny",
                conversation_id=uuid4(),
            )

            assert len(result.signals) == 1
            assert result.signals[0].category == ViceCategory.DARK_HUMOR
            assert result.signals[0].confidence >= Decimal("0.80")
            assert result.signals[0].is_positive is True

    @pytest.mark.asyncio
    async def test_ac_fr002_001_risk_taking_long_enthusiastic_reply(self):
        """AC-FR002-001: Given user writes long enthusiastic reply about risk, Then risk_taking signal logged."""
        from nikita.engine.vice.analyzer import ViceAnalyzer
        from nikita.config.enums import ViceCategory

        analyzer = ViceAnalyzer()

        with patch.object(analyzer, '_analyze_with_llm') as mock_llm:
            mock_llm.return_value = {
                "signals": [
                    {
                        "category": "risk_taking",
                        "confidence": 0.90,
                        "evidence": "User wrote enthusiastically about skydiving experience with many details",
                        "is_positive": True,
                    }
                ]
            }

            result = await analyzer.analyze_exchange(
                user_message=(
                    "Oh my god, have you ever been skydiving? I went last weekend "
                    "and it was absolutely incredible! The rush you get when you "
                    "jump out of the plane is unlike anything else. I'm already "
                    "planning my next jump - maybe somewhere more extreme!"
                ),
                nikita_response="Sounds thrilling!",
                conversation_id=uuid4(),
            )

            assert len(result.signals) >= 1
            risk_signal = next(
                (s for s in result.signals if s.category == ViceCategory.RISK_TAKING),
                None
            )
            assert risk_signal is not None
            assert risk_signal.confidence >= Decimal("0.70")
            assert risk_signal.is_positive is True

    @pytest.mark.asyncio
    async def test_ac_t011_3_returns_empty_signals_no_vices(self):
        """AC-T011.3: Returns empty signals list if no vices detected."""
        from nikita.engine.vice.analyzer import ViceAnalyzer

        analyzer = ViceAnalyzer()

        with patch.object(analyzer, '_analyze_with_llm') as mock_llm:
            mock_llm.return_value = {"signals": []}

            result = await analyzer.analyze_exchange(
                user_message="What's the weather like today?",
                nikita_response="It's sunny!",
                conversation_id=uuid4(),
            )

            assert result.signals == []
            assert not result.has_signals

    @pytest.mark.asyncio
    async def test_ac_t011_4_detects_rejection_signals(self):
        """AC-T011.4: Detects rejection signals (short replies, topic changes)."""
        from nikita.engine.vice.analyzer import ViceAnalyzer
        from nikita.config.enums import ViceCategory

        analyzer = ViceAnalyzer()

        with patch.object(analyzer, '_analyze_with_llm') as mock_llm:
            mock_llm.return_value = {
                "signals": [
                    {
                        "category": "dark_humor",
                        "confidence": 0.75,
                        "evidence": "User responded negatively to morbid joke",
                        "is_positive": False,  # Rejection signal
                    }
                ]
            }

            result = await analyzer.analyze_exchange(
                user_message="That's not funny at all.",
                nikita_response="Sorry, I thought it was clever",
                conversation_id=uuid4(),
            )

            assert len(result.signals) == 1
            assert result.signals[0].category == ViceCategory.DARK_HUMOR
            assert result.signals[0].is_positive is False
            assert result.rejection_count == 1

    @pytest.mark.asyncio
    async def test_multiple_vice_signals_detected(self):
        """Multiple vice signals can be detected in one exchange."""
        from nikita.engine.vice.analyzer import ViceAnalyzer
        from nikita.config.enums import ViceCategory

        analyzer = ViceAnalyzer()

        with patch.object(analyzer, '_analyze_with_llm') as mock_llm:
            mock_llm.return_value = {
                "signals": [
                    {
                        "category": "intellectual_dominance",
                        "confidence": 0.80,
                        "evidence": "User corrected and showed knowledge",
                        "is_positive": True,
                    },
                    {
                        "category": "dark_humor",
                        "confidence": 0.65,
                        "evidence": "Added dark joke at the end",
                        "is_positive": True,
                    },
                ]
            }

            result = await analyzer.analyze_exchange(
                user_message="Actually, that's not quite right. Let me explain...",
                nikita_response="Oh really?",
                conversation_id=uuid4(),
            )

            assert len(result.signals) == 2
            categories = [s.category for s in result.signals]
            assert ViceCategory.INTELLECTUAL_DOMINANCE in categories
            assert ViceCategory.DARK_HUMOR in categories


class TestViceAnalyzerAllCategories:
    """Test detection for all 8 vice categories."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("category,evidence", [
        ("intellectual_dominance", "User demonstrated expert knowledge"),
        ("risk_taking", "User mentioned dangerous activity excitement"),
        ("substances", "User discussed alcohol openly"),
        ("sexuality", "User made flirtatious comment"),
        ("emotional_intensity", "User shared deep emotional experience"),
        ("rule_breaking", "User expressed anti-authority sentiment"),
        ("dark_humor", "User made morbid joke"),
        ("vulnerability", "User shared personal fear"),
    ])
    async def test_detects_all_8_categories(self, category, evidence):
        """All 8 vice categories can be detected."""
        from nikita.engine.vice.analyzer import ViceAnalyzer
        from nikita.config.enums import ViceCategory

        analyzer = ViceAnalyzer()

        with patch.object(analyzer, '_analyze_with_llm') as mock_llm:
            mock_llm.return_value = {
                "signals": [
                    {
                        "category": category,
                        "confidence": 0.75,
                        "evidence": evidence,
                        "is_positive": True,
                    }
                ]
            }

            result = await analyzer.analyze_exchange(
                user_message="Test message",
                nikita_response="Test response",
                conversation_id=uuid4(),
            )

            assert len(result.signals) == 1
            assert result.signals[0].category == ViceCategory(category)


class TestViceAnalyzerContext:
    """Test analyzer context usage."""

    @pytest.mark.asyncio
    async def test_conversation_id_traceability(self):
        """Analysis result includes conversation ID for tracing."""
        from nikita.engine.vice.analyzer import ViceAnalyzer

        analyzer = ViceAnalyzer()
        conv_id = uuid4()

        with patch.object(analyzer, '_analyze_with_llm') as mock_llm:
            mock_llm.return_value = {"signals": []}

            result = await analyzer.analyze_exchange(
                user_message="Hello",
                nikita_response="Hi!",
                conversation_id=conv_id,
            )

            assert result.conversation_id == conv_id

    @pytest.mark.asyncio
    async def test_analyzed_at_timestamp_set(self):
        """Analysis result has timestamp."""
        from nikita.engine.vice.analyzer import ViceAnalyzer

        analyzer = ViceAnalyzer()
        before = datetime.now(timezone.utc)

        with patch.object(analyzer, '_analyze_with_llm') as mock_llm:
            mock_llm.return_value = {"signals": []}

            result = await analyzer.analyze_exchange(
                user_message="Hello",
                nikita_response="Hi!",
                conversation_id=uuid4(),
            )

            after = datetime.now(timezone.utc)
            assert before <= result.analyzed_at <= after
