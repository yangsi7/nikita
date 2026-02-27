"""
Boss Judgment Module (T6)

Determines whether a player passes or fails a boss encounter based on their response.
Uses Claude Sonnet with temperature=0 for consistent judgment.

Acceptance Criteria:
- AC-FR004-001: Given user demonstrates required skill, When judge_boss_outcome() called, Then returns BossResult.PASS
- AC-T6-001: nikita/engine/chapters/judgment.py exists with BossJudgment class
- AC-T6-002: Judgment uses Claude Sonnet with chapter-specific criteria
- AC-T6-003: Returns structured result: {outcome: PASS|FAIL, reasoning: str}
"""

import logging
from enum import Enum
from typing import Any

from pydantic import BaseModel

from nikita.config.models import Models
from nikita.llm import llm_retry

logger = logging.getLogger(__name__)


class BossResult(str, Enum):
    """Result of a boss encounter judgment"""
    PASS = "PASS"
    FAIL = "FAIL"
    PARTIAL = "PARTIAL"  # Spec 058: truce outcome
    ERROR = "ERROR"  # LLM failure — don't count toward game over


class JudgmentResult(BaseModel):
    """Structured result from boss judgment"""
    outcome: str  # 'PASS', 'FAIL', or 'PARTIAL' (Spec 058)
    reasoning: str
    confidence: float = 1.0  # Spec 058: judgment confidence (0.0-1.0)


