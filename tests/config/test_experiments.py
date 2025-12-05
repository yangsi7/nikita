"""Tests for Experiment Overlays - TDD for US-5 (T5.1-T5.4).

Acceptance Criteria:
- AC-5.1.1: Reads NIKITA_EXPERIMENT env var at startup
- AC-5.1.2: If set, loads experiments/{name}.yaml
- AC-5.1.3: If not set, uses base config only
- AC-5.2.1: Experiment YAML overlays base config
- AC-5.2.2: Nested dicts merged recursively
- AC-5.2.3: Lists replaced (not appended)
- AC-5.2.4: Scalars overwritten
- AC-5.3.1: extends: "parent_experiment" syntax works
- AC-5.3.2: Parent loaded first, then child overlay
- AC-5.3.3: Circular inheritance detected and raises error
- AC-5.4.1: ConfigurationError raised for unknown experiment
- AC-5.4.2: Error message lists available experiments
- AC-5.4.3: Fails fast at startup, not runtime
"""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch


class TestExperimentImports:
    """Test that experiment-related items are importable."""

    def test_configuration_error_importable(self):
        """AC-5.4.1: ConfigurationError exception should be importable."""
        from nikita.config.experiments import ConfigurationError
        assert issubclass(ConfigurationError, Exception)

    def test_experiment_loader_importable(self):
        """ExperimentLoader class should be importable."""
        from nikita.config.experiments import ExperimentLoader
        assert ExperimentLoader is not None

    def test_deep_merge_importable(self):
        """deep_merge utility should be importable."""
        from nikita.config.experiments import deep_merge
        assert callable(deep_merge)


class TestExperimentEnvVar:
    """Test NIKITA_EXPERIMENT environment variable detection."""

    def test_ac_5_1_1_reads_env_var(self):
        """AC-5.1.1: Reads NIKITA_EXPERIMENT env var at startup."""
        from nikita.config.experiments import ExperimentLoader

        with patch.dict(os.environ, {"NIKITA_EXPERIMENT": "test_exp"}):
            loader = ExperimentLoader()
            assert loader.experiment_name == "test_exp"

    def test_ac_5_1_3_none_when_not_set(self):
        """AC-5.1.3: If not set, uses base config only."""
        from nikita.config.experiments import ExperimentLoader

        # Ensure env var is not set
        env = os.environ.copy()
        env.pop("NIKITA_EXPERIMENT", None)

        with patch.dict(os.environ, env, clear=True):
            loader = ExperimentLoader()
            assert loader.experiment_name is None


class TestExperimentLoading:
    """Test loading experiment YAML files."""

    @pytest.fixture
    def experiment_dir(self):
        """Create temporary experiment directory with test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            exp_dir = Path(tmpdir) / "experiments"
            exp_dir.mkdir()

            # Create base config
            base_yaml = Path(tmpdir) / "game.yaml"
            base_yaml.write_text("""
starting_score: 50.0
max_boss_attempts: 3
game_duration_days: 21
nested:
  value1: original
  value2: keep_this
tags:
  - tag1
  - tag2
""")

            # Create experiment overlay
            exp_file = exp_dir / "harder.yaml"
            exp_file.write_text("""
starting_score: 40.0
nested:
  value1: overridden
tags:
  - new_tag
""")

            # Create parent experiment
            parent_exp = exp_dir / "parent.yaml"
            parent_exp.write_text("""
starting_score: 45.0
parent_only: true
""")

            # Create child experiment with extends
            child_exp = exp_dir / "child.yaml"
            child_exp.write_text("""
extends: parent
starting_score: 35.0
child_only: true
""")

            # Create circular experiment A
            circ_a = exp_dir / "circ_a.yaml"
            circ_a.write_text("""
extends: circ_b
value: a
""")

            # Create circular experiment B
            circ_b = exp_dir / "circ_b.yaml"
            circ_b.write_text("""
