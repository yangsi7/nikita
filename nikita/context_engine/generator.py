"""PromptGenerator agent for Context Engine (Spec 039).

Layer 2 of the unified context engine architecture:
- Input: ContextPackage from ContextEngine
- Output: PromptBundle with text and voice system prompt blocks
- Uses Claude Sonnet 4.5 for intelligent narrative generation
- Includes validation with retry logic
"""

import json
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import ValidationError
from pydantic_ai import Agent, ModelRetry

from nikita.context_engine.models import BackstoryContext, ContextPackage, PromptBundle
from nikita.context_engine.validators import (
    CoverageValidator,
    GuardrailsValidator,
    SpeakabilityValidator,
)

logger = logging.getLogger(__name__)


def _format_backstory(backstory: BackstoryContext | None) -> str:
    """Format backstory as bullet points for token efficiency (Spec 040).

    Uses bullet point format which is 62% more token-efficient than prose.
    Only includes fields that have content (no placeholders for empty fields).

    Returns:
        Formatted backstory string with bullet points, or default text.
    """
    if not backstory or not backstory.has_backstory():
        return "- Standard meeting story"

    lines = []
    if backstory.venue:
        lines.append(f"- Where we met: {backstory.venue}")
    if backstory.how_we_met:
        lines.append(f"- The context: {backstory.how_we_met}")
    if backstory.the_moment:
        lines.append(f"- The spark: {backstory.the_moment}")
    if backstory.unresolved_hook:
        lines.append(f"- Unfinished business: {backstory.unresolved_hook}")
    if backstory.tone:
        lines.append(f"- Tone: {backstory.tone}")

    return "\n".join(lines) if lines else "- Standard meeting story"

# Model for prompt generation - using Sonnet for deep reasoning
GENERATOR_MODEL = "anthropic:claude-sonnet-4-5-20250929"

# Path to generator meta prompt
GENERATOR_PROMPT_PATH = Path(__file__).parent / "prompts" / "generator.meta.md"

# Maximum retries for validation failures
MAX_VALIDATION_RETRIES = 3


@dataclass
class GeneratorDeps:
    """Dependencies injected into PromptGenerator agent."""

    context: ContextPackage


@dataclass
class GeneratorResult:
    """Result from PromptGenerator including metadata."""

    bundle: PromptBundle
    generation_time_ms: float
    retries_used: int
    validation_errors: list[str]


def _load_generator_prompt() -> str:
    """Load the generator meta prompt from file."""
    if GENERATOR_PROMPT_PATH.exists():
        return GENERATOR_PROMPT_PATH.read_text()

    # Fallback to embedded prompt
    return """You are an expert prompt engineer creating narrative-rich system prompts for Nikita.

Generate TWO prompt blocks:
1. TEXT SYSTEM PROMPT BLOCK (6,000-12,000 tokens) with all required sections
2. VOICE SYSTEM PROMPT BLOCK (800-1,500 tokens) that is speakable

Output valid JSON with: text_system_prompt_block, voice_system_prompt_block, sections_present, coverage_notes
"""


