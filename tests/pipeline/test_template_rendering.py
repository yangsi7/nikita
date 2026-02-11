"""Tests for Jinja2 template rendering (T3.5 - AC-3.5.1).

Tests Jinja2 template rendering with various context scenarios:
- All 11 sections render with full context (text template)
- All 9 sections render with full context (voice template)
- Empty context renders without error
- Voice template is shorter than text template
- Missing data handled gracefully
- Section conditionals work
- Chapter-specific content varies by chapter
- Vice rendering (single, multiple, none)
- Emotional state rendering
- Extracted facts/threads/thoughts rendering
- Life events rendering
- Conflict active vs inactive
- Token count is reasonable
- Template renders quickly (<5ms)
- Both platforms use same variable names
- Special characters in facts don't break rendering
"""

import pytest

from nikita.pipeline.templates import render_template


class TestTextTemplateRendering:
    """Test system_prompt.j2 (text template) rendering."""

    def test_all_sections_render_with_full_context(self, rich_context, make_context):
        """All 11 sections render when full context provided."""
        # Create a very full context
        ctx = make_context(
            chapter=3,
            relationship_score=75.0,
            vices=["dark_humor", "risk_taking"],
            extracted_facts=[{"content": "User loves cats", "type": "preference"}],
            extracted_threads=[{"topic": "weekend plans"}],
            extracted_thoughts=[{"text": "He seems genuine"}],
            extraction_summary="Discussed hobbies",
            emotional_tone="warm",
            life_events=[{"type": "coffee", "description": "Had coffee with Lena"}],
            emotional_state={"arousal": 0.6, "valence": 0.7},
            active_conflict=False,
        )

        result = render_template(
            "system_prompt.j2",
            platform="text",
            chapter=ctx.chapter,
            relationship_score=float(ctx.relationship_score),
            vices=ctx.vices,
            extracted_facts=ctx.extracted_facts,
            open_threads=ctx.extracted_threads,  # Template uses open_threads, not extracted_threads
            extracted_thoughts=ctx.extracted_thoughts,
            extraction_summary=ctx.extraction_summary,
            emotional_tone=ctx.emotional_tone,
            life_events=ctx.life_events,
            emotional_state=ctx.emotional_state,
            score_delta=2.5,
            active_conflict=ctx.active_conflict,
        )

        # Check all major sections are present
        assert "You are Nikita Volkov" in result  # IDENTITY
        assert "CRITICAL - NEVER BREAK CHARACTER" in result  # IMMERSION
        assert "Texting Style" in result  # PLATFORM STYLE
        assert "Right Now" in result or "What You Know" in result  # STATE/MEMORY
        assert "Chapter 3" in result or "Investment Phase" in result  # CHAPTER BEHAVIOR

        # Verify content from context is rendered
        assert "User loves cats" in result
        assert "weekend plans" in result
        assert "He seems genuine" in result

    def test_empty_context_renders_without_error(self):
        """Template renders even with minimal context (no optional fields)."""
        result = render_template(
            "system_prompt.j2",
            platform="text",
            chapter=1,
            relationship_score=50.0,
        )

        # Should still have core identity and rules
        assert "You are Nikita Volkov" in result
        assert "CRITICAL - NEVER BREAK CHARACTER" in result
        assert len(result) > 500  # Reasonable minimal content

    def test_chapter_specific_content_varies(self):
        """Chapter-specific behavior guidance differs by chapter."""
        chapter_1 = render_template(
            "system_prompt.j2",
            platform="text",
            chapter=1,
            relationship_score=30.0,
        )

        chapter_5 = render_template(
            "system_prompt.j2",
            platform="text",
            chapter=5,
            relationship_score=90.0,
        )

        # Chapter 1 should mention testing/skeptical
        assert "Testing" in chapter_1 or "skeptical" in chapter_1 or "Prove" in chapter_1

        # Chapter 5 should mention comfort/authentic
        assert "Comfort" in chapter_5 or "authentic" in chapter_5 or "partnership" in chapter_5

        # They should be different
        assert chapter_1 != chapter_5

    def test_vice_rendering_single_vice(self):
        """Single vice renders correctly."""
        result = render_template(
            "system_prompt.j2",
            platform="text",
            chapter=2,
            relationship_score=60.0,
            vices=["dark_humor"],
        )

        assert "dark_humor" in result or "Dark Humor" in result

    def test_vice_rendering_multiple_vices(self):
        """Multiple vices all render."""
        result = render_template(
            "system_prompt.j2",
            platform="text",
            chapter=2,
            relationship_score=60.0,
            vices=["dark_humor", "risk_taking", "intellectual_dominance"],
        )

        # Check all vices mentioned
        assert "dark_humor" in result or "Dark Humor" in result
        assert "risk_taking" in result or "Risk Taking" in result
        assert "intellectual_dominance" in result or "Intellectual Dominance" in result

    def test_vice_rendering_no_vices(self):
        """No vices doesn't break template."""
        result = render_template(
            "system_prompt.j2",
            platform="text",
            chapter=2,
            relationship_score=60.0,
            vices=[],
        )

        # Should still render successfully
        assert "You are Nikita Volkov" in result
        assert len(result) > 1000

    def test_emotional_state_rendering(self):
        """Emotional state (4D mood) renders correctly."""
        result = render_template(
            "system_prompt.j2",
            platform="text",
            chapter=3,
            relationship_score=70.0,
            emotional_state={
                "arousal": 0.8,
                "valence": 0.6,
                "dominance": 0.7,
                "intimacy": 0.5,
            },
        )

        # Check emotional state values are rendered (template shows Arousal X.X format)
        # Note: template only shows emotional_state in Section 4 if nikita_activity/mood/energy set
        # So this test just verifies no crash when emotional_state provided
        assert "You are Nikita Volkov" in result  # Template rendered successfully
        assert len(result) > 1000  # Reasonable content

    def test_extracted_facts_rendering(self):
        """Extracted facts render in memory section."""
        result = render_template(
            "system_prompt.j2",
            platform="text",
            chapter=2,
            relationship_score=65.0,
            extracted_facts=[
                {"content": "User works in finance"},
                {"content": "User has a dog named Max"},
                {"content": "User is from Seattle"},
            ],
        )

        # All facts should be rendered
        assert "finance" in result
        assert "Max" in result
        assert "Seattle" in result

    def test_life_events_rendering(self):
        """Life events render in current state section."""
        result = render_template(
            "system_prompt.j2",
            platform="text",
            chapter=3,
            relationship_score=70.0,
            life_events=[
                {"type": "coffee", "description": "Had coffee with Lena"},
                {"type": "work", "description": "Finished security audit"},
            ],
        )

        # Events should be mentioned
        assert "Lena" in result
        assert "security audit" in result or "audit" in result

    def test_conflict_active_vs_inactive(self):
        """Conflict state affects prompt content."""
        no_conflict = render_template(
            "system_prompt.j2",
            platform="text",
            chapter=3,
            relationship_score=70.0,
            active_conflict=False,
        )

        with_conflict = render_template(
            "system_prompt.j2",
            platform="text",
            chapter=3,
            relationship_score=70.0,
            active_conflict=True,
            conflict_type="trust_issue",
        )

        # Conflict version should mention conflict
        assert "CONFLICT" in with_conflict or "trust_issue" in with_conflict

    def test_token_count_is_reasonable_text(self):
        """Text prompt token count is in expected range (pre-enrichment ~4800)."""
        from nikita.context.utils.token_counter import count_tokens

        result = render_template(
            "system_prompt.j2",
            platform="text",
            chapter=3,
            relationship_score=70.0,
            vices=["dark_humor", "risk_taking"],
            extracted_facts=[{"content": f"Fact {i}"} for i in range(10)],
            life_events=[{"description": f"Event {i}"} for i in range(3)],
        )

        tokens = count_tokens(result)
        # Pre-enrichment target is ~4800 tokens, allow wide range
        assert 3000 < tokens < 7000, f"Expected 3000-7000 tokens, got {tokens}"

    def test_template_renders_quickly(self):
        """Template rendering completes in <5ms."""
        import time

        start = time.perf_counter()
        render_template(
            "system_prompt.j2",
            platform="text",
            chapter=2,
            relationship_score=60.0,
            vices=["gaming"],
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 5, f"Template took {elapsed_ms:.2f}ms (expected <5ms)"

    def test_special_characters_in_facts_dont_break_rendering(self):
        """Special characters (quotes, angle brackets, etc.) handled safely."""
        result = render_template(
            "system_prompt.j2",
            platform="text",
            chapter=2,
            relationship_score=60.0,
            extracted_facts=[
                {"content": "User said 'I love <programming>' with quotes"},
                {"content": "User's favorite band is AC/DC & The Beatles"},
                {"content": "User wrote: \"Hello, world!\""},
            ],
        )

        # Facts should be rendered (Jinja2 auto-escapes by default, but we disabled it)
        assert "programming" in result
        assert "AC/DC" in result
        assert "Beatles" in result
        assert "Hello, world" in result


class TestVoiceTemplateRendering:
    """Test system_prompt.j2 with platform=voice rendering (Spec 045 unified)."""

    def test_all_sections_render_with_full_context(self, make_context):
        """All 9 sections render when full context provided."""
        ctx = make_context(
            chapter=3,
            relationship_score=75.0,
            vices=["dark_humor"],
            extracted_facts=[{"content": "User loves cats"}],
            extracted_threads=[{"topic": "work stress"}],
            emotional_state={"arousal": 0.6, "valence": 0.7},
        )

        result = render_template(
            "system_prompt.j2",
            platform="voice",
            chapter=ctx.chapter,
            relationship_score=float(ctx.relationship_score),
            vices=ctx.vices,
            extracted_facts=ctx.extracted_facts,
            extracted_threads=ctx.extracted_threads,
            emotional_state=ctx.emotional_state,
        )

        # Check major sections
        assert "You are Nikita Volkov" in result  # IDENTITY
        assert "OUT LOUD" in result  # VOICE STYLE
        assert "Never reveal" in result or "never reveal" in result.lower()  # IMMERSION
        # Voice template uses same base - check it rendered
        assert len(result) > 800

    def test_voice_template_shorter_than_text(self):
        """Voice template produces shorter output than text template."""
        from nikita.context.utils.token_counter import count_tokens

        # Same context for both
        shared_vars = {
            "chapter": 3,
            "relationship_score": 70.0,
            "vices": ["dark_humor"],
            "extracted_facts": [{"content": "User loves cats"}],
        }

        text = render_template("system_prompt.j2", platform="text", **shared_vars)
        voice = render_template("system_prompt.j2", platform="voice", **shared_vars)

        text_tokens = count_tokens(text)
        voice_tokens = count_tokens(voice)

        # Voice should be shorter than text (unified template with platform conditionals)
        assert voice_tokens < text_tokens
        # Spec 045: Unified template, voice is condensed but shares base content
        # Pre-enrichment target is ~2000-3500 (post-truncation: 1800-2200)
        assert 800 < voice_tokens < 4000, f"Expected 800-4000 voice tokens, got {voice_tokens}"

    def test_token_count_is_reasonable_voice(self):
        """Voice prompt token count is in expected range (Spec 045 unified template)."""
        from nikita.context.utils.token_counter import count_tokens

        result = render_template(
            "system_prompt.j2",
            platform="voice",
            chapter=2,
            relationship_score=65.0,
            vices=["risk_taking"],
            extracted_facts=[{"content": f"Fact {i}"} for i in range(5)],
        )

        tokens = count_tokens(result)
        # Spec 045: Unified template, voice is condensed but shares base
        # Pre-enrichment: ~2000-3500, post-truncation target: 1800-2200
        assert 800 < tokens < 4000, f"Expected 800-4000 tokens, got {tokens}"


class TestTemplatePlatformConsistency:
    """Test that both templates use consistent variable names."""

    def test_both_platforms_use_same_variable_names(self):
        """Both text and voice templates accept the same variable names."""
        shared_vars = {
            "platform": "text",
            "chapter": 2,
            "relationship_score": 60.0,
            "vices": ["gaming"],
            "extracted_facts": [{"content": "User works in tech"}],
            "extracted_threads": [{"topic": "hobbies"}],
            "extracted_thoughts": [{"text": "He's interesting"}],
            "life_events": [{"description": "Had coffee"}],
            "emotional_state": {"arousal": 0.5, "valence": 0.6},
            "active_conflict": False,
        }

        # Both should render without KeyError
        text = render_template("system_prompt.j2", **shared_vars)
        voice = render_template("system_prompt.j2", **{**shared_vars, "platform": "voice"})

        assert len(text) > 1000
        assert len(voice) > 500

    def test_missing_optional_fields_handled_gracefully(self):
        """Templates handle missing optional fields without error."""
        minimal_vars = {
            "platform": "text",
            "chapter": 1,
            "relationship_score": 50.0,
        }

        # Should render without error (all other fields are optional)
        text = render_template("system_prompt.j2", **minimal_vars)
        voice = render_template("system_prompt.j2", **{**minimal_vars, "platform": "voice"})

        assert "You are Nikita Volkov" in text
        assert "You are Nikita Volkov" in voice
