"""Configuration module for Nikita."""

from nikita.config.settings import Settings, get_settings
from nikita.config.elevenlabs import ElevenLabsConfig, get_agent_id
from nikita.config.loader import ConfigLoader, get_config
from nikita.config.enums import (
    Chapter,
    EngagementState,
    GameStatus,
    Metric,
    Mood,
    TimeOfDay,
    ViceCategory,
    ViceIntensity,
)
from nikita.config.prompt_loader import (
    PromptLoader,
    MissingVariableError,
    get_prompt_loader,
)
from nikita.config.experiments import (
    ExperimentLoader,
    ConfigurationError,
    deep_merge,
)

__all__ = [
    # Settings
    "Settings",
    "get_settings",
    # ElevenLabs
    "ElevenLabsConfig",
    "get_agent_id",
    # Config loader
    "ConfigLoader",
    "get_config",
    # Prompt loader
    "PromptLoader",
    "MissingVariableError",
    "get_prompt_loader",
    # Experiments
    "ExperimentLoader",
    "ConfigurationError",
    "deep_merge",
    # Enums
    "Chapter",
    "EngagementState",
    "GameStatus",
    "Metric",
    "Mood",
    "TimeOfDay",
    "ViceCategory",
    "ViceIntensity",
]
