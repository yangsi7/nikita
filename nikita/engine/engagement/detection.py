"""Detection algorithms for engagement analysis (spec 014).

This module implements the clinginess and neglect detection algorithms
that analyze player messaging patterns to determine engagement quality.

Detectors:
- ClinginessDetector: 5 signals with weights (frequency=0.35, double_text=0.20,
  response=0.15, length=0.10, needy=0.20)
- NeglectDetector: 5 signals with weights (frequency=0.35, slow=0.20, short=0.15,
  endings=0.10, distracted=0.20)

LLM Analysis:
- analyze_neediness(): Pydantic AI structured output for needy language
- analyze_distraction(): Pydantic AI structured output for distracted patterns
"""

import logging
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from nikita.engine.engagement.models import ClinginessResult, NeglectResult

logger = logging.getLogger(__name__)

# Signal weights for clinginess detection
CLINGINESS_WEIGHTS = {
    "frequency": Decimal("0.35"),
    "double_text": Decimal("0.20"),
    "response_time": Decimal("0.15"),
    "length_ratio": Decimal("0.10"),
    "needy_language": Decimal("0.20"),
}

# Signal weights for neglect detection
NEGLECT_WEIGHTS = {
    "frequency": Decimal("0.35"),
    "response_time": Decimal("0.20"),
    "short_messages": Decimal("0.15"),
    "abrupt_endings": Decimal("0.10"),
    "distracted_language": Decimal("0.20"),
}

# Thresholds
CLINGINESS_THRESHOLD = Decimal("0.7")
NEGLECT_THRESHOLD = Decimal("0.6")

# Cache for LLM analysis results (session_id -> hash -> result)
_analysis_cache: dict[str, dict[str, Decimal]] = {}

# LLM model for analysis - using Haiku for cost efficiency
ENGAGEMENT_ANALYSIS_MODEL = "anthropic:claude-haiku-4-5-20251001"


class LanguageAnalysisResult(BaseModel):
    """Result from LLM language pattern analysis."""

    score: Decimal = Field(
        ge=Decimal("0"),
        le=Decimal("1"),
        description="Language pattern score from 0.0 (none) to 1.0 (strong)",
    )
    confidence: Decimal = Field(
        default=Decimal("0.8"),
        ge=Decimal("0"),
        le=Decimal("1"),
        description="Confidence in the analysis",
    )
    patterns_found: list[str] = Field(
        default_factory=list,
        description="Specific patterns identified in the messages",
    )


# System prompt for neediness analysis
NEEDINESS_SYSTEM_PROMPT = """You are analyzing messages from a player in a relationship simulation game.
Your task is to detect needy language patterns that indicate clingy behavior.

Needy patterns include:
- Desperate questions: "Are you there?", "Why aren't you responding?", "Hello???"
- Excessive affection seeking: "I miss you so much", "I can't stop thinking about you"
- Validation seeking: "Do you like me?", "Am I annoying you?", "Did I do something wrong?"
- Urgency without cause: "I need to talk NOW", "Please respond ASAP"
- Apologizing excessively: "Sorry to bother you", "Sorry for messaging again"
- Double/triple texting patterns when asking same thing multiple ways

Return a score from 0.0 (no needy patterns) to 1.0 (very needy language).
Be fair - occasional expressions of affection are normal and should score low (0.1-0.3).
Only high scores (0.7+) for consistently needy patterns across multiple messages.

Return JSON with: score (0.0-1.0), confidence (0.0-1.0), patterns_found (list of strings).
"""

# System prompt for distraction analysis
DISTRACTION_SYSTEM_PROMPT = """You are analyzing messages from a player in a relationship simulation game.
Your task is to detect distracted/disengaged language patterns that indicate distant behavior.

Distracted patterns include:
- Terse responses: "k", "ok", "fine", "whatever", "sure"
- Dismissive language: "busy rn", "can't talk", "later"
- Lack of questions or interest: Not asking about the other person
- Abrupt topic changes without acknowledgment
- One-word answers repeatedly
- Generic responses that don't engage with previous content
- "gtg", "brb" without returning for extended periods

Return a score from 0.0 (fully engaged) to 1.0 (very distracted/disengaged).
Be fair - occasional short messages are normal and should score low (0.1-0.3).
Only high scores (0.7+) for consistently disengaged patterns across multiple messages.

Return JSON with: score (0.0-1.0), confidence (0.0-1.0), patterns_found (list of strings).
"""

