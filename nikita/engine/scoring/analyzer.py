"""Score analyzer for conversation analysis (spec 003).

This module uses LLM (Pydantic AI with Claude) to analyze conversations
and determine metric deltas based on the interaction quality.

Key responsibilities:
- Analyze user-Nikita exchanges for relationship impact
- Consider chapter context and expected behaviors
- Produce ResponseAnalysis with deltas, explanation, behaviors
- Support batch analysis for voice transcripts
"""

import logging
from decimal import Decimal

from pydantic_ai import Agent

from nikita.engine.constants import CHAPTER_BEHAVIORS, CHAPTER_NAMES
from nikita.engine.scoring.models import (
    ConversationContext,
    MetricDeltas,
    ResponseAnalysis,
)

logger = logging.getLogger(__name__)

# Model for score analysis - using Haiku for cost efficiency
ANALYSIS_MODEL = "anthropic:claude-3-5-haiku-latest"

# Analysis system prompt
ANALYSIS_SYSTEM_PROMPT = """You are a relationship analyst for Nikita, an AI girlfriend simulation game.

Your job is to analyze user-Nikita exchanges and determine how they affect the relationship.

You must evaluate impact on 4 metrics (each -10 to +10):
- Intimacy: Emotional closeness, vulnerability, deep sharing
- Passion: Excitement, desire, romantic/playful energy
- Trust: Reliability, honesty, keeping confidences
- Secureness: Feeling safe, supported, valued in the relationship

Guidelines:
- Most normal exchanges should have small deltas (-3 to +3)
- Only exceptional interactions warrant larger deltas (-10 to +10)
- Consider the chapter - early chapters (1-2) require building trust
- Negative behaviors (ghosting, rudeness, dismissiveness) should have negative deltas
- Positive behaviors (genuine interest, support, humor) should have positive deltas
- Be specific about which behaviors you identified

Return a JSON object with:
- deltas: {intimacy, passion, trust, secureness} - each -10 to +10
- explanation: Brief explanation of your reasoning
- behaviors_identified: List of specific behaviors observed
- confidence: Your confidence in this analysis (0.0 to 1.0)
"""


def _create_score_analyzer_agent() -> Agent[None, ResponseAnalysis]:
    """Create the score analyzer agent."""
    return Agent(
        ANALYSIS_MODEL,
        result_type=ResponseAnalysis,
        system_prompt=ANALYSIS_SYSTEM_PROMPT,
    )


