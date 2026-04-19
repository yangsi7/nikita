"""Wiring sanity tests for Spec 214 FR-11c T1.6.

Assert the legacy 8-step Q&A onboarding package and its DI are fully
deleted. Uses source-greps (no heavy imports) so the test stays fast
and survives ImportError on partially-migrated branches.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
NIKITA_DIR = REPO_ROOT / "nikita"

# Structural (code-level) patterns only. We DO NOT grep for the bare
# strings "OnboardingHandler" / "onboarding_handler" because historical
# comments and docstrings legitimately mention the deleted class to
# explain the FR-11c migration. The goal of this test is to catch
# lingering *executable* references that would break `import` or DI.
LEGACY_CODE_PATTERNS = [
    # Any surviving import from the deleted package — the single biggest
    # smell that would re-break `from nikita.api.main import app`.
    r"^\s*from\s+nikita\.platforms\.telegram\.onboarding",
    r"^\s*import\s+nikita\.platforms\.telegram\.onboarding",
    # DI type alias that would require the deleted telegram
    # OnboardingHandler at runtime.
    r"OnboardingHandlerDep\b",
    # Instantiation of the deleted class. Require `(` directly after
    # the name (no space — narrative comments like "OnboardingHandler
    # (8-step Q&A)" would otherwise trigger).
    r"\bOnboardingHandler\(",
]


def _rg_nikita(pattern: str) -> list[str]:
    """Return matching lines under nikita/ for the given regex pattern.

    Pure-Python implementation so the test runs on CI without ripgrep.
    """
    compiled = re.compile(pattern)
    hits: list[str] = []
    for py_file in NIKITA_DIR.rglob("*.py"):
        try:
            for lineno, line in enumerate(py_file.read_text().splitlines(), 1):
                if compiled.search(line):
                    hits.append(f"{py_file}:{lineno}:{line}")
        except (OSError, UnicodeDecodeError):
            continue
    return hits


def test_no_onboarding_handler_references() -> None:
    """AC-T1.6.1 + AC-T1.6.3: zero legacy code-level references in nikita/.

    Scope: nikita/ (production). Scans for import statements, DI type
    aliases, and class instantiations of the deleted OnboardingHandler
    — anything that would fail at runtime if the package is absent.
    Comments/docstrings mentioning the deleted class for historical
    context are intentionally allowed.
    """
    offenders: dict[str, list[str]] = {}
    for pattern in LEGACY_CODE_PATTERNS:
        hits = _rg_nikita(pattern)
        if hits:
            offenders[pattern] = hits
    assert not offenders, (
        "Legacy OnboardingHandler code-level references still in nikita/:\n"
        + "\n".join(
            f"  {pat}:\n    " + "\n    ".join(hits[:5])
            for pat, hits in offenders.items()
        )
    )


def test_webhook_app_imports_cleanly() -> None:
    """AC-T1.6.1 runtime guard: `from nikita.api.main import app` must
    succeed. If any stale legacy import lingers it surfaces as an
    ImportError here, before it can crash a real Cloud Run boot."""
    import importlib

    module = importlib.import_module("nikita.api.main")
    assert hasattr(module, "create_app")


def test_legacy_onboarding_package_deleted() -> None:
    """AC-T1.6.1: nikita/platforms/telegram/onboarding/ must not exist."""
    legacy_pkg = NIKITA_DIR / "platforms" / "telegram" / "onboarding"
    assert not legacy_pkg.exists(), (
        f"Legacy package still present at {legacy_pkg}"
    )
