"""
Unit Tests for ViceBoundaryEnforcer (T035-T039)

Tests for:
- AC-FR010-001: Given high sexuality intensity, When expressing, Then flirtatious but not explicit
- AC-FR010-002: Given substances vice, When expressing, Then discusses but doesn't encourage
- AC-FR010-003: Given any vice pushed to extreme, When generating, Then content policy respected

TDD: Write tests FIRST, verify they fail, then implement.
"""

import pytest
from decimal import Decimal


class TestViceBoundaryEnforcer:
    """T036: ViceBoundaryEnforcer tests."""

    def test_ac_fr010_001_sexuality_capped_early_chapters(self):
        """AC-FR010-001: Sexuality intensity capped in early chapters."""
        from nikita.engine.vice.boundaries import ViceBoundaryEnforcer

        enforcer = ViceBoundaryEnforcer()

        # Chapter 1 should cap sexuality
        capped = enforcer.max_intensity_for_chapter("sexuality", chapter=1)
        assert capped <= Decimal("0.40")  # Subtle only

        # Chapter 5 allows more
        capped_ch5 = enforcer.max_intensity_for_chapter("sexuality", chapter=5)
        assert capped_ch5 > capped

    def test_ac_fr010_002_substances_never_encourages(self):
        """AC-FR010-002: Substances vice never encourages use."""
        from nikita.engine.vice.boundaries import ViceBoundaryEnforcer, CATEGORY_LIMITS

        enforcer = ViceBoundaryEnforcer()

        # Check limits exist
        assert "substances" in CATEGORY_LIMITS
        limits = CATEGORY_LIMITS["substances"]

        # Should have forbidden patterns
        assert "forbidden" in limits
        assert len(limits["forbidden"]) > 0

    def test_ac_fr010_003_extreme_intensity_respects_policy(self):
        """AC-FR010-003: Extreme intensities stay within content policy."""
        from nikita.engine.vice.boundaries import ViceBoundaryEnforcer

        enforcer = ViceBoundaryEnforcer()

        # Even at 1.0 intensity, sensitive categories should be bounded
        for category in ["sexuality", "substances", "rule_breaking"]:
            max_allowed = enforcer.max_intensity_for_chapter(category, chapter=5)
            assert max_allowed <= Decimal("0.90"), f"{category} should be capped even in Ch5"

    def test_ac_t036_1_category_limits_defined(self):
        """AC-T036.1: CATEGORY_LIMITS defines allowed/forbidden for sensitive categories."""
        from nikita.engine.vice.boundaries import CATEGORY_LIMITS

        sensitive = ["sexuality", "substances", "rule_breaking"]
        for cat in sensitive:
            assert cat in CATEGORY_LIMITS, f"Missing limits for {cat}"
            assert "allowed" in CATEGORY_LIMITS[cat] or "forbidden" in CATEGORY_LIMITS[cat]

    def test_ac_t036_3_max_intensity_for_chapter(self):
        """AC-T036.3: max_intensity_for_chapter caps sensitive vices."""
        from nikita.engine.vice.boundaries import ViceBoundaryEnforcer

        enforcer = ViceBoundaryEnforcer()

        # Non-sensitive category should be uncapped
        dark_humor_cap = enforcer.max_intensity_for_chapter("dark_humor", chapter=5)
        assert dark_humor_cap == Decimal("1.0")

        # Sensitive category should be capped
        sexuality_cap = enforcer.max_intensity_for_chapter("sexuality", chapter=1)
        assert sexuality_cap < Decimal("1.0")


class TestBoundaryIntegration:
    """T037: Boundary integration with injector tests."""

    def test_ac_t037_1_injector_uses_limits(self):
        """AC-T037.1: Injector uses boundary limits for sensitive categories."""
        from nikita.engine.vice.injector import VicePromptInjector
        from nikita.engine.vice.models import ViceProfile
        from datetime import datetime, timezone
        from uuid import uuid4

        injector = VicePromptInjector()

        # High sexuality in chapter 1
        profile = ViceProfile(
            user_id=uuid4(),
            intensities={"sexuality": Decimal("0.95")},  # Very high
            top_vices=["sexuality"],
            updated_at=datetime.now(timezone.utc),
        )

        result = injector.inject("Base prompt", profile, chapter=1)

        # Should still inject but with subtle expression
        assert "subtle" in result.lower() or "hint" in result.lower()

    def test_ac_t037_2_early_chapters_capped(self):
        """AC-T037.2: Early chapters get capped intensity for sensitive vices."""
        from nikita.engine.vice.boundaries import ViceBoundaryEnforcer

        enforcer = ViceBoundaryEnforcer()

        # Chapter 1 and 2 should have lower caps
        ch1_cap = enforcer.max_intensity_for_chapter("sexuality", 1)
        ch2_cap = enforcer.max_intensity_for_chapter("sexuality", 2)
        ch5_cap = enforcer.max_intensity_for_chapter("sexuality", 5)

        assert ch1_cap <= ch2_cap <= ch5_cap
