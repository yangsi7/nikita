"""Fact extraction module for Nikita text agent.

This module implements logic for extracting facts about the user
from conversation turns. Facts are identified using LLM analysis
and categorized as explicit (directly stated) or implicit (inferred).

Extracted facts are stored in the user's memory graph for future reference.
"""

from dataclasses import dataclass, field
from typing import Literal, Optional


@dataclass
class ExtractedFact:
    """
    A fact extracted from a conversation turn.

    Attributes:
        fact: The fact statement about the user
        confidence: How confident we are in this fact (0-1)
        source: The message text this fact was extracted from
        fact_type: Whether this was explicit or implicit
    """

    fact: str
    confidence: float
    source: str
    fact_type: Literal["explicit", "implicit"] = "explicit"


# Prompt template for LLM fact extraction
FACT_EXTRACTION_PROMPT = """Analyze this conversation turn and extract facts about the user.

User message: "{user_message}"
Nikita's response: "{nikita_response}"

Already known facts about user (do NOT re-extract these):
{existing_facts_list}

Extract:
1. EXPLICIT facts: Things the user directly states (e.g., "I work at Tesla" → "User works at Tesla")
   - High confidence (0.85-0.95)
2. IMPLICIT facts: Things inferred from context (e.g., "Work has been crazy" → "User may be stressed")
   - Lower confidence (0.5-0.75)

Return a JSON array of extracted facts. Each fact should have:
- fact: string (the fact statement, starting with "User...")
- confidence: float (0-1)
- source: string (the exact text this was extracted from)
- fact_type: "explicit" or "implicit"

If no new facts can be extracted, return an empty array [].

Do NOT extract:
- Facts already in the existing facts list
- Generic greetings or small talk
- Facts about Nikita (only facts about the USER)

Example output:
[
  {{"fact": "User works at Tesla", "confidence": 0.92, "source": "I work at Tesla", "fact_type": "explicit"}},
  {{"fact": "User may be interested in electric vehicles", "confidence": 0.65, "source": "I work at Tesla", "fact_type": "implicit"}}
]"""


class FactExtractor:
    """
    Extracts facts about the user from conversation turns.

    Uses LLM analysis to identify both explicit facts (directly stated)
    and implicit facts (inferred from context). Deduplicates against
    existing known facts to avoid redundant storage.

    Example usage:
        extractor = FactExtractor()
        facts = await extractor.extract_facts(
            user_message="I work at Tesla as an engineer",
            nikita_response="Electric cars, huh? That's pretty cool.",
            existing_facts=["User lives in California"],
        )
        # Returns list of ExtractedFact objects
    """

    def __init__(self, min_confidence: float = 0.5):
        """
        Initialize the FactExtractor.

        Args:
            min_confidence: Minimum confidence threshold for facts (default 0.5)
        """
        self.min_confidence = min_confidence

    async def extract_facts(
        self,
        user_message: str,
        nikita_response: str,
        existing_facts: list[str],
    ) -> list[ExtractedFact]:
        """
        Extract facts about the user from a conversation turn.

        Analyzes the user's message and Nikita's response to identify
        new facts about the user. Filters out facts that are already known.

        Args:
            user_message: The user's message text
            nikita_response: Nikita's response text
            existing_facts: List of already known facts (for deduplication)

        Returns:
            List of ExtractedFact objects with new facts about the user
        """
        # Get raw facts from LLM
        raw_facts = await self._call_llm_for_extraction(
            user_message, nikita_response, existing_facts
        )

        # Deduplicate against existing facts
        deduplicated = self._deduplicate_facts(raw_facts, existing_facts)

        # Filter by minimum confidence
        filtered = [f for f in deduplicated if f.confidence >= self.min_confidence]

        return filtered

    async def _call_llm_for_extraction(
        self,
        user_message: str,
        nikita_response: str,
        existing_facts: list[str],
    ) -> list[ExtractedFact]:
        """
        Call LLM to extract facts from the conversation.

        NOTE: This method intentionally returns an empty list.
        LLM-based fact extraction is handled by ExtractionStage in the
        post-conversation pipeline (nikita/pipeline/stages/extraction.py),
        which uses Pydantic AI + Claude to extract facts, threads, and thoughts
        after each conversation ends (Spec 042 / post-processing redesign).

        The FactExtractor class is kept for backwards compatibility and testing,
        but no in-conversation LLM call is made here.

        Args:
            user_message: The user's message text
            nikita_response: Nikita's response text
            existing_facts: List of already known facts

        Returns:
            Empty list — extraction handled by ExtractionStage in pipeline.
        """
        return []

    def _deduplicate_facts(
        self,
        new_facts: list[ExtractedFact],
        existing_facts: list[str],
    ) -> list[ExtractedFact]:
        """
        Remove facts that are already known.

        Performs case-insensitive comparison to avoid duplicates.

        Args:
            new_facts: List of newly extracted facts
            existing_facts: List of already known fact strings

        Returns:
            List of facts that are not already known
        """
        # Normalize existing facts for comparison
        normalized_existing = {fact.lower().strip() for fact in existing_facts}

        deduplicated = []
        for fact in new_facts:
            # Check if this fact is already known (case-insensitive)
            if fact.fact.lower().strip() not in normalized_existing:
                deduplicated.append(fact)

        return deduplicated
