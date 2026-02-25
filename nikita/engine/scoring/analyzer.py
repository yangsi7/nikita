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
from nikita.config.models import Models

ANALYSIS_MODEL = Models.haiku()

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

## Four Horsemen Detection (Gottman)
Also detect if any of Gottman's Four Horsemen are present in the user's message:
- horseman:criticism — Attacking character rather than complaining about specific behavior (e.g., "You never listen" vs "I felt unheard when...")
- horseman:contempt — Superiority, mockery, sarcasm, eye-rolling language, name-calling, disgust (e.g., "That's pathetic", "You're so dumb")
- horseman:defensiveness — Counter-attacking, whining, playing victim, refusing responsibility (e.g., "It's not my fault", "Yeah but YOU...")
- horseman:stonewalling — Withdrawal, one-word responses, complete disengagement, shutting down (e.g., "k", "whatever", "fine")

If detected, include the horseman tag in behaviors_identified using the prefix format: "horseman:criticism", "horseman:contempt", etc. Only tag genuine instances — normal short replies or mild disagreement are NOT horsemen.

## Repair Attempt Detection
IMPORTANT: Independently evaluate the USER'S message only (ignore Nikita's response tone) for repair attempts.
A repair attempt is when the user tries to de-escalate, reconnect, or mend the relationship. Signals include:
- Apology language ("I'm sorry", "my bad", "I shouldn't have said that")
- Emotional openness ("I feel bad about earlier", "I miss you", "I was wrong")
- Accountability ("That was unfair of me", "I overreacted")
- Reaching out after silence ("Hey, I've been thinking about us")
- Humor to defuse tension (genuine, not sarcastic)

If a repair attempt is detected, set repair_attempt_detected=true and rate repair_quality:
- "excellent": Genuine accountability + emotional vulnerability + specific acknowledgment
- "good": Clear apology or emotional openness with some specificity
- "adequate": Basic attempt to reconnect or de-escalate, even if vague

Do NOT flag as repair: sarcastic "apologies", manipulation ("I'll leave then"), or conditional apologies ("sorry IF you were offended"). These are NOT genuine repairs.

## Vulnerability Exchange Detection (Spec 058)
Detect if a vulnerability exchange occurred in this interaction:
- Nikita shared something vulnerable (fear, insecurity, personal struggle, emotional truth)
- Player responded with empathy, matching vulnerability, or genuine understanding
If BOTH conditions are met, include "vulnerability_exchange" in behaviors_identified.
Only tag genuine mutual vulnerability — one-sided sharing (only Nikita or only the player) is NOT an exchange.

Return a JSON object with:
- deltas: {intimacy, passion, trust, secureness} - each -10 to +10
- explanation: Brief explanation of your reasoning
- behaviors_identified: List of specific behaviors observed (including horseman:* tags if detected)
- confidence: Your confidence in this analysis (0.0 to 1.0)
- repair_attempt_detected: Whether the user's message contains a genuine repair attempt (true/false)
- repair_quality: If repair detected, rate as "excellent", "good", or "adequate". null if no repair.
"""


def _create_score_analyzer_agent() -> Agent[None, ResponseAnalysis]:
    """Create the score analyzer agent."""
    return Agent(
        ANALYSIS_MODEL,
        output_type=ResponseAnalysis,
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
            logger.warning(
                "LLM scoring failed, using zero-delta fallback: %s",
                str(e),
                extra={"scoring_error": True},
            )
            return self._fallback_analysis(error=str(e))

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
            return result.output
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
        """Return a neutral analysis (zero deltas, confidence=0.5).

        Used when LLM returns None or fails validation — the LLM ran but
        produced unusable output.  confidence=0.5 signals "uncertain but
        attempted".  No downstream consumer gates on this value (confirmed
        Feb 2026 via grep); it is stored for observability only.

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

    def _fallback_analysis(self, error: str = "") -> ResponseAnalysis:
        """Return zero-delta analysis with confidence=0.0 for LLM error fallback.

        Distinct from _neutral_analysis (confidence=0.5): this is used when
        the LLM call itself raised an exception — zero confidence signals
        "analysis never ran".  No downstream consumer gates on confidence
        thresholds for scoring (confirmed Feb 2026); ScoreCalculator.calculate()
        applies deltas unconditionally.
        """
        return ResponseAnalysis(
            deltas=MetricDeltas(
                intimacy=Decimal("0"),
                passion=Decimal("0"),
                trust=Decimal("0"),
                secureness=Decimal("0"),
            ),
            explanation=f"Fallback: {error}" if error else "Fallback: LLM scoring failed",
            behaviors_identified=[],
            confidence=Decimal("0.0"),
        )
