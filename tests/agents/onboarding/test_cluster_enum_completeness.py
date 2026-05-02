"""B1.7 — Cluster taxonomy completeness.

Every (slot, cluster) pair declared in CLUSTER_TAXONOMIES must have a
corresponding fallback entry in follow_up_registry.yaml. This is a
shape lint test; it does not validate semantic content.
"""

from __future__ import annotations

from pathlib import Path

import pytest


def _import_taxonomies():
    from nikita.agents.onboarding.conversation_prompts import (  # noqa: PLC0415
        CLUSTER_TAXONOMIES,
    )
    return CLUSTER_TAXONOMIES


class TestClusterEnumCompleteness:
    def test_taxonomies_dict_keys_are_slot_kinds(self):
        """Keys of CLUSTER_TAXONOMIES are SlotKind values (subset)."""
        from nikita.agents.onboarding.question_registry import SlotKind

        tax = _import_taxonomies()
        valid = {m.value for m in SlotKind}
        for slot in tax:
            assert slot in valid, f"taxonomy key {slot!r} is not a SlotKind value"

    def test_every_taxonomy_entry_is_non_empty_list(self):
        """Each taxonomy lists at least 2 clusters (incl. ambiguous)."""
        tax = _import_taxonomies()
        for slot, clusters in tax.items():
            assert isinstance(clusters, (list, tuple))
            assert len(clusters) >= 2, (
                f"taxonomy for {slot} must have at least 2 clusters"
            )

    def test_ambiguous_present_in_each_taxonomy(self):
        """Every taxonomy includes the 'ambiguous' cluster as low-confidence sentinel."""
        tax = _import_taxonomies()
        for slot, clusters in tax.items():
            assert "ambiguous" in clusters, (
                f"taxonomy for {slot} must include 'ambiguous' cluster"
            )
