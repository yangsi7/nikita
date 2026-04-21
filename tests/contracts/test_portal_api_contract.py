"""Cross-stack API path contract — Spec 214 GH #373 regression guard.

Parses ``portal/src/app/onboarding/hooks/use-onboarding-api.ts`` via Python
regex to extract every static-string path argument from
``api.post(path, ...)`` / ``api.get(path, ...)`` etc. For each, asserts the
corresponding FastAPI route is registered (via ``app.routes`` inspection).

Why a separate test file: this asserts a contract that spans two systems
(TS frontend + Python backend). Pattern extends
``tests/api/routes/test_telegram.py::TestDIContract`` which uses
``ast.walk`` + ``inspect.signature`` reflection for the intra-Python DI
factory contract.

Known limitations (tracked here so the test is honest about coverage):

- Template-literal paths (e.g. ``/api/v1/onboarding/${id}``) are skipped,
  counted, and printed for manual review. Add to ``EXPLICIT_STATIC_PATHS``
  below if they form a critical backbone.
- Only the onboarding hook is parsed for iteration 1 (matches the #373
  bug). Expansion to all ``portal/src/**/hooks/use-*.ts`` is a follow-up
  if Walk O reveals other path-mismatch bugs.

PR-A introduces this file. The bug it would have caught (had it existed at
PR #361 merge) was a 3-way drift between the frontend hook path, the
backend route declaration, and the test docstring — none of the three
agreed, mock tests passed, prod 404'd for 5+ days.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from nikita.api.main import create_app

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK_FILE = REPO_ROOT / "portal/src/app/onboarding/hooks/use-onboarding-api.ts"

# Backbone routes that MUST resolve regardless of AST extractor coverage.
# Each entry = (HTTP method, full path). Path includes /api/v1 prefix.
# Hand-curated to stay falsifiable even if the regex misses something.
# Updating this list is a deliberate contract change.
EXPLICIT_STATIC_PATHS = [
    ("POST", "/api/v1/onboarding/converse"),                # #373 fix site
    ("PATCH", "/api/v1/onboarding/profile"),
    ("PUT", "/api/v1/onboarding/profile/chosen-option"),
    ("POST", "/api/v1/onboarding/preview-backstory"),
    ("POST", "/api/v1/onboarding/profile"),                  # submitProfile
    ("POST", "/api/v1/portal/link-telegram"),                # linkTelegram
]

# Minimal regex extractor for ``api.<verb>("/literal-path", ...)`` calls.
# Pure-Python (no Node deps). Trade-off: only catches static double-quoted
# paths, NOT template literals or variable references.
API_CALL_RE = re.compile(
    r'\bapi\.(get|post|put|patch|delete)(?:<[^>]+>)?\(\s*"([^"]+)"',
    re.MULTILINE,
)
TEMPLATE_LITERAL_RE = re.compile(
    r'\bapi\.(get|post|put|patch|delete)(?:<[^>]+>)?\(\s*`'
)


def _registered_paths(app) -> set[tuple[str, str]]:
    """Return ``{(method, path)}`` for every registered FastAPI route."""
    out: set[tuple[str, str]] = set()
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if path and methods:
            for m in methods:
                if m != "HEAD":  # FastAPI auto-adds HEAD for GET
                    out.add((m, path))
    return out


@pytest.fixture(scope="module")
def app_routes() -> set[tuple[str, str]]:
    return _registered_paths(create_app())


class TestPortalApiContract:
    """Spec 214 #373 regression guard — frontend↔backend path contract."""

    def test_explicit_static_paths_are_registered(self, app_routes):
        """Backbone routes referenced by the wizard MUST be registered."""
        missing = [
            (m, p) for m, p in EXPLICIT_STATIC_PATHS if (m, p) not in app_routes
        ]
        assert not missing, (
            f"Frontend assumes these routes exist; backend has not registered them: "
            f"{missing}. Either register the route or remove from EXPLICIT_STATIC_PATHS."
        )

    def test_negative_case_wrong_path_unregistered(self, app_routes):
        """Discriminating-power check — known-wrong paths MUST be missing."""
        wrong = [
            ("POST", "/api/v1/portal/onboarding/converse"),       # The #373 bug path
            ("POST", "/api/v1/onboarding/onboarding/converse"),   # Doubled prefix
        ]
        for entry in wrong:
            assert entry not in app_routes, (
                f"{entry} unexpectedly registered. The contract test's negative "
                f"case is not discriminating — review test setup."
            )

    def test_extracted_hook_paths_are_registered(self, app_routes):
        """For every static-string ``api.<verb>("/path", ...)`` call in the
        wizard hook, the corresponding ``/api/v1{path}`` route MUST be
        registered.
        """
        if not HOOK_FILE.exists():
            pytest.skip(f"Hook file not found at {HOOK_FILE} — repo layout changed")

        source = HOOK_FILE.read_text()
        # Sanity: hook MUST use api.<verb> not raw fetch (per Plan v13 Critical Risk #3).
        assert "api.post" in source or "api.get" in source, (
            f"Hook file changed shape; AST extractor expects api.<verb>(...). "
            f"If migrated to raw fetch(), update extractor + Plan v13 Critical Risk #3."
        )

        # Print template-literal calls for visibility (skipped from assertion)
        template_hits = TEMPLATE_LITERAL_RE.findall(source)
        if template_hits:
            print(
                f"\n[contract-test] {len(template_hits)} template-literal api calls "
                f"skipped (not falsifiable via static extraction): {template_hits}"
            )

        extracted = [
            (verb.upper(), f"/api/v1{path}")
            for verb, path in API_CALL_RE.findall(source)
        ]
        assert extracted, (
            f"Extractor found 0 static api.<verb>('...') calls in {HOOK_FILE}. "
            f"Either the hook moved to template literals (update extractor) "
            f"or the regex is broken."
        )

        missing = [pair for pair in extracted if pair not in app_routes]
        assert not missing, (
            f"Frontend hook calls these routes; backend has NOT registered them: "
            f"{missing}.\n"
            f"Likely #373-class regression. Either fix the hook path or register "
            f"the backend route. Hook file: {HOOK_FILE}"
        )

    def test_telegram_di_contract_present(self):
        """Sanity: PR #372's TestDIContract (sibling guard) MUST still exist.

        If this test goes missing, the regression-guard layer is degrading.
        """
        from tests.api.routes import test_telegram

        assert hasattr(test_telegram, "TestDIContract"), (
            "PR #372's TestDIContract was removed. That regression guard catches "
            "DI-factory drift; PR-A's contract test catches FE→BE path drift. "
            "Both must coexist."
        )