extends: circ_a
value: b
""")

            yield tmpdir

    def test_ac_5_1_2_loads_experiment_yaml(self, experiment_dir):
        """AC-5.1.2: If set, loads experiments/{name}.yaml."""
        from nikita.config.experiments import ExperimentLoader

        with patch.dict(os.environ, {"NIKITA_EXPERIMENT": "harder"}):
            loader = ExperimentLoader(base_path=Path(experiment_dir))
            assert loader.experiment_name == "harder"
            # Should find the experiment file
            exp_path = loader._get_experiment_path()
            assert exp_path.exists()


class TestDeepMerge:
    """Test deep merge logic."""

    def test_ac_5_2_1_overlay_base_config(self):
        """AC-5.2.1: Experiment YAML overlays base config."""
        from nikita.config.experiments import deep_merge

        base = {"score": 50, "name": "test"}
        overlay = {"score": 40}

        result = deep_merge(base, overlay)

        assert result["score"] == 40  # Overwritten
        assert result["name"] == "test"  # Preserved

    def test_ac_5_2_2_nested_dicts_merged(self):
        """AC-5.2.2: Nested dicts merged recursively."""
        from nikita.config.experiments import deep_merge

        base = {
            "nested": {
                "value1": "original",
                "value2": "keep_this",
                "deep": {"a": 1, "b": 2}
            }
        }
        overlay = {
            "nested": {
                "value1": "overridden",
                "deep": {"a": 10}
            }
        }

        result = deep_merge(base, overlay)

        assert result["nested"]["value1"] == "overridden"
        assert result["nested"]["value2"] == "keep_this"
        assert result["nested"]["deep"]["a"] == 10
        assert result["nested"]["deep"]["b"] == 2

    def test_ac_5_2_3_lists_replaced(self):
        """AC-5.2.3: Lists replaced (not appended)."""
        from nikita.config.experiments import deep_merge

        base = {"tags": ["tag1", "tag2"]}
        overlay = {"tags": ["new_tag"]}

        result = deep_merge(base, overlay)

        assert result["tags"] == ["new_tag"]
        assert "tag1" not in result["tags"]

    def test_ac_5_2_4_scalars_overwritten(self):
        """AC-5.2.4: Scalars overwritten."""
        from nikita.config.experiments import deep_merge

        base = {"score": 50.0, "attempts": 3, "name": "base"}
        overlay = {"score": 40.0, "attempts": 5}

        result = deep_merge(base, overlay)

        assert result["score"] == 40.0
        assert result["attempts"] == 5
        assert result["name"] == "base"


class TestExperimentInheritance:
    """Test experiment inheritance via extends."""

    @pytest.fixture
    def inheritance_dir(self):
        """Create directory with parent/child experiments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            exp_dir = Path(tmpdir) / "experiments"
            exp_dir.mkdir()

            # Parent experiment
            parent = exp_dir / "parent.yaml"
            parent.write_text("""
starting_score: 45.0
parent_only: true
shared: from_parent
""")

            # Child experiment
            child = exp_dir / "child.yaml"
            child.write_text("""
extends: parent
starting_score: 35.0
child_only: true
""")

            # Grandchild experiment
            grandchild = exp_dir / "grandchild.yaml"
            grandchild.write_text("""
extends: child
starting_score: 25.0
grandchild_only: true
""")

            yield tmpdir

    def test_ac_5_3_1_extends_syntax(self, inheritance_dir):
        """AC-5.3.1: extends: 'parent_experiment' syntax works."""
        from nikita.config.experiments import ExperimentLoader

        with patch.dict(os.environ, {"NIKITA_EXPERIMENT": "child"}):
            loader = ExperimentLoader(base_path=Path(inheritance_dir))
            config = loader.load_experiment_config()

            # Child values should be present
            assert config.get("child_only") is True
            assert config.get("starting_score") == 35.0

    def test_ac_5_3_2_parent_loaded_first(self, inheritance_dir):
        """AC-5.3.2: Parent loaded first, then child overlay."""
        from nikita.config.experiments import ExperimentLoader

        with patch.dict(os.environ, {"NIKITA_EXPERIMENT": "child"}):
            loader = ExperimentLoader(base_path=Path(inheritance_dir))
            config = loader.load_experiment_config()

            # Parent values inherited
            assert config.get("parent_only") is True
            # Child overrides
            assert config.get("starting_score") == 35.0
            # Child adds
            assert config.get("child_only") is True


