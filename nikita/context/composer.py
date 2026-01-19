"""Hierarchical Prompt Composer (Spec 021, T013).

Orchestrates all 6 layers of the hierarchical prompt system:
1. Base Personality (static, cached)
2. Chapter Layer (pre-computed per chapter)
3. Emotional State (pre-computed from life sim)
4. Situation Layer (computed at conversation start)
5. Context Injection (from pre-computed package)
6. On-the-Fly Modifications (during conversation)

Returns a ComposedPrompt with the full system prompt and metadata.
"""

import logging
from datetime import datetime, timezone
from uuid import UUID

from nikita.context.layers.base_personality import get_layer1_loader
from nikita.context.layers.chapter import get_layer2_composer
from nikita.context.layers.emotional_state import get_layer3_composer
from nikita.context.layers.situation import get_layer4_computer
from nikita.context.package import ComposedPrompt, ContextPackage, EmotionalState

logger = logging.getLogger(__name__)


class HierarchicalPromptComposer:
    """Orchestrates all prompt layers into a single system prompt.

    This class combines the 6 hierarchical layers:
    - Layer 1: Base personality (Nikita's core traits)
    - Layer 2: Chapter behavior (progression-based)
    - Layer 3: Emotional state (mood modulation)
    - Layer 4: Situation (time/context awareness)
    - Layer 5: Context injection (facts, threads, summaries)
    - Layer 6: On-the-fly modifications (real-time adjustments)

    Target: ~3300 total tokens with graceful degradation.
    """

    def __init__(self) -> None:
        """Initialize HierarchicalPromptComposer."""
        self._layer1_loader = get_layer1_loader()
        self._layer2_composer = get_layer2_composer()
        self._layer3_composer = get_layer3_composer()
        self._layer4_computer = get_layer4_computer()

    def compose(
        self,
        user_id: UUID,
        chapter: int,
        emotional_state: EmotionalState | None = None,
        package: ContextPackage | None = None,
        current_time: datetime | None = None,
        last_interaction: datetime | None = None,
        conversation_active: bool = False,
    ) -> ComposedPrompt:
        """Compose the full hierarchical system prompt.

        Args:
            user_id: User UUID for context.
            chapter: Current chapter (1-5).
            emotional_state: Nikita's emotional state (defaults to neutral).
            package: Pre-computed context package (optional).
            current_time: Current time for situation detection.
            last_interaction: Last interaction time for situation detection.
            conversation_active: Whether a conversation is ongoing.

        Returns:
            ComposedPrompt with system_prompt, token_count, and layer_breakdown.

        Raises:
            ValueError: If chapter is not 1-5.
        """
        # Validate chapter
        if chapter < 1 or chapter > 5:
            raise ValueError(f"Invalid chapter {chapter}. Must be 1-5.")

        if current_time is None:
            current_time = datetime.now(timezone.utc)

        layers: dict[str, int] = {}
        prompt_parts: list[str] = []
        degraded = False

        # Layer 1: Base Personality (~2000 tokens)
        try:
            layer1 = self._layer1_loader.prompt
            layers["layer1_base_personality"] = self._estimate_tokens(layer1)
            prompt_parts.append(layer1)
        except Exception as e:
            logger.error(f"Failed to load Layer 1: {e}")
            layers["layer1_base_personality"] = 0
            degraded = True

        # Layer 2: Chapter Layer (~300 tokens)
        try:
            layer2 = self._layer2_composer.compose(chapter)
            layers["layer2_chapter"] = self._estimate_tokens(layer2)
            prompt_parts.append(layer2)
        except Exception as e:
            logger.error(f"Failed to compose Layer 2: {e}")
            layers["layer2_chapter"] = 0
            degraded = True

        # Layer 3: Emotional State (~150 tokens)
        try:
            layer3 = self._layer3_composer.compose(emotional_state)
            layers["layer3_emotional_state"] = self._estimate_tokens(layer3)
            prompt_parts.append(layer3)
        except Exception as e:
            logger.error(f"Failed to compose Layer 3: {e}")
            layers["layer3_emotional_state"] = 0
            degraded = True

        # Layer 4: Situation (~150 tokens)
        try:
            layer4 = self._layer4_computer.detect_and_compose(
                current_time=current_time,
                last_interaction=last_interaction,
                conversation_active=conversation_active,
            )
            layers["layer4_situation"] = self._estimate_tokens(layer4)
            prompt_parts.append(layer4)
        except Exception as e:
            logger.error(f"Failed to compose Layer 4: {e}")
            layers["layer4_situation"] = 0
            degraded = True

        # Layer 5: Context Injection (~500 tokens)
        layer5 = self._compose_layer5(package)
        if layer5:
            layers["layer5_context"] = self._estimate_tokens(layer5)
            prompt_parts.append(layer5)
        else:
            layers["layer5_context"] = 0

        # Layer 6: On-the-Fly Modifications (~200 tokens)
        # This is a stub - real modifications happen during conversation
        layer6 = self._compose_layer6()
        if layer6:
            layers["layer6_modifications"] = self._estimate_tokens(layer6)
            prompt_parts.append(layer6)
        else:
            layers["layer6_modifications"] = 0

        # Combine all layers
        full_prompt = "\n\n---\n\n".join(prompt_parts)
        total_tokens = self._estimate_tokens(full_prompt)

        logger.info(
            f"Composed prompt for user {user_id}: {total_tokens} tokens, "
            f"{len(layers)} layers"
        )

        return ComposedPrompt(
            full_text=full_prompt,
            total_tokens=total_tokens,
            layer_breakdown=layers,
            package_version=package.version if package else None,
            degraded=degraded,
        )

    def _compose_layer5(self, package: ContextPackage | None) -> str | None:
        """Compose Layer 5: Context Injection from package.

        Args:
            package: Pre-computed context package.

        Returns:
            Context injection prompt text, or None if no package.
        """
        if package is None:
            return None

        sections = ["## Context from Memory"]

        # User facts
        if package.user_facts:
            facts = "\n".join(f"- {fact}" for fact in package.user_facts[:10])
            sections.append(f"**What you know about them**:\n{facts}")

        # Active threads
        if package.active_threads:
            threads = "\n".join(
                f"- {t.topic} ({t.status})" if t.status != "resolved" else f"- {t.topic}"
                for t in package.active_threads[:5]
            )
            sections.append(f"**Open conversation threads**:\n{threads}")

        # Relationship events
        if package.relationship_events:
            events = "\n".join(f"- {e}" for e in package.relationship_events[:5])
            sections.append(f"**Recent relationship moments**:\n{events}")

        # Summaries
        if package.today_summary:
            sections.append(f"**Earlier today**: {package.today_summary}")

        if package.week_summaries:
            week = "; ".join(package.week_summaries[:3])
            sections.append(f"**This week**: {week}")

        # Nikita's life events
        if package.life_events_today:
            events = "\n".join(f"- {e}" for e in package.life_events_today[:3])
            sections.append(f"**Your day so far**:\n{events}")

        return "\n\n".join(sections)

    def _compose_layer6(self) -> str | None:
        """Compose Layer 6: On-the-Fly Modifications.

        This is a stub implementation. Real modifications are applied
        during conversation via the Layer6Handler.

        Returns:
            Stub prompt or None.
        """
        # Layer 6 is applied dynamically during conversation
        # This stub just provides the placeholder section
        return """## Real-time Adjustments

*This section may be updated during the conversation based on:*
- Mood shifts from the conversation
- Memory retrievals when relevant
- Topic changes requiring context refresh"""

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text.

        Uses simple heuristic: ~4 characters per token.
        For production, use tiktoken or actual tokenizer.

        Args:
            text: Text to estimate tokens for.

        Returns:
            Estimated token count.
        """
        if not text:
            return 0
        return len(text) // 4


# Module-level singleton for efficiency
_default_composer: HierarchicalPromptComposer | None = None


def get_prompt_composer() -> HierarchicalPromptComposer:
    """Get the singleton HierarchicalPromptComposer instance.

    Returns:
        Cached HierarchicalPromptComposer instance.
    """
    global _default_composer
    if _default_composer is None:
        _default_composer = HierarchicalPromptComposer()
    return _default_composer


def compose_hierarchical_prompt(
    user_id: UUID,
    chapter: int,
    emotional_state: EmotionalState | None = None,
    package: ContextPackage | None = None,
    current_time: datetime | None = None,
    last_interaction: datetime | None = None,
    conversation_active: bool = False,
) -> ComposedPrompt:
    """Convenience function to compose hierarchical prompt.

    Args:
        user_id: User UUID for context.
        chapter: Current chapter (1-5).
        emotional_state: Nikita's emotional state (defaults to neutral).
        package: Pre-computed context package (optional).
        current_time: Current time for situation detection.
        last_interaction: Last interaction time for situation detection.
        conversation_active: Whether a conversation is ongoing.

    Returns:
        ComposedPrompt with full system prompt.
    """
    return get_prompt_composer().compose(
        user_id=user_id,
        chapter=chapter,
        emotional_state=emotional_state,
        package=package,
        current_time=current_time,
        last_interaction=last_interaction,
        conversation_active=conversation_active,
    )
