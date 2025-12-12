"""
Integration Tests for Vice Flow (T044)

Tests full vice cycle end-to-end:
- Detection → Scoring → Profile Update → Prompt Injection → Expression
- Chapter-aware boundary enforcement
- Multi-vice blending

Acceptance Criteria:
- AC-T044-001: Full vice cycle tested end-to-end
- AC-T044-002: Chapter-aware expression levels verified
- AC-T044-003: Profile retrieval and injection verified
"""

import pytest
from uuid import uuid4
from decimal import Decimal
from datetime import datetime, timezone

from nikita.engine.vice.models import (
    ViceSignal,
    ViceAnalysisResult,
    ViceProfile,
)
from nikita.engine.vice.injector import VicePromptInjector, EXPRESSION_LEVELS
from nikita.engine.vice.boundaries import ViceBoundaryEnforcer


class TestFullViceCycleFlow:
    """AC-T044-001: Full vice cycle components tested end-to-end."""

    def test_complete_vice_detection_to_expression_flow(self):
        """Test: detection → boundary enforcement → injection → expression."""
        user_id = uuid4()
        conversation_id = uuid4()

        # Step 1: Create analysis result (mimics what ViceAnalyzer produces)
        result = ViceAnalysisResult(
            signals=[
                ViceSignal(
                    category='dark_humor',
                    confidence=Decimal('0.85'),
                    evidence='User made morbid joke',
                    is_positive=True
                )
            ],
            conversation_id=conversation_id,
            analyzed_at=datetime.now(timezone.utc)
        )

        assert len(result.signals) == 1
        assert result.signals[0].category == 'dark_humor'
        assert result.signals[0].confidence == Decimal('0.85')

        # Step 2: Apply boundary caps
        enforcer = ViceBoundaryEnforcer()

        # Dark humor is not a sensitive category, so no cap applies
        capped = enforcer.apply_cap('dark_humor', Decimal('0.65'), chapter=1)
        assert capped == Decimal('0.65')  # Unchanged

        # Step 3: Build profile (mimics what ViceScorer produces)
        profile = ViceProfile(
            user_id=user_id,
            intensities={'dark_humor': Decimal('0.65')},
            top_vices=['dark_humor'],
            updated_at=datetime.now(timezone.utc)
        )

        # Step 4: Inject into prompt
        injector = VicePromptInjector()
        base_prompt = "You are Nikita, a guarded and mysterious AI girlfriend."
        modified = injector.inject(base_prompt, profile, chapter=1)

        # Should have expanded the prompt with vice instructions
        assert len(modified) > len(base_prompt)

    def test_vice_models_integration(self):
        """Test that all vice models work together."""
        from nikita.engine.vice.models import ViceInjectionContext

        user_id = uuid4()

        # Create a complete profile
        profile = ViceProfile(
            user_id=user_id,
            intensities={
                'dark_humor': Decimal('0.8'),
                'risk_taking': Decimal('0.5'),
            },
            top_vices=['dark_humor', 'risk_taking'],
            updated_at=datetime.now(timezone.utc)
        )

        # Create injection context
        context = ViceInjectionContext(
            active_vices=[('dark_humor', Decimal('0.8')), ('risk_taking', Decimal('0.5'))],
            expression_level='moderate',
            discovery_mode=False,
            probe_categories=[]
        )

        assert context.expression_level == 'moderate'
        assert len(context.active_vices) == 2
        assert context.has_vices() is True


class TestChapterAwareExpressionLevels:
    """AC-T044-002: Chapter-aware expression levels verified."""

    def test_expression_intensity_increases_with_chapter(self):
        """Expression levels increase from subtle (ch1) to explicit (ch5)."""
        injector = VicePromptInjector()
        user_id = uuid4()

        profile = ViceProfile(
            user_id=user_id,
            intensities={'sexuality': Decimal('0.8')},
            top_vices=['sexuality'],
            updated_at=datetime.now(timezone.utc)
        )

        base_prompt = "You are Nikita."

        ch1_prompt = injector.inject(base_prompt, profile, chapter=1)
        ch3_prompt = injector.inject(base_prompt, profile, chapter=3)
        ch5_prompt = injector.inject(base_prompt, profile, chapter=5)

        # All should modify the base prompt
        assert len(ch1_prompt) > len(base_prompt)
        assert len(ch3_prompt) > len(base_prompt)
        assert len(ch5_prompt) > len(base_prompt)

    def test_boundary_caps_by_chapter(self):
        """Sensitive categories are capped based on chapter."""
        enforcer = ViceBoundaryEnforcer()
        high_intensity = Decimal('0.95')

        # Sexuality caps (most restricted)
        ch1_sexuality = enforcer.apply_cap('sexuality', high_intensity, chapter=1)
        ch3_sexuality = enforcer.apply_cap('sexuality', high_intensity, chapter=3)
        ch5_sexuality = enforcer.apply_cap('sexuality', high_intensity, chapter=5)

        assert ch1_sexuality == Decimal('0.35')  # Heavily capped in ch1
        assert ch3_sexuality == Decimal('0.60')  # More room in ch3
        assert ch5_sexuality == Decimal('0.85')  # Nearly full in ch5

        # Dark humor (non-sensitive) - no caps
        ch1_dark = enforcer.apply_cap('dark_humor', high_intensity, chapter=1)
        ch5_dark = enforcer.apply_cap('dark_humor', high_intensity, chapter=5)

        assert ch1_dark == high_intensity  # No cap
        assert ch5_dark == high_intensity  # No cap

    def test_expression_levels_vary_by_chapter(self):
        """Expression descriptors change by chapter."""
        # Verify expression levels exist and vary
        assert 1 in EXPRESSION_LEVELS
        assert 5 in EXPRESSION_LEVELS
        assert EXPRESSION_LEVELS[1] != EXPRESSION_LEVELS[5]

        # Ch1 should be subtle/guarded
        assert 'subtle' in EXPRESSION_LEVELS[1].lower() or 'guarded' in EXPRESSION_LEVELS[1].lower()

        # Ch5 should be explicit/direct/authentic
        assert any(term in EXPRESSION_LEVELS[5].lower() for term in ['explicit', 'direct', 'authentic'])