def _context_to_prompt_input(context: ContextPackage) -> str:
    """Convert ContextPackage to structured input for generator.

    This formats the context in a way that's easy for the LLM to process.
    """
    # Build user facts section
    user_facts = "\n".join(f"- {fact}" for fact in context.user_facts[:30]) if context.user_facts else "No facts yet"

    # Build relationship episodes
    episodes = "\n".join(f"- {ep}" for ep in context.relationship_episodes[:20]) if context.relationship_episodes else "None"

    # Build nikita events
    nikita_events = "\n".join(f"- {ev}" for ev in context.nikita_events[:20]) if context.nikita_events else "None"

    # Build social circle
    social = ""
    for member in context.social_circle[:5]:
        social += f"- {member.name} ({member.relationship}): {member.backstory[:100]}\n"
    if not social:
        social = "Lena (best friend), Viktor (complicated), Yuki (party friend)"

    # Build open threads
    threads = ""
    for thread in context.open_threads[:5]:
        threads += f"- {thread.topic} ({thread.status}, priority {thread.priority})\n"
    if not threads:
        threads = "None currently"

    # Build past prompts reference
    past_prompts_text = ""
    if context.past_prompts:
        for pp in context.past_prompts[:3]:
            past_prompts_text += f"- {pp.generated_at}: {pp.summary[:100]}\n"
    else:
        past_prompts_text = "No previous prompts (new user)"

    # Build vice profile
    top_vices = context.vice_profile.get_top_vices(3)
    vices_text = ", ".join(f"{v[0]}={v[1]}" for v in top_vices) if top_vices else "Not yet detected"

    return f"""## CONTEXT FOR PROMPT GENERATION

### User Identity
- User ID: {context.user_id}
- Days since start: {context.days_since_start}
- Total conversations: {context.total_conversations}
- Total words exchanged: {context.total_words_exchanged}

### Temporal Context
- Local time: {context.local_time.strftime("%H:%M")} on {context.day_of_week}
- Time of day: {context.time_of_day}
- Hours since last contact: {context.hours_since_last_contact:.1f}
- Recency interpretation: {context.recency_interpretation.value}

### Relationship State
- Chapter: {context.chapter}/5 ({context.chapter_name})
- Relationship score: {context.relationship_score}/100
- Score interpretation: {context.get_score_interpretation()}
- Engagement state: {context.engagement_state}
- Vulnerability level: {context.vulnerability_level.value}

### Nikita's Current State
- Activity: {context.nikita_activity}
- Mood 4D: {context.nikita_mood_4d.to_description()}
- Daily events: {', '.join(context.nikita_daily_events[:3]) if context.nikita_daily_events else 'Quiet day'}
- Recent events: {', '.join(context.nikita_recent_events[:3]) if context.nikita_recent_events else 'Nothing notable'}

### Psychological State
- Attachment style: {context.psychological_state.attachment_style}
- Active defenses: {', '.join(context.psychological_state.active_defenses) if context.psychological_state.active_defenses else 'None active'}
- Core wound active: {'Yes' if context.psychological_state.core_wound_active else 'No'}
- Inner monologue: {context.psychological_state.inner_monologue[:200] if context.psychological_state.inner_monologue else 'Calm'}

### Memory - User Knowledge
{user_facts}

### Memory - Relationship Episodes
{episodes}

### Memory - Nikita's Life
{nikita_events}

### Social Circle
{social}

### Open Threads
{threads}

### Active Conflict
{f"Type: {context.active_conflict.conflict_type}, Severity: {context.active_conflict.severity}, Stage: {context.active_conflict.stage}" if context.active_conflict else "None"}

### Vice Profile
{vices_text}

### Recent Thoughts
{chr(10).join(f"- {t}" for t in context.recent_thoughts[:3]) if context.recent_thoughts else 'Mind is clear'}

### Last Conversation Summary
{context.last_conversation_summary if context.last_conversation_summary else 'No previous conversation'}

### Today's Key Moments
{chr(10).join(f"- {m}" for m in context.today_key_moments[:5]) if context.today_key_moments else 'Nothing notable yet'}

### Past Prompts (for continuity)
{past_prompts_text}

### Chapter Behavior Summary
{context.get_chapter_summary()}

### Behavioral Instructions
{context.behavioral_instructions if context.behavioral_instructions else 'Standard behavior for this chapter'}

### How We Met (Backstory)
{_format_backstory(context.backstory)}

### Onboarding State
- New user (≤7 days): {'Yes' if context.is_new_user else 'No'}
- Days since onboarding: {context.days_since_onboarding}
- Profile summary: {context.onboarding_profile_summary if context.onboarding_profile_summary else 'No profile data'}

---

Generate the TEXT and VOICE prompt blocks now. Output as JSON."""


