"""Make the repo-root ``scripts/`` package importable from tests.

The repo's ``scripts/`` directory is intentionally NOT a package (no
``__init__.py``); pytest still resolves ``from scripts.models import X``
inside test bodies because rootdir gets added to ``sys.path`` lazily.
However, module-level imports during collection see a snapshot of
``sys.path`` BEFORE that lazy injection, so collection fails when this
file is reached as part of the full suite (works in isolation).

Adding the repo root to ``sys.path`` here, at conftest load (which fires
before any test module in this directory is imported), guarantees
``import scripts.models.heartbeat_live_parity`` resolves at collection
time. Mirrors the same pattern used in tests/heartbeat/test_intensity.py
where the import is deferred to function body — we can't defer here
because the module-level ``patch(...)`` decorators need the symbol
present at import.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