# Lazy-loaded agents
_neediness_agent: Agent[None, LanguageAnalysisResult] | None = None
_distraction_agent: Agent[None, LanguageAnalysisResult] | None = None


def _get_neediness_agent() -> Agent[None, LanguageAnalysisResult]:
    """Get or create the neediness analysis agent."""
    global _neediness_agent
    if _neediness_agent is None:
        _neediness_agent = Agent(
            ENGAGEMENT_ANALYSIS_MODEL,
            output_type=LanguageAnalysisResult,
            system_prompt=NEEDINESS_SYSTEM_PROMPT,
        )
    return _neediness_agent


def _get_distraction_agent() -> Agent[None, LanguageAnalysisResult]:
    """Get or create the distraction analysis agent."""
    global _distraction_agent
    if _distraction_agent is None:
        _distraction_agent = Agent(
            ENGAGEMENT_ANALYSIS_MODEL,
            output_type=LanguageAnalysisResult,
            system_prompt=DISTRACTION_SYSTEM_PROMPT,
        )
    return _distraction_agent


def _clamp(value: Decimal, min_val: Decimal = Decimal("0"), max_val: Decimal = Decimal("1")) -> Decimal:
    """Clamp a value between min and max."""
    return max(min_val, min(max_val, value))


class ClinginessDetector:
    """Detects clingy behavior patterns in player messaging.

    5 Signals:
    1. Frequency signal (35%): Messages per day vs optimal
    2. Double-text signal (20%): Multiple messages before response
    3. Response time signal (15%): Too-fast responses (<30s)
    4. Length ratio signal (10%): Message length vs Nikita's
    5. Needy language signal (20%): LLM-detected needy patterns

    Threshold: score > 0.7 = is_clingy
    """

    def _frequency_signal(
        self,
        messages_per_day: int,
        optimal_frequency: int,
        chapter: int,
    ) -> Decimal:
        """Calculate frequency signal based on message volume.

        High signal when messaging significantly more than optimal.
        Uses chapter-aware thresholds.

        Returns 0-1 score (higher = more clingy).
        """
        if optimal_frequency <= 0:
            return Decimal("0")

        # Calculate ratio of actual to optimal
        ratio = Decimal(str(messages_per_day)) / Decimal(str(optimal_frequency))

        # No clinginess if at or below optimal
        if ratio <= Decimal("1"):
            return Decimal("0")

        # Scale from 0 at 1x to 1 at 2x+ optimal
        excess_ratio = ratio - Decimal("1")
        signal = _clamp(excess_ratio)

        return signal

    def _double_text_signal(
        self,
        consecutive_messages: int,
        total_exchanges: int,
    ) -> Decimal:
        """Calculate double-text signal based on consecutive messages.

        High signal when sending many messages before Nikita responds.

        Returns 0-1 score (higher = more clingy).
        """
        if total_exchanges <= 0:
            return Decimal("0")

        # 1 message per exchange is normal (score 0)
        # 5+ messages before response is very clingy (score 1)
        if consecutive_messages <= 1:
            return Decimal("0")

        excess = consecutive_messages - 1
        signal = _clamp(Decimal(str(excess)) / Decimal("4"))

        return signal

    def _response_time_signal(
        self,
        avg_response_seconds: int,
    ) -> Decimal:
        """Calculate response time signal based on speed.

        High signal when responding too quickly (<30 seconds).

        Returns 0-1 score (higher = more clingy).
        """
        # 30 seconds = threshold for "instant" responses
        # 5 minutes (300s) = normal, score 0
        if avg_response_seconds >= 300:
            return Decimal("0")

        if avg_response_seconds <= 0:
            return Decimal("1")

        # Scale from 1 at 0s to 0 at 300s
        # Threshold at 30s = 0.9
        signal = Decimal("1") - (Decimal(str(avg_response_seconds)) / Decimal("300"))

        return _clamp(signal)

    def _length_ratio_signal(
        self,
        user_avg_length: int,
        nikita_avg_length: int,
    ) -> Decimal:
        """Calculate length ratio signal.

        High signal when user messages are much longer than Nikita's.

        Returns 0-1 score (higher = more clingy).
        """
        if nikita_avg_length <= 0:
            return Decimal("0")

        ratio = Decimal(str(user_avg_length)) / Decimal(str(nikita_avg_length))

        # 1:1 ratio = normal (score 0)
        # 3:1 ratio = very clingy (score 1)
        if ratio <= Decimal("1"):
            return Decimal("0")

        excess_ratio = ratio - Decimal("1")
        signal = _clamp(excess_ratio / Decimal("2"))

        return signal

    def detect(
        self,
        messages_per_day: int,
        optimal_frequency: int,
        chapter: int,
        consecutive_messages: int,
        total_exchanges: int,
        avg_response_seconds: int,
        user_avg_length: int,
        nikita_avg_length: int,
        needy_score: Decimal,
    ) -> ClinginessResult:
        """Detect clinginess and return composite result.

        Combines 5 signals with weights:
        - frequency: 35%
        - double_text: 20%
        - response_time: 15%
        - length_ratio: 10%
        - needy_language: 20%

        is_clingy = True when score > 0.7
        """
        # Calculate individual signals
        frequency = self._frequency_signal(messages_per_day, optimal_frequency, chapter)
        double_text = self._double_text_signal(consecutive_messages, total_exchanges)
        response_time = self._response_time_signal(avg_response_seconds)
        length_ratio = self._length_ratio_signal(user_avg_length, nikita_avg_length)
        needy_language = _clamp(needy_score)

        # Calculate weighted composite score
        score = (
            frequency * CLINGINESS_WEIGHTS["frequency"] +
            double_text * CLINGINESS_WEIGHTS["double_text"] +
            response_time * CLINGINESS_WEIGHTS["response_time"] +
            length_ratio * CLINGINESS_WEIGHTS["length_ratio"] +
            needy_language * CLINGINESS_WEIGHTS["needy_language"]
        )

        score = _clamp(score)

        return ClinginessResult(
            score=score,
            is_clingy=score > CLINGINESS_THRESHOLD,
            signals={
                "frequency": frequency,
                "double_text": double_text,
                "response_time": response_time,
                "length_ratio": length_ratio,
                "needy_language": needy_language,
            },
        )


