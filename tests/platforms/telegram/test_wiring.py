"""Wiring sanity tests for Spec 214 FR-11c T1.6.

Assert the legacy 8-step Q&A onboarding package and its DI are fully
deleted. Uses source-greps (no heavy imports) so the test stays fast
and survives ImportError on partially-migrated branches.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
NIKITA_DIR = REPO_ROOT / "nikita"

LEGACY_PATTERNS = [
    # Source imports that proved T1.6 was incomplete on PR branch.
    r"from nikita\.platforms\.telegram\.onboarding",
    r"OnboardingHandler",
    r"onboarding_handler",
    r"OnboardingHandlerDep",
]


def _rg_nikita(pattern: str) -> list[str]:
    """Return matching lines under nikita/ for the given regex pattern."""
    result = subprocess.run(
        ["rg", "-n", "--", pattern, str(NIKITA_DIR)],
        capture_output=True,
        text=True,
        check=False,
    )
    # rg returns 1 on no-match; treat as empty.
    if result.returncode not in (0, 1):
        raise RuntimeError(
            f"rg failed (code {result.returncode}): {result.stderr}"
        )
    return [ln for ln in result.stdout.splitlines() if ln.strip()]


def test_no_onboarding_handler_references() -> None:
    """AC-T1.6.1 + AC-T1.6.3: zero legacy references in production code.

    Scope: nikita/ (production). Tests/docs are allowed to reference the
    legacy class for archival context. Spec/doc files in specs/, docs/,
    and .claude/ are out-of-scope for this gate.
    """
    offenders: dict[str, list[str]] = {}
    for pattern in LEGACY_PATTERNS:
        hits = _rg_nikita(pattern)
        if hits:
            offenders[pattern] = hits
    assert not offenders, (
        "Legacy OnboardingHandler references still in nikita/:\n"
        + "\n".join(
            f"  {pat}:\n    " + "\n    ".join(hits[:5])
            for pat, hits in offenders.items()
        )
    )


def test_legacy_onboarding_package_deleted() -> None:
    """AC-T1.6.1: nikita/platforms/telegram/onboarding/ must not exist."""
    legacy_pkg = NIKITA_DIR / "platforms" / "telegram" / "onboarding"
    assert not legacy_pkg.exists(), (
        f"Legacy package still present at {legacy_pkg}"
    )
