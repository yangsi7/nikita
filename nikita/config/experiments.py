"""Experiment overlay system for configuration.

Supports:
- NIKITA_EXPERIMENT env var to activate experiments
- Deep merge of experiment config over base config
- Experiment inheritance via 'extends' field
- Circular inheritance detection

Usage:
    # Set env var to activate
    export NIKITA_EXPERIMENT=harder

    # In code
    from nikita.config.experiments import ExperimentLoader
    loader = ExperimentLoader()
    overlay = loader.load_experiment_config()
"""

from __future__ import annotations

import os
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


class ConfigurationError(Exception):
    """Raised for configuration errors like missing experiments."""

    pass


def deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Deep merge overlay dict into base dict.

    Rules:
    - Nested dicts are merged recursively
    - Lists are replaced (not appended)
    - Scalars are overwritten

    Args:
        base: Base configuration dict
        overlay: Overlay configuration to merge on top

    Returns:
        New merged dict (base is not mutated)
    """
    result = deepcopy(base)

    for key, value in overlay.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            # Recursively merge nested dicts
            result[key] = deep_merge(result[key], value)
        else:
            # Replace lists, scalars, or add new keys
            result[key] = deepcopy(value)

    return result


class ExperimentLoader:
    """Load and apply experiment configuration overlays.

    Reads NIKITA_EXPERIMENT env var to determine which experiment to load.
    Supports experiment inheritance via 'extends' field.
    """

    ENV_VAR = "NIKITA_EXPERIMENT"

    def __init__(self, base_path: Path | str | None = None):
        """Initialize ExperimentLoader.

        Args:
            base_path: Base directory containing experiments/ subdirectory.
                       Defaults to nikita/config_data/
        """
        if base_path is None:
            self._base_path = Path(__file__).parent.parent / "config_data"
        else:
            self._base_path = Path(base_path)

        self._experiments_dir = self._base_path / "experiments"
        self._experiment_name = os.environ.get(self.ENV_VAR)

    @property
    def experiment_name(self) -> str | None:
        """Get the current experiment name from env var."""
        return self._experiment_name

    def load_experiment_config(self) -> dict[str, Any]:
        """Load experiment configuration overlay.

        Returns:
            Merged experiment config dict, or empty dict if no experiment

        Raises:
            ConfigurationError: If experiment not found or circular inheritance
        """
        if self._experiment_name is None:
            return {}

        return self._load_experiment_with_inheritance(
            self._experiment_name, visited=set()
        )

    def _get_experiment_path(self, name: str | None = None) -> Path:
        """Get path to experiment YAML file.

        Args:
            name: Experiment name (defaults to current experiment)

        Returns:
            Path to experiment YAML file
        """
        exp_name = name or self._experiment_name
        return self._experiments_dir / f"{exp_name}.yaml"

    def _load_experiment_with_inheritance(
        self, name: str, visited: set[str]
    ) -> dict[str, Any]:
        """Load experiment config with inheritance support.

        Args:
            name: Experiment name to load
            visited: Set of already-visited experiment names (for cycle detection)

        Returns:
            Merged config with all inherited values

        Raises:
            ConfigurationError: If experiment not found or circular inheritance
        """
        # Check for circular inheritance
        if name in visited:
            cycle = " -> ".join(list(visited) + [name])
            raise ConfigurationError(
                f"Circular inheritance detected: {cycle}"
            )

        visited.add(name)

        # Get experiment file path
        exp_path = self._get_experiment_path(name)

        if not exp_path.exists():
            available = self._list_available_experiments()
            available_str = ", ".join(available) if available else "none"
            raise ConfigurationError(
                f"Experiment '{name}' not found. "
                f"Available experiments: {available_str}"
            )

        # Load experiment YAML
        with open(exp_path) as f:
            config = yaml.safe_load(f) or {}

        # Check for inheritance
        parent_name = config.pop("extends", None)

        if parent_name:
            # Load parent first
            parent_config = self._load_experiment_with_inheritance(
                parent_name, visited.copy()
            )
            # Merge child on top of parent
            config = deep_merge(parent_config, config)

        return config

    def _list_available_experiments(self) -> list[str]:
        """List available experiment names.

        Returns:
            List of experiment names (without .yaml extension)
        """
        if not self._experiments_dir.exists():
            return []

        return [
            p.stem
            for p in self._experiments_dir.glob("*.yaml")
            if p.is_file()
        ]
