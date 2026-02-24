"""Centralized LLM model registry — single source of truth.

All consumers import model identifiers from here.
Model upgrade = edit settings.py defaults only.

Format: "anthropic:{model-id}" (Pydantic AI provider prefix).
"""

from nikita.config.settings import get_settings


class Models:
    """Single source of truth for all LLM model identifiers.

    Tiers:
        haiku()  — Fast/cheap: scoring, detection, enrichment, summaries
        sonnet() — Main reasoning: text agent, extraction, judgment, events
        opus()   — Deep analysis: psyche agent
    """

    @staticmethod
    def haiku() -> str:
        """Fast/cheap model for scoring, detection, enrichment."""
        return get_settings().meta_prompt_model  # "anthropic:claude-haiku-4-5-20251001"

    @staticmethod
    def sonnet() -> str:
        """Main reasoning model for text agent, extraction, summary, judgment."""
        s = get_settings()
        model = s.anthropic_model
        if not model.startswith("anthropic:"):
            model = f"anthropic:{model}"
        return model

    @staticmethod
    def opus() -> str:
        """Deep analysis model for psyche agent."""
        return "anthropic:claude-opus-4-6"
