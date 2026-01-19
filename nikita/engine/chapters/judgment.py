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

from enum import Enum
from typing import Any
from pydantic import BaseModel


class BossResult(str, Enum):
    """Result of a boss encounter judgment"""
    PASS = "PASS"
    FAIL = "FAIL"


class JudgmentResult(BaseModel):
    """Structured result from boss judgment"""
    outcome: str  # 'PASS' or 'FAIL'
    reasoning: str


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
    ) -> JudgmentResult:
        """
        Judge whether the user passed or failed the boss encounter.

        Args:
            user_message: The user's response to the boss challenge
            conversation_history: Previous messages in the conversation
            chapter: Current chapter (1-5)
            boss_prompt: Boss prompt with success_criteria

        Returns:
            JudgmentResult with outcome (PASS/FAIL) and reasoning
        """
        return await self._call_llm(
            user_message=user_message,
            conversation_history=conversation_history,
            chapter=chapter,
            boss_prompt=boss_prompt,
        )

    async def _call_llm(
        self,
        user_message: str,
        conversation_history: list[dict[str, Any]],
        chapter: int,
        boss_prompt: dict[str, Any],
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

        Returns:
            JudgmentResult from LLM analysis
        """
        import logging
        from pydantic_ai import Agent

        logger = logging.getLogger(__name__)

        # Build the judgment prompt
        success_criteria = boss_prompt.get('success_criteria', '')
        challenge_context = boss_prompt.get('challenge_context', '')

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
"""

        user_prompt = f"""CONVERSATION HISTORY:
{self._format_history(conversation_history)}

PLAYER'S RESPONSE TO JUDGE:
{user_message}

Evaluate this response against the success criteria. Respond with a JSON object containing "outcome" (PASS or FAIL) and "reasoning"."""

        try:
            # Create agent with Claude Sonnet for consistent judgment
            agent = Agent(
                model="claude-sonnet-4-20250514",
                result_type=JudgmentResult,
                system_prompt=system_prompt,
            )

            # Run the agent
            result = await agent.run(user_prompt)

            logger.info(
                f"[BOSS-JUDGMENT] Chapter {chapter}: {result.output.outcome} - "
                f"{result.output.reasoning}"
            )

            return result.output

        except Exception as e:
            logger.error(f"[BOSS-JUDGMENT] LLM call failed: {e}", exc_info=True)
            # Fail safe - don't pass unfairly on error
            return JudgmentResult(
                outcome='FAIL',
                reasoning=f'Judgment error: {str(e)[:100]}'
            )

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