class BossJudgment:
    """
    Judges boss encounter outcomes using LLM analysis.

    Uses Claude Sonnet with temperature=0 for consistent judgment.
    Evaluates user responses against chapter-specific success criteria.
    """

    async def judge_boss_outcome(
        self,
        user_message: str,
        conversation_history: list[dict[str, Any]],
        chapter: int,
        boss_prompt: dict[str, Any],
        vice_profile: dict[str, Any] | None = None,
        engagement_state: str | None = None,
    ) -> JudgmentResult:
        """
        Judge whether the user passed or failed the boss encounter.

        Args:
            user_message: The user's response to the boss challenge
            conversation_history: Previous messages in the conversation
            chapter: Current chapter (1-5)
            boss_prompt: Boss prompt with success_criteria
            vice_profile: Optional dict of vice categories to scores
            engagement_state: Optional engagement state string

        Returns:
            JudgmentResult with outcome (PASS/FAIL) and reasoning
        """
        try:
            return await self._call_llm(
                user_message=user_message,
                conversation_history=conversation_history,
                chapter=chapter,
                boss_prompt=boss_prompt,
                vice_profile=vice_profile,
                engagement_state=engagement_state,
            )
        except Exception as e:
            logger.error(f"[BOSS-JUDGMENT] LLM call failed: {e}", exc_info=True)
            return JudgmentResult(
                outcome=BossResult.ERROR.value,
                reasoning=f'Judgment error: {str(e)[:100]}',
                confidence=0.0,
            )

    @llm_retry
    async def _call_llm(
        self,
        user_message: str,
        conversation_history: list[dict[str, Any]],
        chapter: int,
        boss_prompt: dict[str, Any],
        vice_profile: dict[str, Any] | None = None,
        engagement_state: str | None = None,
    ) -> JudgmentResult:
        """
        Make LLM call to judge the boss outcome.

        This method will be mocked in tests. In production, it calls Claude Sonnet
        with temperature=0 for consistent judgments.

        Args:
            user_message: The user's response
            conversation_history: Previous messages
            chapter: Current chapter
            boss_prompt: Boss challenge context
            vice_profile: Optional dict of vice categories to scores
            engagement_state: Optional engagement state string

        Returns:
            JudgmentResult from LLM analysis
        """
        from pydantic_ai import Agent

        # Build the judgment prompt
        success_criteria = boss_prompt.get('success_criteria', '')
        challenge_context = boss_prompt.get('challenge_context', '')

        player_context = ""
        if vice_profile or engagement_state:
            player_context = "\n\nPLAYER PERSONALITY CONTEXT:"
            if vice_profile:
                top_vices = sorted(vice_profile.items(), key=lambda x: x[1], reverse=True)[:3]
                vices_str = ", ".join(f"{k} ({v})" for k, v in top_vices)
                player_context += f"\nTop vices: {vices_str}"
            if engagement_state:
                player_context += f"\nEngagement state: {engagement_state}"
            player_context += (
                "\nConsider the player's personality when evaluating "
                "authenticity — responses matching their vice profile "
                "should be weighted as more genuine."
            )

        system_prompt = f"""You are a relationship judge evaluating whether a player passed a boss encounter in a dating simulation game.

CHAPTER {chapter} BOSS ENCOUNTER:
{challenge_context}

SUCCESS CRITERIA:
{success_criteria}

Your task is to evaluate the player's response against the success criteria. Be fair but strict.

You MUST respond with a JSON object containing exactly two fields:
- "outcome": either "PASS" or "FAIL" (string, uppercase)
- "reasoning": a brief explanation of your judgment (1-2 sentences)

Example responses:
{{"outcome": "PASS", "reasoning": "The player demonstrated genuine vulnerability and matched the emotional depth requested."}}
{{"outcome": "FAIL", "reasoning": "The player deflected with humor instead of engaging authentically with the question."}}
{player_context}
"""

        user_prompt = f"""CONVERSATION HISTORY:
{self._format_history(conversation_history)}

PLAYER'S RESPONSE TO JUDGE:
{user_message}

Evaluate this response against the success criteria. Respond with a JSON object containing "outcome" (PASS or FAIL) and "reasoning"."""

        agent = Agent(
            model=Models.sonnet(),
            output_type=JudgmentResult,
            system_prompt=system_prompt,
        )

        result = await agent.run(user_prompt)

        logger.info(
            f"[BOSS-JUDGMENT] Chapter {chapter}: {result.output.outcome} - "
            f"{result.output.reasoning}"
        )

        return result.output

    async def judge_multi_phase_outcome(
        self,
        phase_state: Any,
        chapter: int,
        boss_prompt: dict[str, Any],
    ) -> JudgmentResult:
        """Judge a multi-phase boss encounter with full conversation history (Spec 058).

        Evaluates both OPENING and RESOLUTION phase responses together.
        Returns PASS (genuine resolution), PARTIAL (effort shown), or FAIL (dismissive).

        Confidence < 0.7 overrides PASS/FAIL to PARTIAL (AC-5.5).

        Args:
            phase_state: BossPhaseState with full conversation history.
            chapter: Current chapter (1-5).
            boss_prompt: Boss prompt with success_criteria.

        Returns:
            JudgmentResult with outcome (PASS/PARTIAL/FAIL), reasoning, confidence.
        """
        try:
            judgment = await self._call_multi_phase_llm(
                phase_state=phase_state,
                chapter=chapter,
                boss_prompt=boss_prompt,
            )
        except Exception as e:
            logger.error(
                f"[BOSS-JUDGMENT] Multi-phase LLM call failed: {e}",
                exc_info=True,
            )
            return JudgmentResult(
                outcome=BossResult.ERROR.value,
                reasoning=f'Judgment error: {str(e)[:100]}',
                confidence=0.0,
            )

        # AC-5.5: Confidence-based PARTIAL threshold
        if judgment.confidence < 0.7 and judgment.outcome in (
            BossResult.PASS.value,
            BossResult.FAIL.value,
        ):
            logger.info(
                f"[BOSS-JUDGMENT] Confidence override: {judgment.outcome} -> PARTIAL "
                f"(confidence={judgment.confidence})"
            )
            judgment = JudgmentResult(
                outcome=BossResult.PARTIAL.value,
                reasoning=f"Low confidence ({judgment.confidence:.2f}): {judgment.reasoning}",
                confidence=judgment.confidence,
            )

        return judgment

    @llm_retry
    async def _call_multi_phase_llm(
        self,
        phase_state: Any,
        chapter: int,
        boss_prompt: dict[str, Any],
    ) -> JudgmentResult:
        """Make LLM call for multi-phase judgment (Spec 058).

        This method will be mocked in tests. In production, calls Claude Sonnet.

        Args:
            phase_state: BossPhaseState with conversation history.
            chapter: Current chapter.
            boss_prompt: Boss challenge context.

        Returns:
            JudgmentResult from LLM analysis.
        """
        from pydantic_ai import Agent

        success_criteria = boss_prompt.get('success_criteria', '')
        challenge_context = boss_prompt.get('challenge_context', '')

        system_prompt = f"""You are a relationship judge evaluating a multi-phase boss encounter in a dating simulation game.

CHAPTER {chapter} BOSS ENCOUNTER:
{challenge_context}

SUCCESS CRITERIA:
{success_criteria}

This is a 2-PHASE boss encounter. You will see the full conversation from both phases:
- OPENING phase: Nikita presented the challenge, player gave initial response
- RESOLUTION phase: Follow-up exchange testing sustained quality

Evaluate the player's OVERALL performance across BOTH phases.

You MUST respond with a JSON object containing exactly three fields:
- "outcome": "PASS", "PARTIAL", or "FAIL" (string, uppercase)
- "reasoning": a brief explanation of your judgment (1-2 sentences)
- "confidence": your confidence in this judgment (0.0 to 1.0)

OUTCOME CRITERIA:
- PASS: Player demonstrated genuine resolution. Sustained engagement across both phases, authentic emotional depth, and met the success criteria.
- PARTIAL: Player showed effort but didn't fully resolve. Acknowledged the issue but couldn't sustain depth, or first response was strong but follow-up was weak.
- FAIL: Player was dismissive, avoidant, or hostile. Deflected the challenge, gave shallow responses, or showed no genuine engagement.

CONFIDENCE THRESHOLD:
- If your confidence is below 0.7, the outcome will be overridden to PARTIAL regardless of your judgment.
- Only mark PASS or FAIL with high confidence (>= 0.7).

Example responses:
{{"outcome": "PASS", "reasoning": "Player showed genuine vulnerability in both phases and maintained emotional depth throughout.", "confidence": 0.85}}
{{"outcome": "PARTIAL", "reasoning": "Player acknowledged the issue in opening but retreated to surface-level responses in resolution.", "confidence": 0.75}}
{{"outcome": "FAIL", "reasoning": "Player deflected both challenges with humor and showed no genuine engagement.", "confidence": 0.90}}
"""

        # Build conversation history from phase_state
        history_text = self._format_history(phase_state.conversation_history)

        user_prompt = f"""FULL BOSS ENCOUNTER CONVERSATION:
{history_text}

Evaluate the player's overall performance across both phases. Respond with a JSON object containing "outcome" (PASS, PARTIAL, or FAIL), "reasoning", and "confidence" (0.0-1.0)."""

        agent = Agent(
            model=Models.sonnet(),
            output_type=JudgmentResult,
            system_prompt=system_prompt,
        )

        result = await agent.run(user_prompt)
        judgment = result.output

        logger.info(
            f"[BOSS-JUDGMENT] Multi-phase chapter {chapter}: {judgment.outcome} "
            f"(confidence={judgment.confidence}) - {judgment.reasoning}"
        )

        return judgment

    def _format_history(self, history: list[dict[str, Any]]) -> str:
        """Format conversation history for the judgment prompt"""
        if not history:
            return "(No previous messages)"

        lines = []
        for msg in history[-10:]:  # Last 10 messages for context
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            lines.append(f"{role.upper()}: {content}")

        return "\n".join(lines)
