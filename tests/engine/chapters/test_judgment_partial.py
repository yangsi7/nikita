"""Tests for Spec 058 BossResult.PARTIAL enum extension."""

from __future__ import annotations

from nikita.engine.chapters.judgment import BossResult


class TestBossResultPartial:
    """AC-3.1: PARTIAL member exists, backward compat."""

    def test_partial_exists(self):
        assert hasattr(BossResult, "PARTIAL")
        assert BossResult.PARTIAL.value == "PARTIAL"

    def test_pass_still_works(self):
        assert BossResult.PASS.value == "PASS"

    def test_fail_still_works(self):
        assert BossResult.FAIL.value == "FAIL"

    def test_all_three_outcomes_roundtrip(self):
        for result in [BossResult.PASS, BossResult.FAIL, BossResult.PARTIAL]:
            assert BossResult(result.value) == result
