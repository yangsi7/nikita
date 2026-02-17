"""Tests for Spec 060: Token budget correction and validation.

TDD-RED: Validates template header accuracy and budget constant alignment.
"""

import os

import pytest


class TestTemplateHeader:
    """Verify system_prompt.j2 header has updated token counts."""

    def test_template_header_has_text_token_count(self):
        """T2.1-1: Template header mentions ~5,400 tokens for text."""
        template_path = os.path.join(
            os.path.dirname(__file__),
            "../../../nikita/pipeline/templates/system_prompt.j2",
        )
        # Normalize path
        template_path = os.path.normpath(template_path)

        with open(template_path) as f:
            header = f.read(500)  # Read first 500 chars (header area)

        assert "5,400" in header, (
            f"Template header should mention ~5,400 tokens for text. "
            f"Found: {header[:200]}"
        )

    def test_template_header_has_voice_token_count(self):
        """T2.1-2: Template header mentions ~4,400 tokens for voice."""
        template_path = os.path.join(
            os.path.dirname(__file__),
            "../../../nikita/pipeline/templates/system_prompt.j2",
        )
        template_path = os.path.normpath(template_path)

        with open(template_path) as f:
            header = f.read(500)

        assert "4,400" in header, (
            f"Template header should mention ~4,400 tokens for voice. "
            f"Found: {header[:200]}"
        )


class TestTokenBudgetConstants:
    """Verify TOKEN_MIN/MAX constants are reasonable for current template."""

    def test_text_token_min_is_reasonable(self):
        """T2.1-3: TEXT_TOKEN_MIN should be >= 5000 (template base is ~5,400)."""
        from nikita.pipeline.stages.prompt_builder import PromptBuilderStage

        assert PromptBuilderStage.TEXT_TOKEN_MIN >= 5000

    def test_text_token_max_is_reasonable(self):
        """T2.1-4: TEXT_TOKEN_MAX should allow enrichment headroom (>= 6000)."""
        from nikita.pipeline.stages.prompt_builder import PromptBuilderStage

        assert PromptBuilderStage.TEXT_TOKEN_MAX >= 6000
        # But not absurdly high
        assert PromptBuilderStage.TEXT_TOKEN_MAX <= 10000