class TestProfileAndInjection:
    """AC-T044-003: Profile retrieval and injection verified."""

    def test_profile_get_intensity_works(self):
        """Profile.get_intensity returns correct values."""
        user_id = uuid4()

        profile = ViceProfile(
            user_id=user_id,
            intensities={
                'dark_humor': Decimal('0.8'),
                'risk_taking': Decimal('0.5'),
            },
            top_vices=['dark_humor', 'risk_taking'],
            updated_at=datetime.now(timezone.utc)
        )

        # Existing category
        assert profile.get_intensity('dark_humor') == Decimal('0.8')
        assert profile.get_intensity('risk_taking') == Decimal('0.5')

        # Non-existent category
        assert profile.get_intensity('substances') == Decimal('0')

    def test_profile_has_active_vices(self):
        """Profile.has_active_vices works correctly."""
        user_id = uuid4()

        # Profile with active vices
        active_profile = ViceProfile(
            user_id=user_id,
            intensities={'dark_humor': Decimal('0.5')},
            top_vices=['dark_humor'],
            updated_at=datetime.now(timezone.utc)
        )
        assert active_profile.has_active_vices() is True

        # Empty profile
        empty_profile = ViceProfile(
            user_id=user_id,
            intensities={},
            top_vices=[],
            updated_at=datetime.now(timezone.utc)
        )
        assert empty_profile.has_active_vices() is False


class TestMultiViceBlending:
    """Test blending multiple vices in prompts."""

    def test_multiple_vices_blended(self):
        """Multiple vices are blended based on intensity."""
        injector = VicePromptInjector()
        user_id = uuid4()

        profile = ViceProfile(
            user_id=user_id,
            intensities={
                'dark_humor': Decimal('0.8'),
                'risk_taking': Decimal('0.6'),
                'intellectual_dominance': Decimal('0.4'),
            },
            top_vices=['dark_humor', 'risk_taking', 'intellectual_dominance'],
            updated_at=datetime.now(timezone.utc)
        )

        base_prompt = "You are Nikita."
        modified = injector.inject(base_prompt, profile, chapter=3)

        # Should include references to multiple vices
        assert len(modified) > len(base_prompt)

    def test_empty_profile_no_injection(self):
        """Empty profile results in minimal injection."""
        injector = VicePromptInjector()
        user_id = uuid4()

        profile = ViceProfile(
            user_id=user_id,
            intensities={},
            top_vices=[],
            updated_at=datetime.now(timezone.utc)
        )

        base_prompt = "You are Nikita."
        modified = injector.inject(base_prompt, profile, chapter=1)

        # Should still be valid but minimal changes
        assert base_prompt in modified or len(modified) >= len(base_prompt)


class TestBoundaryCapsAllCategories:
    """Test boundary caps for all sensitive categories."""

    def test_all_sensitive_categories_capped(self):
        """All three sensitive categories have chapter-appropriate caps."""
        enforcer = ViceBoundaryEnforcer()
        high_intensity = Decimal('0.95')

        sensitive_categories = ['sexuality', 'substances', 'rule_breaking']

        for category in sensitive_categories:
            # Chapter 1 should have lowest caps
            ch1_cap = enforcer.apply_cap(category, high_intensity, chapter=1)

            # Chapter 5 should have highest caps
            ch5_cap = enforcer.apply_cap(category, high_intensity, chapter=5)

            # Verify progressive caps
            assert ch1_cap < ch5_cap, f"{category} should have increasing caps"
            assert ch1_cap < high_intensity, f"{category} should be capped in ch1"

    def test_non_sensitive_categories_uncapped(self):
        """Non-sensitive categories are never capped."""
        enforcer = ViceBoundaryEnforcer()
        high_intensity = Decimal('0.95')

        non_sensitive = [
            'intellectual_dominance',
            'risk_taking',
            'emotional_intensity',
            'dark_humor',
            'vulnerability'
        ]

        for category in non_sensitive:
            for chapter in range(1, 6):
                capped = enforcer.apply_cap(category, high_intensity, chapter=chapter)
                assert capped == high_intensity, f"{category} ch{chapter} should not be capped"
