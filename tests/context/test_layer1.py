"""Tests for Layer1Loader (Spec 021, T005).

AC-T005.1: Layer1Loader class loads base personality from config
AC-T005.2: Caching mechanism (load once, reuse)
AC-T005.3: Token count validation (~2000 tokens)
AC-T005.4: Unit tests for loader
"""

from pathlib import Path

import pytest

from nikita.context.layers.base_personality import (
    Layer1Loader,
    get_base_personality_prompt,
    get_layer1_loader,
)


class TestLayer1Loader:
    """Tests for Layer1Loader class."""

    def test_init_default_path(self):
        """AC-T005.1: Loader initializes with default config path."""
        loader = Layer1Loader()
        assert loader._config_path.name == "base_personality.yaml"

    def test_init_custom_path(self, tmp_path):
        """AC-T005.1: Loader accepts custom config path."""
        custom_path = tmp_path / "custom.yaml"
        loader = Layer1Loader(config_path=custom_path)
        assert loader._config_path == custom_path

    def test_load_config_from_default(self):
        """AC-T005.1: Loads config from default path."""
        loader = Layer1Loader()
        config = loader.config

        assert isinstance(config, dict)
        assert "version" in config
        assert "identity" in config
        assert "traits" in config

    def test_config_cached(self):
        """AC-T005.2: Config is cached after first load."""
        loader = Layer1Loader()

        # First access loads config
        config1 = loader.config
        # Second access returns cached config
        config2 = loader.config

        assert config1 is config2

    def test_prompt_cached(self):
        """AC-T005.2: Prompt is cached after first load."""
        loader = Layer1Loader()

        # First access generates prompt
        prompt1 = loader.prompt
        # Second access returns cached prompt
        prompt2 = loader.prompt

        assert prompt1 is prompt2

    def test_prompt_contains_nikita(self):
        """AC-T005.1: Prompt contains Nikita's identity."""
        loader = Layer1Loader()
        prompt = loader.prompt

        assert "Nikita" in prompt
        assert len(prompt) > 100

    def test_token_estimate_in_budget(self):
        """AC-T005.3: Token estimate is within budget (~2000)."""
        loader = Layer1Loader()
        estimate = loader.token_estimate

        assert estimate <= 2500, f"Token estimate {estimate} exceeds budget"
        assert estimate >= 1000, f"Token estimate {estimate} seems too low"

    def test_version_property(self):
        """AC-T005.1: Version property returns config version."""
        loader = Layer1Loader()
        version = loader.version

        assert version == "1.0.0"

    def test_get_identity(self):
        """AC-T005.1: get_identity returns identity section."""
        loader = Layer1Loader()
        identity = loader.get_identity()

        assert identity["name"] == "Nikita"
        assert identity["age"] == 26
        assert "occupation" in identity

    def test_get_traits(self):
        """AC-T005.1: get_traits returns traits section."""
        loader = Layer1Loader()
        traits = loader.get_traits()

        assert "openness" in traits
        assert "wit" in traits
        assert traits["openness"] >= 1
        assert traits["openness"] <= 10

    def test_get_values(self):
        """AC-T005.1: get_values returns list of values."""
        loader = Layer1Loader()
        values = loader.get_values()

        assert isinstance(values, list)
        assert len(values) >= 3
        assert any("authentic" in v.lower() for v in values)

    def test_get_speaking_style(self):
        """AC-T005.1: get_speaking_style returns style preferences."""
        loader = Layer1Loader()
        style = loader.get_speaking_style()

        assert "tone" in style
        assert "emoji_usage" in style

    def test_get_backstory(self):
        """AC-T005.1: get_backstory returns backstory elements."""
        loader = Layer1Loader()
        backstory = loader.get_backstory()

        assert "education" in backstory
        assert "career" in backstory

    def test_get_boundaries(self):
        """AC-T005.1: get_boundaries returns boundaries."""
        loader = Layer1Loader()
        boundaries = loader.get_boundaries()

        assert "hard_limits" in boundaries
        assert isinstance(boundaries["hard_limits"], list)

    def test_validate_success(self):
        """AC-T005.1: validate returns True for valid config."""
        loader = Layer1Loader()
        is_valid, errors = loader.validate()

        assert is_valid, f"Validation failed: {errors}"
        assert errors == []

    def test_validate_missing_section(self, tmp_path):
        """AC-T005.1: validate catches missing sections."""
        # Create config missing required sections
        config_path = tmp_path / "incomplete.yaml"
        config_path.write_text("version: '1.0.0'\n")

        loader = Layer1Loader(config_path=config_path)
        is_valid, errors = loader.validate()

        assert not is_valid
        assert any("identity" in e for e in errors)

    def test_file_not_found(self, tmp_path):
        """AC-T005.1: Raises FileNotFoundError for missing file."""
        loader = Layer1Loader(config_path=tmp_path / "nonexistent.yaml")

        with pytest.raises(FileNotFoundError):
            _ = loader.config


class TestLayer1ModuleFunctions:
    """Tests for module-level convenience functions."""

    def test_get_layer1_loader_singleton(self):
        """AC-T005.2: get_layer1_loader returns singleton."""
        loader1 = get_layer1_loader()
        loader2 = get_layer1_loader()

        assert loader1 is loader2

    def test_get_base_personality_prompt(self):
        """AC-T005.1: get_base_personality_prompt returns prompt."""
        prompt = get_base_personality_prompt()

        assert isinstance(prompt, str)
        assert "Nikita" in prompt
        assert len(prompt) > 100


class TestLayer1FallbackPrompt:
    """Tests for fallback prompt generation."""

    def test_fallback_prompt_generated(self, tmp_path):
        """AC-T005.1: Fallback prompt generated when template missing."""
        # Create config without prompt_template
        config_path = tmp_path / "no_template.yaml"
        config_path.write_text("""
version: '1.0.0'
identity:
  name: TestNikita
  age: 25
  occupation: tester
traits: {}
values: []
speaking_style: {}
""")

        loader = Layer1Loader(config_path=config_path)
        prompt = loader.prompt

        assert "TestNikita" in prompt
        assert "25" in prompt
        assert len(prompt) > 50
