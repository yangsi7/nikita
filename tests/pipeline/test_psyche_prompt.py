"""Tests for psyche state in pipeline prompt generation (Spec 056 T22).

AC coverage: AC-4.2, AC-7.2 (max 150 tokens)
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from nikita.agents.psyche.models import PsycheState


class TestPsycheL3TokenBudget:
    """Test L3 stays within 150 token budget (AC-7.2)."""

    def test_l3_under_150_tokens(self):
        """AC-7.2: L3 psyche block stays under 150 tokens."""
        from nikita.pipeline.templates import render_template

        psyche = PsycheState(
            attachment_activation="anxious",
            defense_mode="guarded",
            behavioral_guidance="Be careful with vulnerability topics. Watch for deflection patterns.",
            internal_monologue="Something feels different today.",
            vulnerability_level=0.3,
            emotional_tone="serious",
            topics_to_encourage=["music", "work"],
            topics_to_avoid=["past relationships", "family"],
        )

        # Render just the psyche section by rendering full template and extracting L3
        rendered = render_template(
            "system_prompt.j2",
            platform="text",
            psyche_state=psyche.model_dump(),
            chapter=2,
            relationship_score=60.0,
            game_status="active",
            engagement_state="engaged",
            vices=[],
            metrics={},
            user=None,
            extracted_facts=[],
            extracted_threads=[],
            extracted_thoughts=[],
            extraction_summary="",
            emotional_tone="neutral",
            life_events=[],
            emotional_state={},
            score_delta=0.0,
            active_conflict=False,
            conflict_type=None,
            touchpoint_scheduled=False,
            nikita_activity=None,
            nikita_mood=None,
            nikita_energy=None,
            time_of_day=None,
            vulnerability_level=2,
            nikita_daily_events=None,
            last_conversation_summary=None,
            today_summaries=None,
            week_summaries=None,
            hours_since_last=None,
            open_threads=[],
            relationship_episodes=[],
            nikita_events=[],
            inner_monologue=None,
            active_thoughts=[],
            user_id="test",
            conversation_id="test",
        )

        # Extract the L3 section
        start = rendered.find("**Current Psychological Disposition:**")
        if start == -1:
            pytest.fail("L3 section not found in rendered template")

        # Find the end of the L3 section (next section starts with {# or **)
        end = rendered.find("**Right Now:**", start)
        if end == -1:
            end = rendered.find("**Physical Context:**", start)
        if end == -1:
            end = len(rendered)

        l3_section = rendered[start:end].strip()

        # Count tokens (rough: words / 0.75)
        word_count = len(l3_section.split())
        estimated_tokens = int(word_count / 0.75)

        assert estimated_tokens < 150, (
            f"L3 section has ~{estimated_tokens} tokens (>{150} limit). "
            f"Section:\n{l3_section}"
        )

    def test_empty_psyche_state_zero_tokens(self):
        """AC-4.3: No psyche_state = 0 extra tokens."""
        from nikita.pipeline.templates import render_template

        rendered = render_template(
            "system_prompt.j2",
            platform="text",
            psyche_state=None,
            chapter=2,
            relationship_score=60.0,
            game_status="active",
            engagement_state="engaged",
            vices=[],
            metrics={},
            user=None,
            extracted_facts=[],
            extracted_threads=[],
            extracted_thoughts=[],
            extraction_summary="",
            emotional_tone="neutral",
            life_events=[],
            emotional_state={},
            score_delta=0.0,
            active_conflict=False,
            conflict_type=None,
            touchpoint_scheduled=False,
            nikita_activity=None,
            nikita_mood=None,
            nikita_energy=None,
            time_of_day=None,
            vulnerability_level=2,
            nikita_daily_events=None,
            last_conversation_summary=None,
            today_summaries=None,
            week_summaries=None,
            hours_since_last=None,
            open_threads=[],
            relationship_episodes=[],
            nikita_events=[],
            inner_monologue=None,
            active_thoughts=[],
            user_id="test",
            conversation_id="test",
        )

        assert "Current Psychological Disposition" not in rendered
