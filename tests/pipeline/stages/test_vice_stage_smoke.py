"""Smoke test: ViceStage enabled path can instantiate real dependencies (HIGH-1).

Verifies that ViceAnalyzer, ViceScorer, and ViceStage can be imported and
constructed without crashing. This catches constructor signature mismatches
between the stage and its dependencies that mocked unit tests would miss.
"""

from __future__ import annotations


class TestViceAnalyzerImportable:
    """ViceAnalyzer can be imported and instantiated."""

    def test_vice_analyzer_importable(self):
        from nikita.engine.vice.analyzer import ViceAnalyzer

        analyzer = ViceAnalyzer()
        assert analyzer is not None
        # Constructor sets _agent to None (lazy-loaded)
        assert analyzer._agent is None


class TestViceScorerImportable:
    """ViceScorer can be imported and instantiated."""

    def test_vice_scorer_importable(self):
        from nikita.engine.vice.scorer import ViceScorer

        scorer = ViceScorer()
        assert scorer is not None
        # Constructor sets _session to None and _closed to False
        assert scorer._session is None
        assert scorer._closed is False


class TestViceStageImportable:
    """ViceStage can be imported and instantiated."""

    def test_vice_stage_importable(self):
        from nikita.pipeline.stages.vice import ViceStage

        stage = ViceStage()
        assert stage is not None
        assert stage.name == "vice"
        assert stage.is_critical is False
        assert stage.timeout_seconds == 45.0

    def test_vice_stage_accepts_session_kwarg(self):
        """ViceStage constructor matches BaseStage(session=...) signature."""
        from unittest.mock import MagicMock

        from nikita.pipeline.stages.vice import ViceStage

        mock_session = MagicMock()
        stage = ViceStage(session=mock_session)
        assert stage._session is mock_session
