"""Tests for PromptLoader - TDD for US-4 (T4.1-T4.5).

Acceptance Criteria:
- AC-4.1.1: PromptLoader class exists in prompt_loader.py
- AC-4.1.2: load(path) method reads .prompt files
- AC-4.1.3: Returns string content
- AC-4.2.1: {{variable}} syntax replaced with values
- AC-4.2.2: render(path, **kwargs) method accepts variables
- AC-4.2.3: Nested variables work {{user.name}}
- AC-4.3.1: MissingVariableError exception defined
- AC-4.3.2: Raised when template has unreplaced {{var}}
- AC-4.3.3: Error message includes missing variable name
- AC-4.4.1: Prompts cached after first load
- AC-4.4.2: @lru_cache or dict-based cache
- AC-4.4.3: Subsequent loads < 1ms
- AC-4.5.1: cache_clear() method exists
- AC-4.5.2: Clears all cached prompts
- AC-4.5.3: Next load reads from disk
"""

import os
import time
import tempfile
import pytest
from pathlib import Path


class TestPromptLoaderImports:
    """Test that PromptLoader module is importable."""

    def test_ac_4_1_1_prompt_loader_class_exists(self):
        """AC-4.1.1: PromptLoader class exists in prompt_loader.py."""
        from nikita.config.prompt_loader import PromptLoader
        assert PromptLoader is not None

    def test_missing_variable_error_importable(self):
        """AC-4.3.1: MissingVariableError exception defined."""
        from nikita.config.prompt_loader import MissingVariableError
        assert issubclass(MissingVariableError, Exception)

    def test_get_prompt_loader_importable(self):
        """Convenience function should be importable."""
        from nikita.config.prompt_loader import get_prompt_loader
        assert callable(get_prompt_loader)


class TestPromptLoaderLoad:
    """Test load() method for reading .prompt files."""

    @pytest.fixture
    def temp_prompt_file(self):
        """Create a temporary .prompt file for testing."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.prompt', delete=False
        ) as f:
            f.write("This is a test prompt.\nWith multiple lines.")
            f.flush()
            yield f.name
        os.unlink(f.name)

    def test_ac_4_1_2_load_reads_prompt_file(self, temp_prompt_file):
        """AC-4.1.2: load(path) method reads .prompt files."""
        from nikita.config.prompt_loader import PromptLoader

        loader = PromptLoader()
        content = loader.load(temp_prompt_file)

        assert "This is a test prompt" in content

    def test_ac_4_1_3_load_returns_string(self, temp_prompt_file):
        """AC-4.1.3: Returns string content."""
        from nikita.config.prompt_loader import PromptLoader

        loader = PromptLoader()
        content = loader.load(temp_prompt_file)

        assert isinstance(content, str)
        assert len(content) > 0

    def test_load_nonexistent_file_raises_error(self):
        """Loading nonexistent file should raise FileNotFoundError."""
        from nikita.config.prompt_loader import PromptLoader

        loader = PromptLoader()
        with pytest.raises(FileNotFoundError):
            loader.load("/nonexistent/path/to/file.prompt")

    def test_load_preserves_newlines(self, temp_prompt_file):
        """Load should preserve newlines in content."""
        from nikita.config.prompt_loader import PromptLoader

        loader = PromptLoader()
        content = loader.load(temp_prompt_file)

        assert "\n" in content


class TestPromptLoaderRender:
    """Test render() method with variable substitution."""

    @pytest.fixture
    def template_prompt_file(self):
        """Create a template .prompt file with variables."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.prompt', delete=False
        ) as f:
            f.write("Hello {{name}}! Your score is {{score}}.")
            f.flush()
            yield f.name
        os.unlink(f.name)

    @pytest.fixture
    def nested_template_file(self):
        """Create a template with nested variables."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.prompt', delete=False
        ) as f:
            f.write("User: {{user.name}}, Chapter: {{game.chapter}}")
            f.flush()
            yield f.name
        os.unlink(f.name)

    def test_ac_4_2_1_variable_substitution(self, template_prompt_file):
        """AC-4.2.1: {{variable}} syntax replaced with values."""
        from nikita.config.prompt_loader import PromptLoader

        loader = PromptLoader()
        content = loader.render(
            template_prompt_file,
            name="Alice",
            score="85"
        )

        assert "Hello Alice!" in content
        assert "Your score is 85" in content
        assert "{{" not in content

    def test_ac_4_2_2_render_accepts_kwargs(self, template_prompt_file):
        """AC-4.2.2: render(path, **kwargs) method accepts variables."""
        from nikita.config.prompt_loader import PromptLoader

        loader = PromptLoader()
        # Should not raise
        content = loader.render(
            template_prompt_file,
            name="Bob",
            score="90"
        )
        assert isinstance(content, str)

    def test_ac_4_2_3_nested_variables(self, nested_template_file):
        """AC-4.2.3: Nested variables work {{user.name}}."""
        from nikita.config.prompt_loader import PromptLoader

        loader = PromptLoader()
        content = loader.render(
            nested_template_file,
            user={"name": "Charlie"},
            game={"chapter": 3}
        )

        assert "User: Charlie" in content
        assert "Chapter: 3" in content

    def test_render_with_no_variables(self):
        """Render file with no variables returns content unchanged."""
        from nikita.config.prompt_loader import PromptLoader

        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.prompt', delete=False
        ) as f:
            f.write("No variables here.")
            f.flush()
            path = f.name

        try:
            loader = PromptLoader()
            content = loader.render(path)
            assert content == "No variables here."
        finally:
            os.unlink(path)


class TestMissingVariableError:
    """Test MissingVariableError exception."""

    @pytest.fixture
    def incomplete_template(self):
        """Create template with variables that won't be provided."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.prompt', delete=False
        ) as f:
            f.write("Hello {{name}}! Your {{missing_var}} is ready.")
            f.flush()
            yield f.name
        os.unlink(f.name)

    def test_ac_4_3_1_exception_defined(self):
        """AC-4.3.1: MissingVariableError exception defined."""
        from nikita.config.prompt_loader import MissingVariableError

        error = MissingVariableError("test_var")
        assert isinstance(error, Exception)

    def test_ac_4_3_2_raised_for_unreplaced_variable(self, incomplete_template):
        """AC-4.3.2: Raised when template has unreplaced {{var}}."""
        from nikita.config.prompt_loader import PromptLoader, MissingVariableError

        loader = PromptLoader()
        with pytest.raises(MissingVariableError):
            loader.render(incomplete_template, name="Alice")
            # missing_var is not provided

    def test_ac_4_3_3_error_includes_variable_name(self, incomplete_template):
        """AC-4.3.3: Error message includes missing variable name."""
        from nikita.config.prompt_loader import PromptLoader, MissingVariableError

        loader = PromptLoader()
        try:
            loader.render(incomplete_template, name="Alice")
            pytest.fail("Should have raised MissingVariableError")
        except MissingVariableError as e:
            assert "missing_var" in str(e)


