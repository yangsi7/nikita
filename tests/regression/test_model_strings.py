"""Regression tests for LLM model string consistency.

Prevents:
- Outdated model versions slipping in via copy-paste
- Missing anthropic: prefix for Pydantic AI
- Unpinned -latest aliases
- Typos in model IDs (validated via Anthropic API)
"""
import os
import re

import pytest
from pathlib import Path

# Approved model strings (update when upgrading models)
APPROVED_SONNET = "claude-sonnet-4-6"
APPROVED_HAIKU = "claude-haiku-4-5-20251001"
APPROVED_OPUS = "claude-opus-4-6"

APPROVED_MODELS = {
    APPROVED_SONNET,
    APPROVED_HAIKU,
    APPROVED_OPUS,
    f"anthropic:{APPROVED_SONNET}",
    f"anthropic:{APPROVED_HAIKU}",
    f"anthropic:{APPROVED_OPUS}",
}

# Bare model IDs (without anthropic: prefix) for API validation
APPROVED_BARE_MODELS = {APPROVED_SONNET, APPROVED_HAIKU, APPROVED_OPUS}

# Known non-model strings that match patterns (e.g. docstring examples)
KNOWN_EXCEPTIONS = {
    "nikita/agents/voice/models.py",  # docstring example only
}

NIKITA_SRC = Path("nikita")


def _find_model_strings() -> list[tuple[str, int, str]]:
    """Scan all .py files under nikita/ for Claude model string literals."""
    results = []
    pattern = re.compile(r"""['"](?:anthropic:)?claude-[a-z0-9\-\.]+['"]""")
    for py_file in NIKITA_SRC.rglob("*.py"):
        rel = str(py_file.relative_to(NIKITA_SRC.parent))
        if rel in KNOWN_EXCEPTIONS:
            continue
        for i, line in enumerate(py_file.read_text().splitlines(), 1):
            # Skip comments
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for match in pattern.finditer(line):
                model_str = match.group().strip("'\"")
                results.append((rel, i, model_str))
    return results


class TestModelStringConsistency:
    """Ensure all model strings use approved latest versions."""

    def test_no_outdated_models(self):
        """Every Claude model string in nikita/ must be in APPROVED_MODELS."""
        violations = []
        for filepath, line_num, model_str in _find_model_strings():
            if model_str not in APPROVED_MODELS:
                violations.append(f"  {filepath}:{line_num} — {model_str}")
        assert not violations, (
            f"Found {len(violations)} outdated/unapproved model strings:\n"
            + "\n".join(violations)
            + f"\n\nApproved models: {APPROVED_MODELS}"
        )

    def test_no_latest_aliases(self):
        """No -latest aliases allowed (non-deterministic between deploys)."""
        violations = []
        for filepath, line_num, model_str in _find_model_strings():
            if "-latest" in model_str:
                violations.append(f"  {filepath}:{line_num} — {model_str}")
        assert not violations, (
            f"Found {len(violations)} unpinned -latest model aliases:\n"
            + "\n".join(violations)
        )

    def test_no_missing_prefix(self):
        """Model strings used with Pydantic AI Agent() should have anthropic: prefix.

        Note: AnthropicModel() constructor uses bare names — that's OK.
        This test catches bare names in model= string args.
        """
        violations = []
        # Look for model="claude-..." (without anthropic: prefix) in Agent() or similar
        pattern = re.compile(r'model\s*=\s*["\']claude-')
        for py_file in NIKITA_SRC.rglob("*.py"):
            rel = str(py_file.relative_to(NIKITA_SRC.parent))
            if rel in KNOWN_EXCEPTIONS:
                continue
            for i, line in enumerate(py_file.read_text().splitlines(), 1):
                if pattern.search(line):
                    violations.append(f"  {rel}:{i} — {line.strip()}")
        # Allow known bare-name usages (AnthropicModel constructor, settings defaults)
        # Filter out AnthropicModel(...) and Field(default=...) patterns
        real_violations = [
            v for v in violations
            if "AnthropicModel" not in v and "Field(" not in v and "default=" not in v
        ]
        assert not real_violations, (
            f"Found {len(real_violations)} model strings missing anthropic: prefix:\n"
            + "\n".join(real_violations)
        )


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set — skipping live model validation",
)
class TestModelExistence:
    """Validate approved model IDs actually exist via Anthropic API.

    Catches typos in APPROVED_MODELS that static tests can't detect.
    Requires ANTHROPIC_API_KEY; skipped in CI without credentials.
    """

    @pytest.fixture(scope="class")
    def client(self):
        """Create Anthropic client once per test class."""
        import anthropic
        return anthropic.Anthropic()

    @pytest.mark.parametrize("model_id", sorted(APPROVED_BARE_MODELS))
    def test_model_responds(self, client, model_id: str):
        """Each approved model must accept a minimal API call.

        A 1-token request costs <$0.001 and proves the model ID is valid.
        If the model doesn't exist, Anthropic returns NotFoundError.
        """
        import anthropic

        try:
            response = client.messages.create(
                model=model_id,
                max_tokens=1,
                messages=[{"role": "user", "content": "hi"}],
            )
            assert response.id, f"Model {model_id} returned empty response"
        except anthropic.NotFoundError:
            pytest.fail(
                f"Model '{model_id}' does not exist — "
                f"Anthropic returned 404. Check for typos in APPROVED_MODELS."
            )
        except anthropic.BadRequestError as e:
            # Model exists but rejected our request (e.g., content filter)
            # — that's fine, it proves the model ID is valid
            if "not found" in str(e).lower() or "does not exist" in str(e).lower():
                pytest.fail(f"Model '{model_id}' not found: {e}")
            # Other BadRequestErrors mean the model exists