class TestCircularInheritance:
    """Test circular inheritance detection."""

    @pytest.fixture
    def circular_dir(self):
        """Create directory with circular experiments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            exp_dir = Path(tmpdir) / "experiments"
            exp_dir.mkdir()

            # Circular A -> B
            circ_a = exp_dir / "circ_a.yaml"
            circ_a.write_text("""
extends: circ_b
value: a
""")

            # Circular B -> A
            circ_b = exp_dir / "circ_b.yaml"
            circ_b.write_text("""
extends: circ_a
value: b
""")

            yield tmpdir

    def test_ac_5_3_3_circular_inheritance_error(self, circular_dir):
        """AC-5.3.3: Circular inheritance detected and raises error."""
        from nikita.config.experiments import ExperimentLoader, ConfigurationError

        with patch.dict(os.environ, {"NIKITA_EXPERIMENT": "circ_a"}):
            loader = ExperimentLoader(base_path=Path(circular_dir))

            with pytest.raises(ConfigurationError) as exc_info:
                loader.load_experiment_config()

            assert "circular" in str(exc_info.value).lower()


class TestInvalidExperiment:
    """Test invalid experiment handling."""

    @pytest.fixture
    def valid_exp_dir(self):
        """Create directory with known experiments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            exp_dir = Path(tmpdir) / "experiments"
            exp_dir.mkdir()

            # Create some valid experiments
            (exp_dir / "exp1.yaml").write_text("value: 1")
            (exp_dir / "exp2.yaml").write_text("value: 2")

            yield tmpdir

    def test_ac_5_4_1_unknown_experiment_raises_error(self, valid_exp_dir):
        """AC-5.4.1: ConfigurationError raised for unknown experiment."""
        from nikita.config.experiments import ExperimentLoader, ConfigurationError

        with patch.dict(os.environ, {"NIKITA_EXPERIMENT": "nonexistent"}):
            loader = ExperimentLoader(base_path=Path(valid_exp_dir))

            with pytest.raises(ConfigurationError):
                loader.load_experiment_config()

    def test_ac_5_4_2_error_lists_available(self, valid_exp_dir):
        """AC-5.4.2: Error message lists available experiments."""
        from nikita.config.experiments import ExperimentLoader, ConfigurationError

        with patch.dict(os.environ, {"NIKITA_EXPERIMENT": "nonexistent"}):
            loader = ExperimentLoader(base_path=Path(valid_exp_dir))

            try:
                loader.load_experiment_config()
                pytest.fail("Should have raised ConfigurationError")
            except ConfigurationError as e:
                error_msg = str(e)
                assert "exp1" in error_msg or "exp2" in error_msg

    def test_ac_5_4_3_fails_fast_at_startup(self, valid_exp_dir):
        """AC-5.4.3: Fails fast at startup, not runtime."""
        from nikita.config.experiments import ExperimentLoader, ConfigurationError

        # This should fail immediately when trying to load, not later
        with patch.dict(os.environ, {"NIKITA_EXPERIMENT": "nonexistent"}):
            loader = ExperimentLoader(base_path=Path(valid_exp_dir))

            # The error should be raised when loading config, not later
            with pytest.raises(ConfigurationError):
                loader.load_experiment_config()


class TestNoExperiment:
    """Test behavior when no experiment is set."""

    def test_no_experiment_returns_empty_overlay(self):
        """When NIKITA_EXPERIMENT not set, return empty overlay."""
        from nikita.config.experiments import ExperimentLoader

        env = os.environ.copy()
        env.pop("NIKITA_EXPERIMENT", None)

        with patch.dict(os.environ, env, clear=True):
            loader = ExperimentLoader()
            config = loader.load_experiment_config()

            # Should return empty dict (no overlay)
            assert config == {}
