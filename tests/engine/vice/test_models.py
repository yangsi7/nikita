"""
Unit Tests for Vice Models (T005-T007)

Tests for:
- ViceSignal model (T005)
- ViceAnalysisResult model (T006)
- ViceProfile model (T007)

TDD: Write tests FIRST, verify they fail, then implement.
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4


class TestViceSignal:
    """T005: ViceSignal model tests."""

    def test_ac_t005_1_category_from_vice_categories(self):
        """AC-T005.1: category field from VICE_CATEGORIES enum."""
        from nikita.engine.vice.models import ViceSignal
        from nikita.config.enums import ViceCategory

        signal = ViceSignal(
            category=ViceCategory.DARK_HUMOR,
            confidence=Decimal("0.85"),
            evidence="User made self-deprecating joke",
            is_positive=True,
        )
        assert signal.category == ViceCategory.DARK_HUMOR
        assert signal.category.value == "dark_humor"

    def test_ac_t005_2_confidence_decimal_range(self):
        """AC-T005.2: confidence field (Decimal 0.0-1.0)."""
        from nikita.engine.vice.models import ViceSignal
        from nikita.config.enums import ViceCategory

        # Valid range
        signal = ViceSignal(
            category=ViceCategory.RISK_TAKING,
            confidence=Decimal("0.50"),
            evidence="Mentioned skydiving",
            is_positive=True,
        )
        assert signal.confidence == Decimal("0.50")

        # Test boundary values
        signal_low = ViceSignal(
            category=ViceCategory.RISK_TAKING,
            confidence=Decimal("0.00"),
            evidence="No signal",
            is_positive=False,
        )
        assert signal_low.confidence == Decimal("0.00")

        signal_high = ViceSignal(
            category=ViceCategory.RISK_TAKING,
            confidence=Decimal("1.00"),
            evidence="Strong signal",
            is_positive=True,
        )
        assert signal_high.confidence == Decimal("1.00")

    def test_ac_t005_2_confidence_validation_fails_out_of_range(self):
        """AC-T005.2: confidence must be 0.0-1.0."""
        from nikita.engine.vice.models import ViceSignal
        from nikita.config.enums import ViceCategory
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ViceSignal(
                category=ViceCategory.DARK_HUMOR,
                confidence=Decimal("1.50"),  # Invalid
                evidence="Test",
                is_positive=True,
            )

        with pytest.raises(ValidationError):
            ViceSignal(
                category=ViceCategory.DARK_HUMOR,
                confidence=Decimal("-0.10"),  # Invalid
                evidence="Test",
                is_positive=True,
            )

    def test_ac_t005_3_evidence_field_reasoning(self):
        """AC-T005.3: evidence field for detection reasoning."""
        from nikita.engine.vice.models import ViceSignal
        from nikita.config.enums import ViceCategory

        evidence_text = "User asked about illegal substances in a non-judgmental way"
        signal = ViceSignal(
            category=ViceCategory.SUBSTANCES,
            confidence=Decimal("0.65"),
            evidence=evidence_text,
            is_positive=True,
        )
        assert signal.evidence == evidence_text
        assert len(signal.evidence) > 0

    def test_ac_t005_4_is_positive_field(self):
        """AC-T005.4: is_positive field (True=engagement, False=rejection)."""
        from nikita.engine.vice.models import ViceSignal
        from nikita.config.enums import ViceCategory

        # Positive engagement signal
        positive = ViceSignal(
            category=ViceCategory.VULNERABILITY,
            confidence=Decimal("0.75"),
            evidence="User shared personal fear",
            is_positive=True,
        )
        assert positive.is_positive is True

        # Rejection signal
        negative = ViceSignal(
            category=ViceCategory.DARK_HUMOR,
            confidence=Decimal("0.80"),
            evidence="User said 'that's not funny'",
            is_positive=False,
        )
        assert negative.is_positive is False


class TestViceAnalysisResult:
    """T006: ViceAnalysisResult model tests."""

    def test_ac_t006_1_signals_list(self):
        """AC-T006.1: signals list of ViceSignal."""
        from nikita.engine.vice.models import ViceSignal, ViceAnalysisResult
        from nikita.config.enums import ViceCategory

        signals = [
            ViceSignal(
                category=ViceCategory.DARK_HUMOR,
                confidence=Decimal("0.85"),
                evidence="Made morbid joke",
                is_positive=True,
            ),
            ViceSignal(
                category=ViceCategory.INTELLECTUAL_DOMINANCE,
                confidence=Decimal("0.60"),
                evidence="Corrected a statement",
                is_positive=True,
            ),
        ]

        result = ViceAnalysisResult(
            signals=signals,
            conversation_id=uuid4(),
            analyzed_at=datetime.now(timezone.utc),
        )
        assert len(result.signals) == 2
        assert result.signals[0].category == ViceCategory.DARK_HUMOR

    def test_ac_t006_1_empty_signals_list(self):
        """AC-T006.1: signals list can be empty."""
        from nikita.engine.vice.models import ViceAnalysisResult

        result = ViceAnalysisResult(
            signals=[],
            conversation_id=uuid4(),
            analyzed_at=datetime.now(timezone.utc),
        )
        assert result.signals == []

    def test_ac_t006_2_conversation_id_traceability(self):
        """AC-T006.2: conversation_id for traceability."""
        from nikita.engine.vice.models import ViceAnalysisResult

        conv_id = uuid4()
        result = ViceAnalysisResult(
            signals=[],
            conversation_id=conv_id,
            analyzed_at=datetime.now(timezone.utc),
        )
        assert result.conversation_id == conv_id

    def test_ac_t006_3_analyzed_at_timestamp(self):
        """AC-T006.3: analyzed_at timestamp."""
        from nikita.engine.vice.models import ViceAnalysisResult

        now = datetime.now(timezone.utc)
        result = ViceAnalysisResult(
            signals=[],
            conversation_id=uuid4(),
            analyzed_at=now,
        )
        assert result.analyzed_at == now


class TestViceProfile:
    """T007: ViceProfile model tests."""

    def test_ac_t007_1_user_id_field(self):
        """AC-T007.1: user_id UUID field."""
        from nikita.engine.vice.models import ViceProfile

        user_id = uuid4()
        profile = ViceProfile(
            user_id=user_id,
            intensities={},
            top_vices=[],
            updated_at=datetime.now(timezone.utc),
        )
        assert profile.user_id == user_id

    def test_ac_t007_2_intensities_dict_all_categories(self):
        """AC-T007.2: intensities dict[str, Decimal] for all 8 categories."""
        from nikita.engine.vice.models import ViceProfile
        from nikita.config.enums import ViceCategory

        intensities = {
            ViceCategory.INTELLECTUAL_DOMINANCE.value: Decimal("0.75"),
            ViceCategory.RISK_TAKING.value: Decimal("0.30"),
            ViceCategory.SUBSTANCES.value: Decimal("0.10"),
            ViceCategory.SEXUALITY.value: Decimal("0.45"),
            ViceCategory.EMOTIONAL_INTENSITY.value: Decimal("0.60"),
            ViceCategory.RULE_BREAKING.value: Decimal("0.20"),
            ViceCategory.DARK_HUMOR.value: Decimal("0.85"),
            ViceCategory.VULNERABILITY.value: Decimal("0.55"),
        }

        profile = ViceProfile(
            user_id=uuid4(),
            intensities=intensities,
            top_vices=["dark_humor", "intellectual_dominance"],
            updated_at=datetime.now(timezone.utc),
        )
        assert len(profile.intensities) == 8
        assert profile.intensities["dark_humor"] == Decimal("0.85")

    def test_ac_t007_3_top_vices_ordered_list(self):
        """AC-T007.3: top_vices ordered list."""
        from nikita.engine.vice.models import ViceProfile

        profile = ViceProfile(
            user_id=uuid4(),
            intensities={
                "dark_humor": Decimal("0.85"),
                "intellectual_dominance": Decimal("0.75"),
                "vulnerability": Decimal("0.55"),
            },
            top_vices=["dark_humor", "intellectual_dominance", "vulnerability"],
            updated_at=datetime.now(timezone.utc),
        )
        assert profile.top_vices == ["dark_humor", "intellectual_dominance", "vulnerability"]
        assert profile.top_vices[0] == "dark_humor"  # Highest first

    def test_ac_t007_4_updated_at_timestamp(self):
        """AC-T007.4: updated_at timestamp."""
        from nikita.engine.vice.models import ViceProfile

        now = datetime.now(timezone.utc)
        profile = ViceProfile(
            user_id=uuid4(),
            intensities={},
            top_vices=[],
            updated_at=now,
        )
        assert profile.updated_at == now


class TestViceProfileMethods:
    """Additional ViceProfile helper method tests."""

    def test_get_intensity_returns_value(self):
        """get_intensity returns correct value for existing category."""
        from nikita.engine.vice.models import ViceProfile

        profile = ViceProfile(
            user_id=uuid4(),
            intensities={"dark_humor": Decimal("0.85")},
            top_vices=["dark_humor"],
            updated_at=datetime.now(timezone.utc),
        )
        assert profile.get_intensity("dark_humor") == Decimal("0.85")

    def test_get_intensity_returns_zero_for_missing(self):
        """get_intensity returns 0.0 for missing category."""
        from nikita.engine.vice.models import ViceProfile

        profile = ViceProfile(
            user_id=uuid4(),
            intensities={},
            top_vices=[],
            updated_at=datetime.now(timezone.utc),
        )
        assert profile.get_intensity("dark_humor") == Decimal("0.0")

    def test_has_active_vices_true(self):
        """has_active_vices returns True when vices above threshold."""
        from nikita.engine.vice.models import ViceProfile

        profile = ViceProfile(
            user_id=uuid4(),
            intensities={"dark_humor": Decimal("0.50")},
            top_vices=["dark_humor"],
            updated_at=datetime.now(timezone.utc),
        )
        assert profile.has_active_vices(threshold=Decimal("0.30")) is True

    def test_has_active_vices_false(self):
        """has_active_vices returns False when no vices above threshold."""
        from nikita.engine.vice.models import ViceProfile

        profile = ViceProfile(
            user_id=uuid4(),
            intensities={"dark_humor": Decimal("0.20")},
            top_vices=[],
            updated_at=datetime.now(timezone.utc),
        )
        assert profile.has_active_vices(threshold=Decimal("0.30")) is False