class NeglectDetector:
    """Detects neglect behavior patterns in player messaging.

    5 Signals:
    1. Frequency signal (35%): Messages per day vs optimal (too few)
    2. Response time signal (20%): Too-slow responses (>4 hours)
    3. Short message signal (15%): Very short messages (<20 chars)
    4. Abrupt endings signal (10%): Ending conversations abruptly
    5. Distracted language signal (20%): LLM-detected disengagement

    Threshold: score > 0.6 = is_neglecting
    """

    def _frequency_signal(
        self,
        messages_per_day: int,
        optimal_frequency: int,
        chapter: int,
    ) -> Decimal:
        """Calculate frequency signal based on message volume.

        High signal when messaging significantly less than optimal.

        Returns 0-1 score (higher = more neglecting).
        """
        if optimal_frequency <= 0:
            return Decimal("0")

        ratio = Decimal(str(messages_per_day)) / Decimal(str(optimal_frequency))

        # No neglect if at or above optimal
        if ratio >= Decimal("1"):
            return Decimal("0")

        # Scale from 0 at 1x to 1 at 0x (inverse)
        signal = Decimal("1") - ratio

        return _clamp(signal)

    def _response_time_signal(
        self,
        avg_response_seconds: int,
    ) -> Decimal:
        """Calculate response time signal based on delays.

        High signal when responding too slowly (>4 hours).

        Returns 0-1 score (higher = more neglecting).
        """
        four_hours = 4 * 3600  # 14400 seconds

        if avg_response_seconds <= four_hours:
            return Decimal("0")

        # Scale from 0 at 4h to 1 at 8h+
        eight_hours = 8 * 3600
        excess = avg_response_seconds - four_hours
        signal = Decimal(str(excess)) / Decimal(str(four_hours))

        return _clamp(signal)

    def _short_message_signal(
        self,
        avg_message_length: int,
    ) -> Decimal:
        """Calculate short message signal.

        High signal when messages are very short (<20 chars average).

        Returns 0-1 score (higher = more neglecting).
        """
        # 20 chars = threshold
        # 50+ chars = normal (score 0)
        if avg_message_length >= 50:
            return Decimal("0")

        if avg_message_length <= 0:
            return Decimal("1")

        # Scale from 1 at 0 chars to 0 at 50 chars
        # 20 chars = 0.6 signal
        signal = Decimal("1") - (Decimal(str(avg_message_length)) / Decimal("50"))

        return _clamp(signal)

    def _abrupt_ending_signal(
        self,
        abrupt_endings: int,
        total_conversations: int,
    ) -> Decimal:
        """Calculate abrupt ending signal.

        High signal when many conversations end abruptly.

        Returns 0-1 score (higher = more neglecting).
        """
        if total_conversations <= 0:
            return Decimal("0")

        ratio = Decimal(str(abrupt_endings)) / Decimal(str(total_conversations))

        return _clamp(ratio)

    def detect(
        self,
        messages_per_day: int,
        optimal_frequency: int,
        chapter: int,
        avg_response_seconds: int,
        avg_message_length: int,
        abrupt_endings: int,
        total_conversations: int,
        distracted_score: Decimal,
    ) -> NeglectResult:
        """Detect neglect and return composite result.

        Combines 5 signals with weights:
        - frequency: 35%
        - response_time: 20%
        - short_messages: 15%
        - abrupt_endings: 10%
        - distracted_language: 20%

        is_neglecting = True when score > 0.6
        """
        # Calculate individual signals
        frequency = self._frequency_signal(messages_per_day, optimal_frequency, chapter)
        response_time = self._response_time_signal(avg_response_seconds)
        short_messages = self._short_message_signal(avg_message_length)
        abrupt = self._abrupt_ending_signal(abrupt_endings, total_conversations)
        distracted_language = _clamp(distracted_score)

        # Calculate weighted composite score
        score = (
            frequency * NEGLECT_WEIGHTS["frequency"] +
            response_time * NEGLECT_WEIGHTS["response_time"] +
            short_messages * NEGLECT_WEIGHTS["short_messages"] +
            abrupt * NEGLECT_WEIGHTS["abrupt_endings"] +
            distracted_language * NEGLECT_WEIGHTS["distracted_language"]
        )

        score = _clamp(score)

        return NeglectResult(
            score=score,
            is_neglecting=score > NEGLECT_THRESHOLD,
            signals={
                "frequency": frequency,
                "response_time": response_time,
                "short_messages": short_messages,
                "abrupt_endings": abrupt,
                "distracted_language": distracted_language,
            },
        )


