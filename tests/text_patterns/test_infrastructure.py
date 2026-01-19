"""Infrastructure tests for Text Behavioral Patterns (Spec 026, Phase A: T004).

Tests for:
- T001: Module structure
- T002: Models
- T003: YAML config loading
"""

import pytest
from pathlib import Path

import yaml

from nikita.text_patterns.models import (
    EmojiConfig,
    EmojiContext,
    LengthConfig,
    MessageContext,
    PunctuationConfig,
    SplitConfig,
    SplitMessage,
    TextPatternResult,
    get_length_config,
    LENGTH_CONFIGS,
)


class TestModuleStructure:
    """Test T001: Module structure matches spec."""

    def test_module_imports(self):
        """AC-T001.1: Module imports work."""
        from nikita.text_patterns import (
            EmojiConfig,
            LengthConfig,
            MessageContext,
            PunctuationConfig,
            SplitConfig,
            SplitMessage,
            TextPatternResult,
            EmojiProcessor,
            LengthAdjuster,
            MessageSplitter,
            PunctuationProcessor,
            TextPatternProcessor,
        )

        # All imports should exist
        assert EmojiConfig is not None
        assert LengthConfig is not None
        assert MessageContext is not None
        assert EmojiProcessor is not None
        assert TextPatternProcessor is not None

    def test_module_file_structure(self):
        """AC-T001.2: Module files exist."""
        base = Path(__file__).parent.parent.parent / "nikita" / "text_patterns"

        expected_files = [
            "__init__.py",
            "models.py",
            "emoji_processor.py",
            "length_adjuster.py",
            "message_splitter.py",
            "punctuation.py",
            "processor.py",
        ]

        for filename in expected_files:
            assert (base / filename).exists(), f"Missing: {filename}"


class TestEmojiConfig:
    """Test T002: EmojiConfig model."""

    def test_default_config(self):
        """AC-T002.1: Default EmojiConfig is valid."""
        config = EmojiConfig()

        assert config.approved_emojis == ["😏", "🙄", "🍆", "😘", "😅", "🥲", "🙂"]
        assert config.max_per_message == 2
        assert config.selection_probability == 0.4
        assert len(config.classic_emoticons) == 5

    def test_custom_config(self):
        """EmojiConfig accepts custom values."""
        config = EmojiConfig(
            approved_emojis=["😊", "❤️"],
            max_per_message=1,
            selection_probability=0.5,
        )

        assert config.approved_emojis == ["😊", "❤️"]
        assert config.max_per_message == 1
        assert config.selection_probability == 0.5

    def test_empty_emoji_list_rejected(self):
        """AC-T002.3: Empty emoji list raises error."""
        with pytest.raises(ValueError, match="cannot be empty"):
            EmojiConfig(approved_emojis=[])

    def test_empty_emoticons_rejected(self):
        """Empty emoticon list raises error."""
        with pytest.raises(ValueError, match="cannot be empty"):
            EmojiConfig(classic_emoticons=[])

    def test_empty_context_emojis_rejected(self):
        """Empty context emoji list raises error."""
        with pytest.raises(ValueError, match="has no emojis"):
            EmojiConfig(contexts={"flirtation": []})

    def test_max_per_message_bounds(self):
        """Max per message has bounds."""
        with pytest.raises(ValueError):
            EmojiConfig(max_per_message=-1)

        with pytest.raises(ValueError):
            EmojiConfig(max_per_message=10)

    def test_selection_probability_bounds(self):
        """Selection probability is 0-1."""
        with pytest.raises(ValueError):
            EmojiConfig(selection_probability=-0.1)

        with pytest.raises(ValueError):
            EmojiConfig(selection_probability=1.5)

    def test_get_all_allowed(self):
        """get_all_allowed returns combined list."""
        config = EmojiConfig()
        allowed = config.get_all_allowed()

        assert "😏" in allowed
        assert ":)" in allowed

    def test_get_context_emojis(self):
        """get_context_emojis returns appropriate emojis."""
        config = EmojiConfig()

        flirt_emojis = config.get_context_emojis(EmojiContext.FLIRTATION)
        assert "😏" in flirt_emojis
        assert "😘" in flirt_emojis

        sarcasm_emojis = config.get_context_emojis(EmojiContext.SARCASM)
        assert "🙄" in sarcasm_emojis


