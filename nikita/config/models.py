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
    def _normalize(model_id: str) -> str:
        """Ensure model ID has the 'anthropic:' prefix required by Pydantic AI."""
        if not model_id.startswith("anthropic:"):
            return f"anthropic:{model_id}"
        return model_id

    @staticmethod
    def haiku() -> str:
        """Fast/cheap model for scoring, detection, enrichment."""
        return Models._normalize(get_settings().meta_prompt_model)

    @staticmethod
    def sonnet() -> str:
        """Main reasoning model for text agent, extraction, summary, judgment."""
        return Models._normalize(get_settings().anthropic_model)

    @staticmethod
    def opus() -> str:
        """Deep analysis model for psyche agent."""
        return Models._normalize(get_settings().psyche_model)
