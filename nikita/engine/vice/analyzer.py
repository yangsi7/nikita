"""
Vice Analyzer Module (T010, T011)

LLM-based analysis of conversations to detect vice signals.
Uses Pydantic AI with Claude for structured vice detection.
"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from nikita.config.enums import ViceCategory
from nikita.config.settings import get_settings
from nikita.engine.vice.models import ViceAnalysisResult, ViceSignal


# Structured output model for LLM response
class LLMViceSignal(BaseModel):
    """LLM output format for a vice signal."""

    category: str = Field(description="Vice category detected")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence 0.0-1.0")
    evidence: str = Field(description="Quote or reasoning for detection")
    is_positive: bool = Field(description="True=engagement, False=rejection")


class LLMViceAnalysis(BaseModel):
    """LLM output format for vice analysis."""

    signals: list[LLMViceSignal] = Field(default_factory=list)


# Vice category descriptions for prompt (T010: AC-T010.1)
VICE_DESCRIPTIONS = {
    "intellectual_dominance": "Enjoys debates, showing expertise, mental challenges, correcting others",
    "risk_taking": "Attracted to danger, adrenaline, unconventional choices, thrills",
    "substances": "Open about alcohol, drugs, partying lifestyle without judgment",
    "sexuality": "Responds to flirtation, innuendo, attraction-based conversation",
    "emotional_intensity": "Seeks deep emotional exchanges, intense feelings, drama",
    "rule_breaking": "Anti-authority, norms-defying, rebellious attitudes",
    "dark_humor": "Appreciates morbid, edgy, uncomfortable, self-deprecating jokes",
    "vulnerability": "Values emotional openness, sharing fears, authentic weakness",
}

# Vice analysis prompt template (T010: AC-T010.2, AC-T010.3, AC-T010.4)
VICE_ANALYSIS_PROMPT = """Analyze this conversation exchange for vice signals.

Vice categories to detect:
{vice_list}

User message: "{user_message}"
Nikita's response: "{nikita_response}"

Detect any vice signals in the USER's message:
1. Look for topics they bring up that match vice categories
2. Note enthusiasm level (long replies, follow-up questions = engagement)
3. Detect rejection signals (short replies, topic changes, negative reactions)
4. Only report signals with confidence >= 0.50

For each signal detected:
- category: One of the 8 vice categories
- confidence: 0.0-1.0 (how certain the signal is)
- evidence: Quote the specific text or explain reasoning
- is_positive: True if user is engaging with the vice, False if rejecting it

Return empty signals list if no clear vice signals detected.
Be conservative - prefer missing a signal to false positives."""


class ViceAnalyzer:
    """T011: LLM-based vice signal analyzer.

    Analyzes conversation exchanges to detect vice signals using Pydantic AI.
    """

    def __init__(self):
        """Initialize analyzer with Pydantic AI agent."""
        self._agent: Agent[None, LLMViceAnalysis] | None = None

    def _get_agent(self) -> Agent[None, LLMViceAnalysis]:
        """Lazy-load Pydantic AI agent for vice analysis."""
        if self._agent is None:
            settings = get_settings()
            self._agent = Agent(
                model=settings.secondary_model,  # Use cheaper model for analysis
                result_type=LLMViceAnalysis,
                system_prompt=(
                    "You are a behavioral analyst detecting engagement patterns. "
                    "Analyze messages for vice category signals. Be accurate and conservative."
                ),
            )
        return self._agent

    async def analyze_exchange(
        self,
        user_message: str,
        nikita_response: str,
        conversation_id: UUID,
        context: dict | None = None,
    ) -> ViceAnalysisResult:
        """Analyze a conversation exchange for vice signals.

        Args:
            user_message: The user's message
            nikita_response: Nikita's response
            conversation_id: ID for traceability
            context: Optional context (chapter, recent history)

        Returns:
            ViceAnalysisResult with detected signals
        """
        # Build vice list for prompt (AC-T010.1)
        vice_list = "\n".join(
            f"- {cat}: {desc}"
            for cat, desc in VICE_DESCRIPTIONS.items()
        )

        # Format prompt
        prompt = VICE_ANALYSIS_PROMPT.format(
            vice_list=vice_list,
            user_message=user_message,
            nikita_response=nikita_response,
        )

        # Call LLM
        llm_result = await self._analyze_with_llm(prompt)

        # Convert to ViceSignal objects
        signals = self._convert_llm_signals(llm_result.get("signals", []))

        return ViceAnalysisResult(
            signals=signals,
            conversation_id=conversation_id,
            analyzed_at=datetime.now(timezone.utc),
        )

    async def _analyze_with_llm(self, prompt: str) -> dict:
        """Call LLM for vice analysis.

        This method is separated for easy mocking in tests.

        Args:
            prompt: Formatted analysis prompt

        Returns:
            Dict with 'signals' list
        """
        agent = self._get_agent()
        result = await agent.run(prompt)
        return {"signals": [s.model_dump() for s in result.data.signals]}

    def _convert_llm_signals(self, llm_signals: list[dict]) -> list[ViceSignal]:
        """Convert LLM output to ViceSignal objects.

        Args:
            llm_signals: Raw signal dicts from LLM

        Returns:
            List of validated ViceSignal objects
        """
        signals = []
        for raw in llm_signals:
            try:
                # Validate category
                category_str = raw.get("category", "").lower()
                if category_str not in [vc.value for vc in ViceCategory]:
                    continue

                # Create ViceSignal
                signal = ViceSignal(
                    category=ViceCategory(category_str),
                    confidence=Decimal(str(raw.get("confidence", 0.0))),
                    evidence=raw.get("evidence", ""),
                    is_positive=raw.get("is_positive", True),
                )
                signals.append(signal)
            except (ValueError, KeyError):
                # Skip invalid signals
                continue

        return signals