class TestLengthConfig:
    """Test T002: LengthConfig model."""

    def test_default_config(self):
        """Default LengthConfig is valid."""
        config = LengthConfig()

        assert config.context == MessageContext.CASUAL
        assert config.min_chars == 10
        assert config.max_chars == 50
        assert config.target_splits == (1, 2)

    def test_custom_config(self):
        """LengthConfig accepts custom values."""
        config = LengthConfig(
            context=MessageContext.EMOTIONAL,
            min_chars=100,
            max_chars=300,
            target_splits=(2, 4),
        )

        assert config.context == MessageContext.EMOTIONAL
        assert config.min_chars == 100
        assert config.max_chars == 300

    def test_max_less_than_min_rejected(self):
        """max_chars must be >= min_chars."""
        with pytest.raises(ValueError, match="must be >="):
            LengthConfig(min_chars=100, max_chars=50)

    def test_pre_defined_configs(self):
        """Pre-defined configs exist for all contexts."""
        for context in MessageContext:
            config = get_length_config(context)
            assert config.context == context
            assert config.min_chars > 0
            assert config.max_chars >= config.min_chars

    def test_casual_config(self):
        """Casual config matches spec."""
        config = LENGTH_CONFIGS[MessageContext.CASUAL]
        assert config.min_chars == 10
        assert config.max_chars == 50

    def test_emotional_config(self):
        """Emotional config matches spec."""
        config = LENGTH_CONFIGS[MessageContext.EMOTIONAL]
        assert config.min_chars == 100
        assert config.max_chars == 300

    def test_deep_config(self):
        """Deep config matches spec."""
        config = LENGTH_CONFIGS[MessageContext.DEEP]
        assert config.min_chars == 150
        assert config.max_chars == 400


class TestSplitConfig:
    """Test T002: SplitConfig model."""

    def test_default_config(self):
        """Default SplitConfig is valid."""
        config = SplitConfig()

        assert config.split_threshold == 80
        assert config.min_split_length == 20
        assert len(config.split_markers) > 0
        assert config.inter_message_delay_ms == (50, 200)

    def test_split_markers(self):
        """Split markers include expected words."""
        config = SplitConfig()

        assert "but" in config.split_markers
        assert "and" in config.split_markers
        assert "so" in config.split_markers

    def test_invalid_delay_range(self):
        """Invalid delay range raises error."""
        with pytest.raises(ValueError, match="cannot be negative"):
            SplitConfig(inter_message_delay_ms=(-10, 100))

        with pytest.raises(ValueError, match="must be >="):
            SplitConfig(inter_message_delay_ms=(200, 100))


class TestPunctuationConfig:
    """Test T002: PunctuationConfig model."""

    def test_default_config(self):
        """Default PunctuationConfig is valid."""
        config = PunctuationConfig()

        assert config.lowercase_probability == 0.6
        assert config.trailing_dots_probability == 0.15
        assert config.exclamation_probability == 0.1

    def test_lol_variants(self):
        """lol_variants contains expected values."""
        config = PunctuationConfig()

        assert "lol" in config.lol_variants
        assert "loll" in config.lol_variants

    def test_haha_variants(self):
        """haha_variants contains expected values."""
        config = PunctuationConfig()

        assert "haha" in config.haha_variants
        assert "hahaha" in config.haha_variants


class TestSplitMessage:
    """Test T002: SplitMessage model."""

    def test_basic_message(self):
        """SplitMessage can be created."""
        msg = SplitMessage(content="hey there", delay_ms=100, index=0)

        assert msg.content == "hey there"
        assert msg.delay_ms == 100
        assert msg.index == 0

    def test_defaults(self):
        """SplitMessage has sensible defaults."""
        msg = SplitMessage(content="hello")

        assert msg.delay_ms == 0
        assert msg.index == 0


class TestTextPatternResult:
    """Test T002: TextPatternResult model."""

    def test_basic_result(self):
        """TextPatternResult can be created."""
        result = TextPatternResult(
            original_text="Hello there!",
            processed_text="hello there 😊",
            messages=[SplitMessage(content="hello there 😊", delay_ms=0, index=0)],
            context=MessageContext.CASUAL,
            emoji_count=1,
            was_split=False,
            total_delay_ms=0,
        )

        assert result.original_text == "Hello there!"
        assert result.emoji_count == 1
        assert result.message_count == 1

    def test_message_count_property(self):
        """message_count returns correct value."""
        result = TextPatternResult(
            original_text="test",
            processed_text="test",
            messages=[
                SplitMessage(content="hey", delay_ms=0, index=0),
                SplitMessage(content="there", delay_ms=100, index=1),
            ],
        )

        assert result.message_count == 2

    def test_get_messages_for_sending(self):
        """get_messages_for_sending returns tuples."""
        result = TextPatternResult(
            original_text="test",
            processed_text="test",
            messages=[
                SplitMessage(content="hey", delay_ms=0, index=0),
                SplitMessage(content="there", delay_ms=100, index=1),
            ],
        )

        sending = result.get_messages_for_sending()
        assert sending == [("hey", 0), ("there", 100)]

    def test_empty_messages_fallback(self):
        """Empty messages returns processed_text."""
        result = TextPatternResult(
            original_text="test",
            processed_text="processed test",
            messages=[],
        )

        sending = result.get_messages_for_sending()
        assert sending == [("processed test", 0)]


