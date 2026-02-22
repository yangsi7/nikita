"""Tests for Spec 058 chapter exports."""

from __future__ import annotations


class TestExports058:
    """AC-8.1: All Spec 058 exports importable."""

    def test_boss_phase_importable(self):
        from nikita.engine.chapters import BossPhase
        assert BossPhase.OPENING.value == "opening"

    def test_boss_phase_state_importable(self):
        from nikita.engine.chapters import BossPhaseState
        state = BossPhaseState(phase="opening", chapter=1)
        assert state.chapter == 1

    def test_boss_phase_manager_importable(self):
        from nikita.engine.chapters import BossPhaseManager
        mgr = BossPhaseManager()
        assert hasattr(mgr, "start_boss")

    def test_is_multi_phase_boss_enabled_importable(self):
        from nikita.engine.chapters import is_multi_phase_boss_enabled
        assert callable(is_multi_phase_boss_enabled)

    def test_get_boss_phase_prompt_importable(self):
        from nikita.engine.chapters import get_boss_phase_prompt
        assert callable(get_boss_phase_prompt)

    def test_existing_exports_still_work(self):
        from nikita.engine.chapters import (
            BOSS_PROMPTS,
            BossJudgment,
            BossResult,
            BossStateMachine,
            JudgmentResult,
            get_boss_prompt,
        )
        assert BossResult.PASS.value == "PASS"
