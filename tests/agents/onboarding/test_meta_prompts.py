"""B1.6 / B1.7 — M1-M4 meta-prompt template presence + structure.

This tests the static templates and cluster taxonomies. Live LLM behavior
is exercised in higher-level integration tests; here we verify the
strings exist with the right [FIXED]/[DYNAMIC] structure and that
M2 cluster taxonomies cover all 4 prose-slot kinds.
"""

from __future__ import annotations

import pytest


def _imports():
    from nikita.agents.onboarding.conversation_prompts import (  # noqa: PLC0415
        M1_GENERATE_FOLLOW_UP,
        M2_CLASSIFY_ANSWER_CLUSTER,
        M3_REFINE_SUMMARY,
        M4_DETECT_SATURATION,
        CLUSTER_TAXONOMIES,
    )
    return (
        M1_GENERATE_FOLLOW_UP,
        M2_CLASSIFY_ANSWER_CLUSTER,
        M3_REFINE_SUMMARY,
        M4_DETECT_SATURATION,
        CLUSTER_TAXONOMIES,
    )


class TestMetaPromptTemplates:
    def test_m1_has_fixed_and_dynamic_blocks(self):
        m1, _, _, _, _ = _imports()
        assert "[FIXED]" in m1
        assert "[DYNAMIC]" in m1
        assert "DynamicFollowUp" in m1
        assert m1.find("[FIXED]") < m1.find("[DYNAMIC]"), (
            "[FIXED] block must come before [DYNAMIC] for prompt-cache breakpoint"
        )

    def test_m2_has_fixed_and_dynamic_blocks(self):
        _, m2, _, _, _ = _imports()
        assert "[FIXED]" in m2
        assert "[DYNAMIC]" in m2
        assert "AnswerCluster" in m2
        assert "ambiguous" in m2

    def test_m3_has_fixed_and_dynamic_blocks(self):
        _, _, m3, _, _ = _imports()
        assert "[FIXED]" in m3
        assert "[DYNAMIC]" in m3
        assert "PromptSummary" in m3 or "summary" in m3.lower()

    def test_m4_has_fixed_and_dynamic_blocks(self):
        _, _, _, m4, _ = _imports()
        assert "[FIXED]" in m4
        assert "[DYNAMIC]" in m4
        assert "SaturationSignal" in m4
        # HARD OVERRIDES section
        assert "HARD OVERRIDES" in m4 or "move_on" in m4.lower()


class TestClusterTaxonomies:
    """B1.7 — cluster taxonomies for prose-answer slots."""

    def test_taxonomy_covers_four_prose_slots(self):
        _, _, _, _, taxonomies = _imports()
        # M2 §spec: hobbies, saturday_morning, geek_out_on, together_we_could
        for key in (
            "primary_hobbies",
            "saturday_morning",
            "geek_out_on",
            "together_we_could",
        ):
            assert key in taxonomies, f"cluster taxonomy missing for {key}"

    def test_every_taxonomy_includes_ambiguous(self):
        _, _, _, _, taxonomies = _imports()
        for slot, clusters in taxonomies.items():
            assert "ambiguous" in clusters, (
                f"taxonomy for {slot} must include 'ambiguous' cluster"
            )

    def test_hobbies_taxonomy_has_expected_clusters(self):
        _, _, _, _, taxonomies = _imports()
        hobbies = set(taxonomies["primary_hobbies"])
        # spec.md M2: 6 + ambiguous = 7
        expected_subset = {
            "aesthete", "kinetic", "digital_nomad",
            "homemaker", "nightlife", "outdoorsy", "ambiguous",
        }
        assert expected_subset.issubset(hobbies), (
            f"primary_hobbies taxonomy missing: {expected_subset - hobbies}"
        )

    def test_saturday_morning_taxonomy_has_expected_clusters(self):
        _, _, _, _, taxonomies = _imports()
        sat = set(taxonomies["saturday_morning"])
        expected_subset = {"movement", "quiet", "social", "chaos", "ambiguous"}
        assert expected_subset.issubset(sat)

    def test_geek_out_on_taxonomy_has_expected_clusters(self):
        _, _, _, _, taxonomies = _imports()
        geek = set(taxonomies["geek_out_on"])
        expected_subset = {"hands_on", "system", "culture", "human", "ambiguous"}
        assert expected_subset.issubset(geek)

    def test_together_we_could_taxonomy_has_expected_clusters(self):
        _, _, _, _, taxonomies = _imports()
        tg = set(taxonomies["together_we_could"])
        expected_subset = {"risk", "refuge", "craft", "discovery", "ritual", "ambiguous"}
        assert expected_subset.issubset(tg)
