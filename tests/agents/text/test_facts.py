"""Tests for FactExtractor - TDD for T6.1.

Acceptance Criteria:
- AC-6.1.1: `extract_facts(user_message, nikita_response, existing_facts)` async method
- AC-6.1.2: Uses LLM to identify explicit facts (user states directly)
- AC-6.1.3: Uses LLM to identify implicit facts (inferred from context)
- AC-6.1.4: Returns list[ExtractedFact] with fact, confidence, source
- AC-6.1.5: Avoids extracting already-known facts (deduplication)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

pytestmark = pytest.mark.asyncio(loop_scope="function")


class TestFactsModule:
    """Tests for facts module structure."""

    def test_facts_module_importable(self):
        """Facts module should be importable."""
        from nikita.agents.text import facts

        assert hasattr(facts, "FactExtractor")
        assert hasattr(facts, "ExtractedFact")

    def test_extracted_fact_dataclass(self):
        """ExtractedFact should be a dataclass with required fields."""
        from nikita.agents.text.facts import ExtractedFact

        fact = ExtractedFact(
            fact="User works at Tesla",
            confidence=0.9,
            source="I work at Tesla",
        )

        assert fact.fact == "User works at Tesla"
        assert fact.confidence == 0.9
        assert fact.source == "I work at Tesla"

    def test_extracted_fact_has_fact_type(self):
        """ExtractedFact should have fact_type field (explicit/implicit)."""
        from nikita.agents.text.facts import ExtractedFact

        explicit = ExtractedFact(
            fact="User is an engineer",
            confidence=0.95,
            source="I'm an engineer",
            fact_type="explicit",
        )

        implicit = ExtractedFact(
            fact="User may be stressed about job",
            confidence=0.7,
            source="Work has been crazy lately",
            fact_type="implicit",
        )

        assert explicit.fact_type == "explicit"
        assert implicit.fact_type == "implicit"


class TestFactExtractor:
    """Tests for FactExtractor class."""

    def test_fact_extractor_class_exists(self):
        """FactExtractor class should exist."""
        from nikita.agents.text.facts import FactExtractor

        assert callable(FactExtractor)

    def test_ac_6_1_1_extract_facts_method_exists(self):
        """AC-6.1.1: extract_facts async method should exist."""
        from nikita.agents.text.facts import FactExtractor
        import inspect

        extractor = FactExtractor()

        assert hasattr(extractor, "extract_facts")
        assert callable(extractor.extract_facts)
        assert inspect.iscoroutinefunction(extractor.extract_facts)

    def test_extract_facts_signature(self):
        """extract_facts should accept user_message, nikita_response, existing_facts."""
        from nikita.agents.text.facts import FactExtractor
        import inspect

        extractor = FactExtractor()
        sig = inspect.signature(extractor.extract_facts)
        params = list(sig.parameters.keys())

        assert "user_message" in params
        assert "nikita_response" in params
        assert "existing_facts" in params

    @pytest.mark.asyncio
    async def test_ac_6_1_4_returns_list_of_extracted_facts(self):
        """AC-6.1.4: Should return list[ExtractedFact]."""
        from nikita.agents.text.facts import FactExtractor, ExtractedFact

        extractor = FactExtractor()

        # Mock the LLM call
        mock_result = [
            ExtractedFact(
                fact="User works at Tesla",
                confidence=0.9,
                source="I work at Tesla",
                fact_type="explicit",
            )
        ]

        with patch.object(extractor, "_call_llm_for_extraction", new=AsyncMock(return_value=mock_result)):
            result = await extractor.extract_facts(
                user_message="I work at Tesla",
                nikita_response="Oh cool, electric cars?",
                existing_facts=[],
            )

        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(f, ExtractedFact) for f in result)

    @pytest.mark.asyncio
    async def test_extracted_fact_has_required_fields(self):
        """Each ExtractedFact should have fact, confidence, source."""
        from nikita.agents.text.facts import FactExtractor, ExtractedFact

        extractor = FactExtractor()

        mock_result = [
            ExtractedFact(
                fact="User is an engineer",
                confidence=0.85,
                source="I'm an engineer at a startup",
                fact_type="explicit",
            )
        ]

        with patch.object(extractor, "_call_llm_for_extraction", new=AsyncMock(return_value=mock_result)):
            result = await extractor.extract_facts(
                user_message="I'm an engineer at a startup",
                nikita_response="Nice, what kind of startup?",
                existing_facts=[],
            )

        fact = result[0]
        assert hasattr(fact, "fact")
        assert hasattr(fact, "confidence")
        assert hasattr(fact, "source")


class TestExplicitFacts:
    """Tests for explicit fact extraction (AC-6.1.2)."""

    @pytest.mark.asyncio
    async def test_ac_6_1_2_extracts_explicit_facts(self):
        """AC-6.1.2: Should identify explicit facts user states directly."""
        from nikita.agents.text.facts import FactExtractor, ExtractedFact

        extractor = FactExtractor()

        mock_result = [
            ExtractedFact(
                fact="User works at Tesla",
                confidence=0.95,
                source="I work at Tesla as an engineer",
                fact_type="explicit",
            ),
            ExtractedFact(
                fact="User is an engineer",
                confidence=0.95,
                source="I work at Tesla as an engineer",
                fact_type="explicit",
            ),
        ]

        with patch.object(extractor, "_call_llm_for_extraction", new=AsyncMock(return_value=mock_result)):
            result = await extractor.extract_facts(
                user_message="I work at Tesla as an engineer",
                nikita_response="Electric cars, huh?",
                existing_facts=[],
            )

        explicit_facts = [f for f in result if f.fact_type == "explicit"]
        assert len(explicit_facts) >= 1

    @pytest.mark.asyncio
    async def test_explicit_facts_have_high_confidence(self):
        """Explicit facts should have high confidence (>0.8)."""
        from nikita.agents.text.facts import FactExtractor, ExtractedFact

        extractor = FactExtractor()

        mock_result = [
            ExtractedFact(
                fact="User's name is John",
                confidence=0.95,
                source="My name is John",
                fact_type="explicit",
            ),
        ]

        with patch.object(extractor, "_call_llm_for_extraction", new=AsyncMock(return_value=mock_result)):
            result = await extractor.extract_facts(
                user_message="My name is John",
                nikita_response="Hey John",
                existing_facts=[],
            )

        explicit_facts = [f for f in result if f.fact_type == "explicit"]
        for fact in explicit_facts:
            assert fact.confidence > 0.8


class TestImplicitFacts:
    """Tests for implicit fact extraction (AC-6.1.3)."""

    @pytest.mark.asyncio
    async def test_ac_6_1_3_extracts_implicit_facts(self):
        """AC-6.1.3: Should identify implicit facts inferred from context."""
        from nikita.agents.text.facts import FactExtractor, ExtractedFact

        extractor = FactExtractor()

        mock_result = [
            ExtractedFact(
                fact="User may be experiencing work stress",
                confidence=0.7,
                source="Work has been absolutely insane lately",
                fact_type="implicit",
            ),
        ]

        with patch.object(extractor, "_call_llm_for_extraction", new=AsyncMock(return_value=mock_result)):
            result = await extractor.extract_facts(
                user_message="Work has been absolutely insane lately",
                nikita_response="Tell me about it",
                existing_facts=[],
            )

        implicit_facts = [f for f in result if f.fact_type == "implicit"]
        assert len(implicit_facts) >= 1

    @pytest.mark.asyncio
    async def test_implicit_facts_have_lower_confidence(self):
        """Implicit facts should have lower confidence (<0.9)."""
        from nikita.agents.text.facts import FactExtractor, ExtractedFact

        extractor = FactExtractor()

        mock_result = [
            ExtractedFact(
                fact="User may be tired",
                confidence=0.65,
                source="I've been pulling all-nighters",
                fact_type="implicit",
            ),
        ]

        with patch.object(extractor, "_call_llm_for_extraction", new=AsyncMock(return_value=mock_result)):
            result = await extractor.extract_facts(
                user_message="I've been pulling all-nighters",
                nikita_response="Get some sleep",
                existing_facts=[],
            )

        implicit_facts = [f for f in result if f.fact_type == "implicit"]
        for fact in implicit_facts:
            assert fact.confidence < 0.9


class TestFactDeduplication:
    """Tests for fact deduplication (AC-6.1.5)."""

    @pytest.mark.asyncio
    async def test_ac_6_1_5_avoids_extracting_known_facts(self):
        """AC-6.1.5: Should not extract facts that already exist."""
        from nikita.agents.text.facts import FactExtractor, ExtractedFact

        extractor = FactExtractor()

        # Existing fact about Tesla
        existing = ["User works at Tesla"]

        # Mock LLM returning both new and existing facts
        mock_result = [
            ExtractedFact(
                fact="User works at Tesla",  # Already known
                confidence=0.9,
                source="Tesla is great",
                fact_type="explicit",
            ),
            ExtractedFact(
                fact="User enjoys their job",  # New fact
                confidence=0.75,
                source="Tesla is great, I love it",
                fact_type="implicit",
            ),
        ]

        with patch.object(extractor, "_call_llm_for_extraction", new=AsyncMock(return_value=mock_result)):
            result = await extractor.extract_facts(
                user_message="Tesla is great, I love it",
                nikita_response="Nice",
                existing_facts=existing,
            )

        # Should only include the new fact, not the known one
        facts_text = [f.fact for f in result]
        assert "User works at Tesla" not in facts_text
        assert any("enjoy" in f.lower() or "job" in f.lower() for f in facts_text)

    @pytest.mark.asyncio
    async def test_deduplication_is_case_insensitive(self):
        """Deduplication should work regardless of case."""
        from nikita.agents.text.facts import FactExtractor, ExtractedFact

        extractor = FactExtractor()

        existing = ["user works at tesla"]  # lowercase

        mock_result = [
            ExtractedFact(
                fact="User Works at Tesla",  # Different case
                confidence=0.9,
                source="message",
                fact_type="explicit",
            ),
        ]

        with patch.object(extractor, "_call_llm_for_extraction", new=AsyncMock(return_value=mock_result)):
            result = await extractor.extract_facts(
                user_message="Tesla is great",
                nikita_response="Nice",
                existing_facts=existing,
            )

        # Should be filtered out due to case-insensitive matching
        assert len(result) == 0


class TestEmptyResults:
    """Tests for cases with no facts to extract."""

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_facts(self):
        """Should return empty list when no facts found."""
        from nikita.agents.text.facts import FactExtractor

        extractor = FactExtractor()

        with patch.object(extractor, "_call_llm_for_extraction", new=AsyncMock(return_value=[])):
            result = await extractor.extract_facts(
                user_message="hi",
                nikita_response="hey",
                existing_facts=[],
            )

        assert result == []

    @pytest.mark.asyncio
    async def test_handles_small_talk_gracefully(self):
        """Small talk should not generate facts."""
        from nikita.agents.text.facts import FactExtractor

        extractor = FactExtractor()

        with patch.object(extractor, "_call_llm_for_extraction", new=AsyncMock(return_value=[])):
            result = await extractor.extract_facts(
                user_message="Hey, how are you?",
                nikita_response="I'm fine, you?",
                existing_facts=[],
            )

        # Small talk typically has no extractable facts
        assert isinstance(result, list)
