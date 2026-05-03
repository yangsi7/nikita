"""T-B3-9 (Spec 216-B3): /converse contracts deletion-guard regression.

Counter-intuitive but important: Spec 216-B3 ships POST /answer + GET /state +
the /converse 410-Gone shim, but it does NOT delete the legacy /converse
contracts. The FE on master (use-onboarding-api.ts:233) still calls
/converse — deletion would break production until 216-C ships.

This test asserts the legacy symbols are STILL importable post-B3 so a
future contributor cannot accidentally delete them while reviewing the
B3 diff. The deletion belongs to a separate cleanup PR after 216-C ships.

Closes the wave-2 disagreement (scope-reviewer PUNT vs approach-evaluator
big-bang) by encoding the resolved decision (hybrid feature-flag) as a
runtime falsifier.

Rule cross-references:
  - .claude/rules/agentic-design-patterns.md (deprecation discipline)
  - 216-B3 implementation brief §2 (rationale for hybrid approach)
"""

from __future__ import annotations


def test_converse_contracts_still_importable_post_216_b3() -> None:
    """Guard: 216-C owns deletion of these symbols; B3 must NOT remove them.

    If these imports fail, a regression has reverted 216-C's deletion PR
    OR a contributor preemptively deleted them in B3 — both block the
    /converse 410-Gone shim from serving the legacy contract during the
    216-C migration window.
    """
    from nikita.agents.onboarding.converse_contracts import (
        ConverseRequest,
        ConverseResponse,
        Turn,
    )

    assert ConverseRequest is not None, (
        "ConverseRequest deleted prematurely; 216-C owns this deletion."
    )
    assert ConverseResponse is not None
    assert Turn is not None


def test_converse_route_still_registered_post_216_b3() -> None:
    """Guard: /converse handler symbol exists on the route module.

    The 410-shim lives at the top of this handler — if the handler is
    deleted in B3, the shim is also gone and the FE on master breaks
    immediately on the next deploy.
    """
    from nikita.api.routes.portal_onboarding import converse

    assert callable(converse), (
        "/converse handler must remain callable post-B3 — the 410-Gone "
        "shim lives at the top of this handler body."
    )


def test_get_converse_timeout_ms_still_exported_post_216_b3() -> None:
    """Guard: portal/.../converse-timeout-invariant.test.ts imports the
    timeout constant; deleting it in B3 breaks FE tests (216-C cleanup
    will own the deletion path)."""
    from nikita.api.routes.portal_onboarding import get_converse_timeout_ms

    assert callable(get_converse_timeout_ms), (
        "get_converse_timeout_ms must stay exported — the FE timeout-"
        "invariant test imports it."
    )
    # Sanity: the timeout function returns an int (cold or warm budget).
    assert isinstance(get_converse_timeout_ms(), int)