# ==============================================================================
# LLM Analysis Functions (T2.3)
# ==============================================================================


def _get_cache_key(messages: list[str]) -> str:
    """Generate cache key from messages."""
    return hash(tuple(messages)).__str__()


async def _call_neediness_llm(messages: list[str]) -> Decimal:
    """Call LLM to analyze neediness patterns.

    Uses Pydantic AI with Claude Haiku for cost-efficient analysis.
    Returns score 0-1 for needy language patterns.

    Args:
        messages: List of user messages to analyze

    Returns:
        Decimal score 0-1 (higher = more needy)
    """
    try:
        agent = _get_neediness_agent()
        # Format messages for analysis
        prompt = f"""Analyze these messages for needy language patterns:

Messages:
{chr(10).join(f'- "{msg}"' for msg in messages)}

Analyze the overall pattern across all messages and return your assessment."""

        result = await agent.run(prompt)
        logger.debug(
            f"Neediness analysis: score={result.output.score}, "
            f"patterns={result.output.patterns_found}"
        )
        return result.output.score
    except Exception as e:
        logger.error(f"Neediness LLM analysis failed: {e}")
        # Return neutral score on error
        return Decimal("0.3")


async def _call_distraction_llm(messages: list[str]) -> Decimal:
    """Call LLM to analyze distraction patterns.

    Uses Pydantic AI with Claude Haiku for cost-efficient analysis.
    Returns score 0-1 for distracted/disengaged patterns.

    Args:
        messages: List of user messages to analyze

    Returns:
        Decimal score 0-1 (higher = more distracted)
    """
    try:
        agent = _get_distraction_agent()
        # Format messages for analysis
        prompt = f"""Analyze these messages for distracted/disengaged language patterns:

Messages:
{chr(10).join(f'- "{msg}"' for msg in messages)}

Analyze the overall pattern across all messages and return your assessment."""

        result = await agent.run(prompt)
        logger.debug(
            f"Distraction analysis: score={result.output.score}, "
            f"patterns={result.output.patterns_found}"
        )
        return result.output.score
    except Exception as e:
        logger.error(f"Distraction LLM analysis failed: {e}")
        # Return neutral score on error
        return Decimal("0.3")