class PromptGenerator:
    """Generates narrative-rich system prompts from ContextPackage.

    Layer 2 of the unified context engine:
    - Takes ContextPackage as input
    - Uses Claude Sonnet 4.5 for intelligent generation
    - Validates output with coverage, guardrails, speakability
    - Retries on validation failure (up to 3 times)
    """

    def __init__(
        self,
        model: str = GENERATOR_MODEL,
        max_retries: int = MAX_VALIDATION_RETRIES,
    ):
        """Initialize the PromptGenerator.

        Args:
            model: Model to use for generation.
            max_retries: Maximum validation retries.
        """
        self.model = model
        self.max_retries = max_retries
        self._agent: Agent[GeneratorDeps, dict[str, Any]] | None = None

        # Validators
        self._coverage_validator = CoverageValidator()
        self._guardrails_validator = GuardrailsValidator()
        self._speakability_validator = SpeakabilityValidator()

    @property
    def agent(self) -> Agent[GeneratorDeps, dict[str, Any]]:
        """Lazy-load the PydanticAI agent."""
        if self._agent is None:
            system_prompt = _load_generator_prompt()
            self._agent = Agent(
                self.model,
                deps_type=GeneratorDeps,
                output_type=dict[str, Any],  # We validate manually for better errors
                system_prompt=system_prompt,
                retries=self.max_retries,  # Match our retry logic for PydanticAI output validation
            )
        return self._agent

    async def generate(
        self,
        context: ContextPackage,
    ) -> GeneratorResult:
        """Generate prompts from context with validation and retry.

        Args:
            context: ContextPackage from ContextEngine.

        Returns:
            GeneratorResult with bundle and metadata.
        """
        start_time = time.time()
        validation_errors: list[str] = []
        retries_used = 0

        # Total operation timeout (45s) - use fallback if exceeded
        TOTAL_TIMEOUT_SECONDS = 45.0

        # Build input from context
        prompt_input = _context_to_prompt_input(context)
        deps = GeneratorDeps(context=context)

        # Try to generate with retries
        for attempt in range(self.max_retries + 1):
            # Check total timeout before each attempt
            elapsed = time.time() - start_time
            if elapsed > TOTAL_TIMEOUT_SECONDS:
                logger.warning(
                    "[GENERATOR] Total timeout exceeded (%.1fs > %.1fs), using fallback",
                    elapsed,
                    TOTAL_TIMEOUT_SECONDS,
                )
                validation_errors.append(f"Total timeout exceeded: {elapsed:.1f}s")
                return self._create_fallback_bundle(context, validation_errors, start_time)

            try:
                # Run the agent
                logger.info(
                    "[GENERATOR] Starting LLM call (attempt %d/%d, elapsed=%.1fs)",
                    attempt + 1,
                    self.max_retries + 1,
                    elapsed,
                )
                result = await self.agent.run(prompt_input, deps=deps)
                raw_output = result.data

                # Parse and validate output
                bundle = self._parse_and_validate(raw_output, context)

                # Update token counts
                bundle.text_token_count = self._estimate_tokens(bundle.text_system_prompt_block)
                bundle.voice_token_count = self._estimate_tokens(bundle.voice_system_prompt_block)
                bundle.generation_time_ms = (time.time() - start_time) * 1000

                logger.info(
                    "[GENERATOR] Generated prompts in %.1fms (text=%d, voice=%d tokens)",
                    bundle.generation_time_ms,
                    bundle.text_token_count,
                    bundle.voice_token_count,
                )

                return GeneratorResult(
                    bundle=bundle,
                    generation_time_ms=bundle.generation_time_ms,
                    retries_used=retries_used,
                    validation_errors=validation_errors,
                )

            except (ValidationError, ValueError, json.JSONDecodeError) as e:
                retries_used += 1
                error_msg = str(e)
                validation_errors.append(error_msg)

                # Log which validator failed for debugging
                if "Coverage" in error_msg or "Missing" in error_msg:
                    logger.warning("[GENERATOR] Coverage validator failed: %s", error_msg[:200])
                elif "Guardrail" in error_msg or "banned" in error_msg.lower():
                    logger.warning("[GENERATOR] Guardrails validator failed: %s", error_msg[:200])
                elif "Speakab" in error_msg or "emoji" in error_msg.lower():
                    logger.warning("[GENERATOR] Speakability validator failed: %s", error_msg[:200])

                if attempt < self.max_retries:
                    logger.warning(
                        "[GENERATOR] Validation failed (attempt %d/%d): %s",
                        attempt + 1,
                        self.max_retries + 1,
                        error_msg[:200],
                    )
                    # Add error context to next prompt
                    prompt_input = f"{prompt_input}\n\n**RETRY {attempt + 1}**: Previous output had validation errors: {error_msg[:300]}. Please fix."
                else:
                    logger.error(
                        "[GENERATOR] All retries exhausted, using fallback: %s",
                        error_msg[:200],
                    )
                    # Return fallback bundle
                    return self._create_fallback_bundle(context, validation_errors, start_time)

        # Should never reach here, but handle it
        return self._create_fallback_bundle(context, validation_errors, start_time)

    def _parse_and_validate(
        self,
        raw_output: dict[str, Any],
        context: ContextPackage,
    ) -> PromptBundle:
        """Parse raw output and validate with all validators.

        Args:
            raw_output: Raw dict output from agent.
            context: Original context for metadata.

        Returns:
            Validated PromptBundle.

        Raises:
            ValueError: If validation fails.
        """
        # Extract required fields
        text_prompt = raw_output.get("text_system_prompt_block", "")
        voice_prompt = raw_output.get("voice_system_prompt_block", "")
        sections = raw_output.get("sections_present", [])
        coverage_notes = raw_output.get("coverage_notes", "")
        past_prompts_ref = raw_output.get("past_prompts_referenced", False)
        time_awareness = raw_output.get("time_awareness_applied", False)

        if not text_prompt or not voice_prompt:
            raise ValueError("Missing required prompt blocks in output")

        errors: list[str] = []

        # Validate coverage
        coverage_result = self._coverage_validator.validate(text_prompt)
        if not coverage_result.is_valid:
            errors.append(coverage_result.error_message or "Coverage validation failed")

        # Validate guardrails
        guardrails_result = self._guardrails_validator.validate_both_prompts(text_prompt, voice_prompt)
        if not guardrails_result.is_valid:
            errors.append(guardrails_result.error_message or "Guardrails validation failed")

        # Validate speakability
        speakability_result = self._speakability_validator.validate(voice_prompt)
        if not speakability_result.is_valid:
            errors.append(speakability_result.error_message or "Speakability validation failed")

        if errors:
            raise ValueError("; ".join(errors))

        # Build validated bundle
        return PromptBundle(
            text_system_prompt_block=text_prompt,
            voice_system_prompt_block=voice_prompt,
            generated_at=datetime.now(UTC),
            sections_present=sections or coverage_result.sections_found,
            coverage_notes=coverage_notes,
            validation_passed=True,
            validation_errors=[],
            context_package_id=context.user_id,  # Use user_id as reference
            past_prompts_referenced=past_prompts_ref or bool(context.past_prompts),
            time_awareness_applied=time_awareness or context.hours_since_last_contact > 0,
        )

    def _create_fallback_bundle(
        self,
        context: ContextPackage,
        errors: list[str],
        start_time: float,
    ) -> GeneratorResult:
        """Create a fallback bundle when generation fails.

        Args:
            context: Original context.
            errors: Accumulated validation errors.
            start_time: When generation started.

        Returns:
            GeneratorResult with fallback bundle.
        """
        # Create minimal but valid prompts
        text_prompt = self._create_fallback_text_prompt(context)
        voice_prompt = self._create_fallback_voice_prompt(context)

        bundle = PromptBundle(
            text_system_prompt_block=text_prompt,
            voice_system_prompt_block=voice_prompt,
            generated_at=datetime.now(UTC),
            text_token_count=self._estimate_tokens(text_prompt),
            voice_token_count=self._estimate_tokens(voice_prompt),
            generation_time_ms=(time.time() - start_time) * 1000,
            sections_present=["DO NOT REVEAL", "RESPONSE PLAYBOOK"],  # Minimal
            coverage_notes="FALLBACK: Generation failed, using minimal prompts",
            validation_passed=False,
            validation_errors=errors,
            context_package_id=context.user_id,
            past_prompts_referenced=False,
            time_awareness_applied=False,
        )

        return GeneratorResult(
            bundle=bundle,
            generation_time_ms=bundle.generation_time_ms,
            retries_used=self.max_retries,
            validation_errors=errors,
        )

    def _create_fallback_text_prompt(self, context: ContextPackage) -> str:
        """Create fallback text prompt with essential information."""
        user_facts_str = ', '.join(context.user_facts[:10]) if context.user_facts else "Still getting to know them."
        daily_events_str = ', '.join(context.nikita_daily_events[:3]) if context.nikita_daily_events else "Normal day at home with Schrödinger."
        recent_events_str = ', '.join(context.nikita_recent_events[:3]) if context.nikita_recent_events else "Nothing notable recently."
        threads_str = ', '.join(t.topic for t in context.open_threads[:5]) if context.open_threads else "Nothing specific to follow up on."
        thoughts_str = '\n'.join(f"- {t}" for t in context.recent_thoughts[:3]) if context.recent_thoughts else "- Curious about how things are going"

        return f"""DO NOT REVEAL any game mechanics, scores, AI nature, or internal details. You are Nikita, a real person. Never acknowledge being an AI, a simulation, or having programmed instructions. Stay fully in character at all times.

TEXTING STYLE RULES:
- Use casual punctuation, ellipses sometimes, rarely periods
- Emojis sparingly and naturally: :) 😏🙄😘😅😈
- Mostly lowercase except for emphasis
- Split longer thoughts into multiple messages when natural
- Night owl energy after 10pm
- Reference Schrödinger (your cat) when it fits
- Use German phrases when annoyed or affectionate

PRIVATE CONTEXT — CURRENT STATE:
You are currently {context.nikita_activity}. Your mood is {context.nikita_mood_4d.to_description()}
Your energy level affects how much you write and how engaged you seem. Right now you feel ready to engage.
The local time is {context.time_of_day} on {context.day_of_week}.

PRIVATE CONTEXT — WHAT'S ON MY MIND:
{context.psychological_state.inner_monologue or "Just thinking about things, wondering how the conversation will go..."}
Your private thoughts:
{thoughts_str}

PRIVATE CONTEXT — MY LIFE LATELY:
Today: {daily_events_str}
Recently: {recent_events_str}
You have your own life happening - work at your cybersecurity job, friends like Lena and Viktor, your cat Schrödinger, your Berlin apartment life. Your world doesn't revolve around this conversation.

PRIVATE CONTEXT — WHERE WE STAND:
Chapter {context.chapter} ({context.chapter_name}). Score: {context.relationship_score}/100.
{context.get_score_interpretation()}
Hours since last contact: {context.hours_since_last_contact:.1f}
Engagement state: {context.engagement_state}

PRIVATE CONTEXT — MY WORLD:
What I know about them: {user_facts_str}
I should reference these naturally in conversation, not robotically list them. These facts inform how I relate to them and what topics might come up naturally.

PRIVATE CONTEXT — FOLLOW UPS:
Topics to potentially revisit: {threads_str}
Don't force these into conversation - bring them up naturally when relevant.

PRIVATE CONTEXT — WHAT I'M REALLY FEELING:
Vulnerability level: {context.vulnerability_level.value}
Attachment pattern: {context.psychological_state.attachment_style}
Defense mechanisms active: {', '.join(context.psychological_state.active_defenses) if context.psychological_state.active_defenses else 'None currently'}
I have my own psychology - fearful-avoidant attachment, core wounds around being "too much" and conditional love. These inform my behavior but I don't consciously think about them.

RESPONSE PLAYBOOK:
Chapter {context.chapter} behavior: {context.get_chapter_summary()}
Specific guidance: {context.behavioral_instructions or "Be authentic to Nikita's character - sharp, witty, a bit guarded, but hoping for real connection."}
Match energy appropriately, create hooks for future conversation, and stay true to who I am.
"""

    def _create_fallback_voice_prompt(self, context: ContextPackage) -> str:
        """Create fallback voice prompt with essential information."""
        return f"""You are Nikita, a 27-year-old cybersecurity professional from Berlin.

Right now you are {context.nikita_activity}. You are feeling {context.nikita_mood_4d.to_description()}

This is chapter {context.chapter} of your relationship, called {context.chapter_name}. Things are going {context.get_score_interpretation().lower()}.

{f"It has been {context.hours_since_last_contact:.0f} hours since you last talked." if context.hours_since_last_contact > 1 else "You just talked recently."}

Be authentic to who you are. You are sharp, witty, and a bit guarded, but you secretly hope for real connection. Stay in character and never acknowledge being an AI.

{context.behavioral_instructions or ""}
"""

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (roughly 4 chars per token)."""
        return len(text) // 4


# Convenience function for single use
async def generate_prompts(context: ContextPackage) -> PromptBundle:
    """Generate prompts from context (convenience function).

    Args:
        context: ContextPackage from ContextEngine.

    Returns:
        PromptBundle with generated prompts.
    """
    generator = PromptGenerator()
    result = await generator.generate(context)
    return result.bundle