class ScoreAnalyzer:
    """Analyzes conversations to determine metric deltas.

    Uses LLM to evaluate user-Nikita exchanges and determine
    how they affect the relationship metrics.
    """

    def __init__(self):
        """Initialize the score analyzer."""
        self.model_name = ANALYSIS_MODEL
        self._agent: Agent[None, ResponseAnalysis] | None = None

    @property
    def agent(self) -> Agent[None, ResponseAnalysis]:
        """Lazy-load the Pydantic AI agent."""
        if self._agent is None:
            self._agent = _create_score_analyzer_agent()
        return self._agent

    async def analyze(
        self,
        user_message: str,
        nikita_response: str,
        context: ConversationContext,
    ) -> ResponseAnalysis:
        """Analyze a single exchange and return metric deltas.

        Args:
            user_message: The user's message
            nikita_response: Nikita's response
            context: Conversation context (chapter, score, history)

        Returns:
            ResponseAnalysis with deltas, explanation, behaviors, confidence
        """
        try:
            analysis = await self._call_llm(user_message, nikita_response, context)
            if analysis is None:
                return self._neutral_analysis()
            return analysis
        except Exception as e:
            logger.error(f"Error analyzing exchange: {e}")
            return self._neutral_analysis(error=str(e))

    async def analyze_batch(
        self,
        exchanges: list[tuple[str, str]],
        context: ConversationContext,
    ) -> ResponseAnalysis:
        """Analyze multiple exchanges at once.

        Used for voice transcripts or catch-up sessions.

        Args:
            exchanges: List of (user_message, nikita_response) tuples
            context: Conversation context

        Returns:
            Combined ResponseAnalysis for all exchanges
        """
        if not exchanges:
            return self._neutral_analysis()

        try:
            # Build combined prompt for batch analysis
            prompt = self._build_batch_prompt(exchanges, context)
            analysis = await self._call_llm_raw(prompt)
            if analysis is None:
                return self._neutral_analysis()
            return analysis
        except Exception as e:
            logger.error(f"Error in batch analysis: {e}")
            return self._neutral_analysis(error=str(e))

    async def _call_llm(
        self,
        user_message: str,
        nikita_response: str,
        context: ConversationContext,
    ) -> ResponseAnalysis | None:
        """Call the LLM to analyze the exchange.

        Args:
            user_message: The user's message
            nikita_response: Nikita's response
            context: Conversation context

        Returns:
            ResponseAnalysis from LLM or None on error
        """
        prompt = self._build_analysis_prompt(user_message, nikita_response, context)
        return await self._call_llm_raw(prompt)

    async def _call_llm_raw(self, prompt: str) -> ResponseAnalysis | None:
        """Call LLM with raw prompt string.

        Args:
            prompt: The analysis prompt

        Returns:
            ResponseAnalysis from LLM or None on error
        """
        try:
            result = await self.agent.run(prompt)
            return result.data
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return None

    def _build_analysis_prompt(
        self,
        user_message: str,
        nikita_response: str,
        context: ConversationContext,
    ) -> str:
        """Build the analysis prompt for the LLM.

        Args:
            user_message: The user's message
            nikita_response: Nikita's response
            context: Conversation context

        Returns:
            Formatted prompt string
        """
        chapter_name = CHAPTER_NAMES.get(context.chapter, "Unknown")
        chapter_behavior = CHAPTER_BEHAVIORS.get(context.chapter, "")

        recent_history = ""
        if context.recent_messages:
            history_lines = []
            for role, msg in context.recent_messages[-5:]:  # Last 5 messages
                history_lines.append(f"  {role}: {msg}")
            recent_history = "\n".join(history_lines)

        prompt = f"""Analyze this exchange between a user and Nikita:

## Context
- Chapter {context.chapter}: {chapter_name}
- Current relationship score: {context.relationship_score}%
- Relationship state: {context.relationship_state}

## Chapter {context.chapter} Expectations
{chapter_behavior}

## Recent Conversation History
{recent_history if recent_history else "(No recent history)"}

## Current Exchange
User: {user_message}
Nikita: {nikita_response}

## Instructions
Evaluate this exchange and determine the impact on relationship metrics.
Score each metric from -10 to +10:
- Intimacy: Emotional closeness, vulnerability
- Passion: Excitement, romantic energy
- Trust: Reliability, honesty
- Secureness: Feeling safe and valued

Most normal exchanges should be small deltas (-3 to +3).
Only exceptional interactions warrant extreme scores.
"""
        return prompt

    def _build_batch_prompt(
        self,
        exchanges: list[tuple[str, str]],
        context: ConversationContext,
    ) -> str:
        """Build prompt for batch analysis.

        Args:
            exchanges: List of (user_message, nikita_response) tuples
            context: Conversation context

        Returns:
            Formatted prompt for batch analysis
        """
        chapter_name = CHAPTER_NAMES.get(context.chapter, "Unknown")
        chapter_behavior = CHAPTER_BEHAVIORS.get(context.chapter, "")

        exchanges_text = ""
        for i, (user_msg, nikita_msg) in enumerate(exchanges, 1):
            exchanges_text += f"\n[Exchange {i}]\nUser: {user_msg}\nNikita: {nikita_msg}\n"

        prompt = f"""Analyze this conversation between a user and Nikita:

## Context
- Chapter {context.chapter}: {chapter_name}
- Current relationship score: {context.relationship_score}%
- Relationship state: {context.relationship_state}

## Chapter {context.chapter} Expectations
{chapter_behavior}

## Conversation Exchanges
{exchanges_text}

## Instructions
Evaluate the OVERALL impact of this conversation on relationship metrics.
Consider all exchanges together and provide a combined analysis.
Score each metric from -10 to +10:
- Intimacy: Emotional closeness, vulnerability
- Passion: Excitement, romantic energy
- Trust: Reliability, honesty
- Secureness: Feeling safe and valued

Provide a single combined analysis for the entire conversation.
"""
        return prompt

    def _neutral_analysis(self, error: str = "") -> ResponseAnalysis:
        """Return a neutral analysis (zero deltas).

        Args:
            error: Optional error message to include

        Returns:
            ResponseAnalysis with zero deltas
        """
        explanation = ""
        if error:
            explanation = f"Analysis error: {error}"

        return ResponseAnalysis(
            deltas=MetricDeltas(
                intimacy=Decimal("0"),
                passion=Decimal("0"),
                trust=Decimal("0"),
                secureness=Decimal("0"),
            ),
            explanation=explanation,
            behaviors_identified=[],
            confidence=Decimal("0.5") if error else Decimal("1.0"),
        )