async def analyze_neediness(
    messages: list[str],
    session_id: str | None = None,
) -> Decimal:
    """Analyze messages for needy language patterns using Pydantic AI.

    Needy patterns include:
    - Desperate questions ("Are you there?", "Why aren't you responding?")
    - Excessive affection seeking ("I miss you so much")
    - Validation seeking ("Do you like me?", "Am I annoying you?")
    - Urgency without cause ("I need to talk NOW")

    Args:
        messages: List of recent user messages to analyze
        session_id: Optional session ID for caching

    Returns:
        Decimal score 0-1 (higher = more needy)
    """
    if not messages:
        return Decimal("0")

    # Check cache if session_id provided
    cache_key = _get_cache_key(messages)
    if session_id and session_id in _analysis_cache:
        if cache_key in _analysis_cache[session_id]:
            return _analysis_cache[session_id][cache_key]

    # Call LLM
    score = await _call_neediness_llm(messages)
    score = _clamp(score)

    # Cache result
    if session_id:
        if session_id not in _analysis_cache:
            _analysis_cache[session_id] = {}
        _analysis_cache[session_id][cache_key] = score

    return score


async def analyze_distraction(
    messages: list[str],
    session_id: str | None = None,
) -> Decimal:
    """Analyze messages for distracted/disengaged patterns using Pydantic AI.

    Distracted patterns include:
    - Terse responses ("k", "fine", "whatever")
    - Dismissive language ("busy rn", "later")
    - Lack of engagement with previous topics
    - Abrupt topic changes

    Args:
        messages: List of recent user messages to analyze
        session_id: Optional session ID for caching

    Returns:
        Decimal score 0-1 (higher = more distracted/disengaged)
    """
    if not messages:
        return Decimal("0")

    # Check cache if session_id provided
    cache_key = _get_cache_key(messages)
    if session_id and session_id in _analysis_cache:
        if cache_key in _analysis_cache[session_id]:
            return _analysis_cache[session_id][cache_key]

    # Call LLM
    score = await _call_distraction_llm(messages)
    score = _clamp(score)

    # Cache result
    if session_id:
        if session_id not in _analysis_cache:
            _analysis_cache[session_id] = {}
        _analysis_cache[session_id][cache_key] = score

    return score


def clear_analysis_cache() -> None:
    """Clear the LLM analysis cache.

    Call this at session boundaries to free memory.
    """
    global _analysis_cache
    _analysis_cache = {}
