"""B1.9 — Static fallback registry completeness.

Every (slot, cluster) pair in CLUSTER_TAXONOMIES must have a
``static_fallback_question`` entry in ``follow_up_registry.yaml``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_REGISTRY_PATH = _REPO_ROOT / "nikita" / "agents" / "onboarding" / "follow_up_registry.yaml"


def _load_registry():
    import yaml  # noqa: PLC0415
    return yaml.safe_load(_REGISTRY_PATH.read_text())


def _import_taxonomies():
    from nikita.agents.onboarding.conversation_prompts import (  # noqa: PLC0415
        CLUSTER_TAXONOMIES,
    )
    return CLUSTER_TAXONOMIES


class TestFollowUpRegistryCompleteness:
    def test_registry_file_exists(self):
        assert _REGISTRY_PATH.exists(), (
            f"follow_up_registry.yaml missing at {_REGISTRY_PATH}"
        )

    def test_every_dynamic_node_has_static_fallback(self):
        """For each (slot, cluster) pair in taxonomies, the registry has a
        static_fallback_question entry."""
        registry = _load_registry()
        tax = _import_taxonomies()
        missing_entries: list[str] = []
        for slot, clusters in tax.items():
            slot_block = registry.get(slot, {})
            for cluster in clusters:
                entry = slot_block.get(cluster, {})
                if not isinstance(entry, dict):
                    missing_entries.append(f"{slot}.{cluster}: not a dict")
                    continue
                if not entry.get("static_fallback_question"):
                    missing_entries.append(
                        f"{slot}.{cluster}: missing static_fallback_question"
                    )
        assert not missing_entries, (
            "Incomplete fallback registry:\n  " + "\n  ".join(missing_entries)
        )

    def test_every_entry_has_required_keys(self):
        """Each (slot, cluster) entry must declare static_fallback_question,
        why_we_ask, control_type."""
        registry = _load_registry()
        tax = _import_taxonomies()
        for slot, clusters in tax.items():
            slot_block = registry.get(slot, {})
            for cluster in clusters:
                entry = slot_block.get(cluster, {})
                assert isinstance(entry, dict), f"{slot}.{cluster} not a dict"
                for key in ("static_fallback_question", "why_we_ask", "control_type"):
                    assert key in entry, (
                        f"{slot}.{cluster} missing key {key!r}"
                    )