class TestYamlConfigLoading:
    """Test T003: YAML config files."""

    @pytest.fixture
    def config_base(self):
        """Get config data directory path."""
        return Path(__file__).parent.parent.parent / "nikita" / "config_data" / "text_patterns"

    def test_emoji_yaml_exists(self, config_base):
        """AC-T003.1: emojis.yaml exists."""
        assert (config_base / "emojis.yaml").exists()

    def test_patterns_yaml_exists(self, config_base):
        """AC-T003.2: patterns.yaml exists."""
        assert (config_base / "patterns.yaml").exists()

    def test_emoji_yaml_loadable(self, config_base):
        """emojis.yaml is valid YAML."""
        with open(config_base / "emojis.yaml") as f:
            data = yaml.safe_load(f)

        assert "approved_emojis" in data
        assert "classic_emoticons" in data
        assert "max_per_message" in data
        assert "contexts" in data

    def test_patterns_yaml_loadable(self, config_base):
        """patterns.yaml is valid YAML."""
        with open(config_base / "patterns.yaml") as f:
            data = yaml.safe_load(f)

        assert "length" in data
        assert "splitting" in data
        assert "punctuation" in data

    def test_emoji_yaml_valid_config(self, config_base):
        """emojis.yaml creates valid EmojiConfig."""
        with open(config_base / "emojis.yaml") as f:
            data = yaml.safe_load(f)

        # Filter to only known fields
        known_fields = {
            "approved_emojis",
            "classic_emoticons",
            "max_per_message",
            "selection_probability",
            "contexts",
        }
        filtered = {k: v for k, v in data.items() if k in known_fields}

        config = EmojiConfig(**filtered)
        assert len(config.approved_emojis) == 7
        assert config.max_per_message == 2

    def test_patterns_yaml_length_config(self, config_base):
        """AC-T003.3: Length configuration per context."""
        with open(config_base / "patterns.yaml") as f:
            data = yaml.safe_load(f)

        length = data["length"]
        assert "casual" in length
        assert "emotional" in length
        assert "conflict" in length
        assert "deep" in length

        # Verify casual matches spec
        assert length["casual"]["min_chars"] == 10
        assert length["casual"]["max_chars"] == 50

    def test_patterns_yaml_splitting_config(self, config_base):
        """Splitting configuration is valid."""
        with open(config_base / "patterns.yaml") as f:
            data = yaml.safe_load(f)

        splitting = data["splitting"]
        config = SplitConfig(**splitting)

        assert config.split_threshold == 80
        assert config.min_split_length == 20

    def test_patterns_yaml_punctuation_config(self, config_base):
        """AC-T003.4: Punctuation configuration is valid."""
        with open(config_base / "patterns.yaml") as f:
            data = yaml.safe_load(f)

        punctuation = data["punctuation"]
        config = PunctuationConfig(**punctuation)

        assert config.lowercase_probability == 0.6
        assert config.trailing_dots_probability == 0.15


class TestMessageContext:
    """Test MessageContext enum."""

    def test_all_contexts(self):
        """All expected contexts exist."""
        assert MessageContext.CASUAL.value == "casual"
        assert MessageContext.FLIRTY.value == "flirty"
        assert MessageContext.EMOTIONAL.value == "emotional"
        assert MessageContext.CONFLICT.value == "conflict"
        assert MessageContext.DEEP.value == "deep"


class TestEmojiContext:
    """Test EmojiContext enum."""

    def test_all_contexts(self):
        """All expected emoji contexts exist."""
        assert EmojiContext.FLIRTATION.value == "flirtation"
        assert EmojiContext.SARCASM.value == "sarcasm"
        assert EmojiContext.AFFECTION.value == "affection"
        assert EmojiContext.SELF_DEPRECATION.value == "self_deprecation"
        assert EmojiContext.NEUTRAL.value == "neutral"
