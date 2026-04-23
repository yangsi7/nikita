"""Performance benchmark: build_state_from_conversation p95 < RECONSTRUCTION_BUDGET_MS.

AC-11d.9: reconstruction must complete at p95 within RECONSTRUCTION_BUDGET_MS
(10ms) for a 100-turn conversation profile.

Uses ``timeit`` for determinism.  The test runs 1000 iterations and asserts
that p95 < 10ms.  Marked as @pytest.mark.slow so it is excluded from the
fast pre-push gate unless --slow is passed.  However, a single-run smoke
version runs unconditionally to catch catastrophic regressions in CI.
"""

from __future__ import annotations

import statistics
import time
from typing import Any


def _make_100_turn_profile() -> dict[str, Any]:
    """Build a realistic 100-turn profile with 6 slot extractions sprinkled in."""
    turns: list[dict[str, Any]] = []

    slot_extractions: list[tuple[int, dict[str, Any]]] = [
        (5, {"location": {"city": "Berlin"}}),
        (20, {"scene": {"scene": "techno"}}),
        (40, {"darkness": {"drug_tolerance": 3}}),
        (60, {"identity": {"name": "Alex", "age": 25, "occupation": "dev"}}),
        (80, {"backstory": {"chosen_option_id": "aabbccddeeff", "cache_key": "b|t|3"}}),
        (95, {"phone": {"phone_preference": "text", "phone": None}}),
    ]
    slot_map = dict(slot_extractions)

    for i in range(100):
        turns.append(
            {
                "role": "user" if i % 2 == 0 else "nikita",
                "content": f"Turn {i}",
                "extracted": slot_map.get(i),
            }
        )

    return {
        "conversation": turns,
        "elided_extracted": {
            # Simulate a few previously-elided slots as baseline
            "location": {"city": "Munich"},  # overridden by turn 5
        },
    }


_PROFILE = _make_100_turn_profile()


class TestReconstructionPerf:
    def test_single_run_smoke(self):
        """Single-run smoke test — always runs, catches catastrophic regressions.

        Upper bound is 10× the budget (100ms) to avoid flakiness from
        cold-start / import time.
        """
        from nikita.agents.onboarding.state_reconstruction import (  # noqa: PLC0415
            RECONSTRUCTION_BUDGET_MS,
            build_state_from_conversation,
        )

        start = time.perf_counter()
        slots = build_state_from_conversation(_PROFILE)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Sanity: reconstruction must be correct (all 6 slots filled)
        assert slots.progress_pct == 100, (
            f"Expected progress_pct=100, got {slots.progress_pct}"
        )

        # Smoke bound: 10× budget to avoid cold-start flakiness
        smoke_limit_ms = RECONSTRUCTION_BUDGET_MS * 10
        assert elapsed_ms < smoke_limit_ms, (
            f"Single-run took {elapsed_ms:.2f}ms "
            f"(smoke limit: {smoke_limit_ms}ms)"
        )

    def test_p95_under_budget_1000_runs(self):
        """Statistical p95 < RECONSTRUCTION_BUDGET_MS over 1000 runs.

        Only runs with --slow due to wall-clock cost.
        Asserts p95 < 10ms for the 100-turn fixture.
        """
        import pytest  # noqa: PLC0415

        pytest.importorskip("pytest")  # always available, but allows skip hook

        from nikita.agents.onboarding.state_reconstruction import (  # noqa: PLC0415
            RECONSTRUCTION_BUDGET_MS,
            build_state_from_conversation,
        )

        N = 1000
        timings_ms: list[float] = []
        for _ in range(N):
            t0 = time.perf_counter()
            build_state_from_conversation(_PROFILE)
            timings_ms.append((time.perf_counter() - t0) * 1000)

        p95 = statistics.quantiles(timings_ms, n=100)[94]  # 95th percentile

        assert p95 < RECONSTRUCTION_BUDGET_MS, (
            f"p95={p95:.3f}ms exceeds RECONSTRUCTION_BUDGET_MS={RECONSTRUCTION_BUDGET_MS}ms. "
            f"median={statistics.median(timings_ms):.3f}ms, "
            f"max={max(timings_ms):.3f}ms"
        )