class TestPromptCaching:
    """Test prompt caching behavior."""

    @pytest.fixture
    def cacheable_prompt(self):
        """Create a prompt file for cache testing."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.prompt', delete=False
        ) as f:
            f.write("Cached content")
            f.flush()
            yield f.name
        os.unlink(f.name)

    def test_ac_4_4_1_prompts_cached(self, cacheable_prompt):
        """AC-4.4.1: Prompts cached after first load."""
        from nikita.config.prompt_loader import PromptLoader

        loader = PromptLoader()

        # First load
        content1 = loader.load(cacheable_prompt)

        # Modify file (shouldn't affect cached result)
        with open(cacheable_prompt, 'w') as f:
            f.write("Modified content")

        # Second load should return cached
        content2 = loader.load(cacheable_prompt)

        assert content1 == content2
        assert content2 == "Cached content"

    def test_ac_4_4_3_subsequent_loads_fast(self, cacheable_prompt):
        """AC-4.4.3: Subsequent loads < 1ms."""
        from nikita.config.prompt_loader import PromptLoader

        loader = PromptLoader()

        # First load (cold)
        loader.load(cacheable_prompt)

        # Measure subsequent loads
        start = time.perf_counter()
        for _ in range(100):
            loader.load(cacheable_prompt)
        elapsed = time.perf_counter() - start

        # 100 loads should take < 100ms (avg < 1ms each)
        assert elapsed < 0.1, f"100 cached loads took {elapsed*1000:.2f}ms"


class TestCacheClear:
    """Test cache_clear() functionality."""

    @pytest.fixture
    def clearable_prompt(self):
        """Create a prompt file for cache clear testing."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.prompt', delete=False
        ) as f:
            f.write("Original content")
            f.flush()
            yield f.name
        os.unlink(f.name)

    def test_ac_4_5_1_cache_clear_exists(self):
        """AC-4.5.1: cache_clear() method exists."""
        from nikita.config.prompt_loader import PromptLoader

        loader = PromptLoader()
        assert hasattr(loader, 'cache_clear')
        assert callable(loader.cache_clear)

    def test_ac_4_5_2_clears_cached_prompts(self, clearable_prompt):
        """AC-4.5.2: Clears all cached prompts."""
        from nikita.config.prompt_loader import PromptLoader

        loader = PromptLoader()

        # Load and cache
        content1 = loader.load(clearable_prompt)
        assert content1 == "Original content"

        # Modify file
        with open(clearable_prompt, 'w') as f:
            f.write("New content")

        # Still cached
        assert loader.load(clearable_prompt) == "Original content"

        # Clear cache
        loader.cache_clear()

        # Now should read new content
        content2 = loader.load(clearable_prompt)
        assert content2 == "New content"

    def test_ac_4_5_3_next_load_reads_disk(self, clearable_prompt):
        """AC-4.5.3: Next load reads from disk."""
        from nikita.config.prompt_loader import PromptLoader

        loader = PromptLoader()

        # Load original
        loader.load(clearable_prompt)

        # Modify
        with open(clearable_prompt, 'w') as f:
            f.write("Disk content")

        # Clear and reload
        loader.cache_clear()
        content = loader.load(clearable_prompt)

        assert content == "Disk content"


class TestPromptLoaderSingleton:
    """Test that get_prompt_loader returns singleton."""

    def test_get_prompt_loader_returns_same_instance(self):
        """get_prompt_loader should return cached instance."""
        from nikita.config.prompt_loader import get_prompt_loader

        loader1 = get_prompt_loader()
        loader2 = get_prompt_loader()

        assert loader1 is loader2
