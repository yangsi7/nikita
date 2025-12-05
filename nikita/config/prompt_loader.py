"""Prompt file loading with variable substitution and caching.

This module provides PromptLoader for loading .prompt template files
with {{variable}} substitution support.

Usage:
    from nikita.config.prompt_loader import get_prompt_loader

    loader = get_prompt_loader()
    content = loader.render("persona/nikita.prompt", name="Alice", chapter=1)
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any


class MissingVariableError(Exception):
    """Raised when a template contains unreplaced variables."""

    def __init__(self, variable_name: str, template_path: str | None = None):
        self.variable_name = variable_name
        self.template_path = template_path
        msg = f"Missing variable: {{{{{variable_name}}}}}"
        if template_path:
            msg += f" in template {template_path}"
        super().__init__(msg)


class PromptLoader:
    """Load and render .prompt template files with caching.

    Supports:
    - Loading raw .prompt files
    - {{variable}} substitution
    - {{nested.variable}} substitution (dot notation)
    - LRU caching for performance
    """

    # Regex to find {{variable}} patterns
    VARIABLE_PATTERN = re.compile(r"\{\{([a-zA-Z_][a-zA-Z0-9_\.]*)\}\}")

    def __init__(self, base_path: Path | str | None = None):
        """Initialize PromptLoader.

        Args:
            base_path: Optional base directory for prompt files.
                       Defaults to nikita/prompts/
        """
        if base_path is None:
            # Default to nikita/prompts/ relative to this file
            self._base_path = Path(__file__).parent.parent / "prompts"
        else:
            self._base_path = Path(base_path)

        # Internal cache for loaded files
        self._cache: dict[str, str] = {}

    def load(self, path: str | Path) -> str:
        """Load a prompt file and return its content.

        Args:
            path: Path to .prompt file (absolute or relative to base_path)

        Returns:
            Raw content of the prompt file

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        path_str = str(path)

        # Check cache first
        if path_str in self._cache:
            return self._cache[path_str]

        # Resolve path
        file_path = self._resolve_path(path)

        # Read file
        content = file_path.read_text(encoding="utf-8")

        # Cache it
        self._cache[path_str] = content

        return content

    def render(self, path: str | Path, **kwargs: Any) -> str:
        """Load and render a prompt file with variable substitution.

        Args:
            path: Path to .prompt file
            **kwargs: Variables to substitute (supports nested dicts)

        Returns:
            Rendered content with variables replaced

        Raises:
            FileNotFoundError: If file doesn't exist
            MissingVariableError: If template has unreplaced variables
        """
        content = self.load(path)
        return self._substitute_variables(content, kwargs, str(path))

    def cache_clear(self) -> None:
        """Clear all cached prompts."""
        self._cache.clear()

    def _resolve_path(self, path: str | Path) -> Path:
        """Resolve path to absolute path.

        Args:
            path: Relative or absolute path

        Returns:
            Resolved Path object

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        path = Path(path)

        if path.is_absolute():
            resolved = path
        else:
            resolved = self._base_path / path

        if not resolved.exists():
            raise FileNotFoundError(f"Prompt file not found: {resolved}")

        return resolved

    def _substitute_variables(
        self, content: str, variables: dict[str, Any], template_path: str
    ) -> str:
        """Substitute {{variable}} patterns with values.

        Args:
            content: Template content
            variables: Dict of variable values (supports nested dicts)
            template_path: Path for error messages

        Returns:
            Content with variables substituted

        Raises:
            MissingVariableError: If variable not provided
        """

        def replace_match(match: re.Match) -> str:
            var_name = match.group(1)
            value = self._get_nested_value(var_name, variables)

            if value is None:
                raise MissingVariableError(var_name, template_path)

            return str(value)

        result = self.VARIABLE_PATTERN.sub(replace_match, content)
        return result

    def _get_nested_value(self, var_name: str, variables: dict[str, Any]) -> Any:
        """Get value from variables dict, supporting dot notation.

        Args:
            var_name: Variable name (e.g., "user.name" or "score")
            variables: Dict of variable values

        Returns:
            Value or None if not found
        """
        parts = var_name.split(".")
        value: Any = variables

        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return None

        return value


@lru_cache(maxsize=1)
def get_prompt_loader() -> PromptLoader:
    """Get cached PromptLoader singleton.

    Returns:
        Shared PromptLoader instance
    """
    return PromptLoader()
