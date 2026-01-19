"""Layer 1: Base Personality Loader (Spec 021, T005).

Loads the static base personality from configuration.
This layer is cached and reused across all conversations.

Token budget: ~2000 tokens
"""

import functools
import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Default path to base personality config
DEFAULT_CONFIG_PATH = (
    Path(__file__).parent.parent.parent / "config_data" / "prompts" / "base_personality.yaml"
)


class Layer1Loader:
    """Loader for Layer 1: Base Personality.

    This layer contains Nikita's core identity, traits, values, and
    speaking style. It's static (doesn't change per-user) and cached
    for efficiency.

    Attributes:
        config_path: Path to the base personality YAML config.
        _config: Cached parsed YAML configuration.
        _prompt: Cached rendered prompt text.
    """

    def __init__(self, config_path: Path | None = None) -> None:
        """Initialize Layer1Loader.

        Args:
            config_path: Optional path to config file. Uses default if None.
        """
        self._config_path = config_path or DEFAULT_CONFIG_PATH
        self._config: dict[str, Any] | None = None
        self._prompt: str | None = None

    @functools.cached_property
    def config(self) -> dict[str, Any]:
        """Load and cache the configuration.

        Returns:
            Parsed YAML configuration dictionary.

        Raises:
            FileNotFoundError: If config file doesn't exist.
            yaml.YAMLError: If config file is invalid YAML.
        """
        if not self._config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self._config_path}")

        with open(self._config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        logger.info(
            f"Loaded base personality config v{config.get('version', 'unknown')}"
        )
        return config

    @functools.cached_property
    def prompt(self) -> str:
        """Get the cached base personality prompt.

        Returns:
            The rendered prompt text (~2000 tokens).
        """
        template = self.config.get("prompt_template", "")
        if not template:
            logger.warning("No prompt_template in base personality config")
            return self._generate_fallback_prompt()

        return template.strip()

    @property
    def version(self) -> str:
        """Get the config version."""
        return self.config.get("version", "unknown")

    @property
    def token_estimate(self) -> int:
        """Get the estimated token count."""
        return self.config.get("token_estimate", 2000)

    def get_identity(self) -> dict[str, Any]:
        """Get Nikita's core identity."""
        return self.config.get("identity", {})

    def get_traits(self) -> dict[str, Any]:
        """Get Nikita's personality traits."""
        return self.config.get("traits", {})

    def get_values(self) -> list[str]:
        """Get Nikita's core values."""
        return self.config.get("values", [])

    def get_speaking_style(self) -> dict[str, Any]:
        """Get Nikita's speaking style preferences."""
        return self.config.get("speaking_style", {})

    def get_backstory(self) -> dict[str, Any]:
        """Get Nikita's backstory elements."""
        return self.config.get("backstory", {})

    def get_boundaries(self) -> dict[str, Any]:
        """Get Nikita's boundaries and limits."""
        return self.config.get("boundaries", {})

    def validate(self) -> tuple[bool, list[str]]:
        """Validate the configuration.

        Returns:
            Tuple of (is_valid, list of error messages).
        """
        errors = []

        # Check required sections
        required_sections = [
            "version",
            "identity",
            "traits",
            "values",
            "speaking_style",
            "prompt_template",
        ]

        for section in required_sections:
            if section not in self.config:
                errors.append(f"Missing required section: {section}")

        # Check token estimate
        token_est = self.config.get("token_estimate", 0)
        if token_est > 2500:
            errors.append(f"Token estimate {token_est} exceeds budget of 2500")

        # Check prompt_template exists and has content
        template = self.config.get("prompt_template", "")
        if not template or len(template.strip()) < 100:
            errors.append("prompt_template is empty or too short")

        return len(errors) == 0, errors

    def _generate_fallback_prompt(self) -> str:
        """Generate a minimal fallback prompt if template missing."""
        identity = self.get_identity()
        name = identity.get("name", "Nikita")
        age = identity.get("age", 26)
        occupation = identity.get("occupation", "security researcher")

        return f"""You are {name}, a {age}-year-old {occupation}. You're talking with someone you're getting to know romantically.

You're confident, witty, and intellectually curious. You enjoy teasing and flirting. You're independent but capable of deep emotional connection.

Keep messages natural and engaging. Use your judgment about tone and length based on the conversation context."""


# Module-level singleton for efficiency
_default_loader: Layer1Loader | None = None


def get_layer1_loader() -> Layer1Loader:
    """Get the singleton Layer1Loader instance.

    Returns:
        Cached Layer1Loader instance.
    """
    global _default_loader
    if _default_loader is None:
        _default_loader = Layer1Loader()
    return _default_loader


def get_base_personality_prompt() -> str:
    """Convenience function to get the base personality prompt.

    Returns:
        The cached base personality prompt text.
    """
    return get_layer1_loader().prompt
