"""
Unit Tests for ViceService (T030-T034, T040)

Tests for:
- AC-FR007-001: Given new user with empty profile, When Nikita responds, Then varied vice hints included
- AC-FR007-002: Given user positively responds to probe, When analyzed, Then vice intensity increases
- AC-T040: ViceService orchestration tests

TDD: Write tests FIRST, verify they fail, then implement.
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


class TestViceServiceDiscovery:
    """T030-T034: Vice discovery probing tests."""

    @pytest.mark.asyncio
    async def test_ac_fr007_001_new_user_varied_hints(self):
        """AC-FR007-001: New user gets varied vice hints for discovery."""
        from nikita.engine.vice.service import ViceService
        from nikita.engine.vice.models import ViceProfile

        service = ViceService()

        # Empty profile = new user
        profile = ViceProfile(
            user_id=uuid4(),
            intensities={},
            top_vices=[],
            updated_at=datetime.now(timezone.utc),
        )

        context = await service.get_prompt_context(profile, chapter=1)

        # Should be in discovery mode
        assert context.discovery_mode is True
        assert len(context.probe_categories) > 0

    @pytest.mark.asyncio
    async def test_ac_fr007_002_positive_response_increases_intensity(self):
        """AC-FR007-002: Positive probe response increases vice intensity."""
        from nikita.engine.vice.service import ViceService
        from nikita.engine.vice.models import ViceSignal
        from nikita.config.enums import ViceCategory

        service = ViceService()
        user_id = uuid4()

        # Simulate positive response to dark_humor probe
        signals = [
            ViceSignal(
                category=ViceCategory.DARK_HUMOR,
                confidence=Decimal("0.80"),
                evidence="User laughed at morbid joke",
                is_positive=True,
            ),
        ]

        with patch.object(service, '_scorer') as mock_scorer:
            mock_scorer.process_signals = AsyncMock(return_value={"updated": 1})

            result = await service.process_conversation_signals(user_id, signals)

            # Should have processed the signal
            mock_scorer.process_signals.assert_called_once()
            assert result["updated"] >= 1


class TestViceServiceOrchestration:
    """T040: ViceService.get_prompt_context() and process_conversation() tests."""

    @pytest.mark.asyncio
    async def test_ac_t040_1_get_prompt_context(self):
        """AC-T040.1: get_prompt_context(user_id, chapter) returns ViceInjectionContext."""
        from nikita.engine.vice.service import ViceService
        from nikita.engine.vice.models import ViceProfile, ViceInjectionContext

        service = ViceService()

        profile = ViceProfile(
            user_id=uuid4(),
            intensities={"dark_humor": Decimal("0.70")},
            top_vices=["dark_humor"],
            updated_at=datetime.now(timezone.utc),
        )

        context = await service.get_prompt_context(profile, chapter=3)

        assert isinstance(context, ViceInjectionContext)
        assert context.has_vices() or context.discovery_mode

    @pytest.mark.asyncio
    async def test_ac_t040_2_process_conversation(self):
        """AC-T040.2: process_conversation analyzes exchange."""
        from nikita.engine.vice.service import ViceService

        service = ViceService()
        user_id = uuid4()
        conv_id = uuid4()

        with patch.object(service, '_analyzer') as mock_analyzer:
            with patch.object(service, '_scorer') as mock_scorer:
                mock_result = MagicMock()
                mock_result.signals = []
                mock_analyzer.analyze_exchange = AsyncMock(return_value=mock_result)
                mock_scorer.process_signals = AsyncMock(return_value={})

                result = await service.process_conversation(
                    user_id=user_id,
                    user_message="Hello!",
                    nikita_message="Hi there!",
                    conversation_id=conv_id,
                )

                mock_analyzer.analyze_exchange.assert_called_once()

    @pytest.mark.asyncio
    async def test_ac_t040_3_orchestrates_components(self):
        """AC-T040.3: Orchestrates analyzer, scorer, injector, enforcer."""
        from nikita.engine.vice.service import ViceService

        service = ViceService()

        # Service should have all components
        assert hasattr(service, '_analyzer')
        assert hasattr(service, '_scorer')
        assert hasattr(service, '_injector')
        assert hasattr(service, '_enforcer')


class TestViceServiceProbing:
    """T031: Discovery probing logic tests."""

    def test_ac_t031_1_new_users_get_varied_hints(self):
        """AC-T031.1: New users get varied vice hints in prompts."""
        from nikita.engine.vice.service import ViceService
        from nikita.engine.vice.models import ViceProfile
        from datetime import datetime, timezone
        from uuid import uuid4

        service = ViceService()

        # Empty profile
        profile = ViceProfile(
            user_id=uuid4(),
            intensities={},
            top_vices=[],
            updated_at=datetime.now(timezone.utc),
        )

        # Should suggest probing categories
        probes = service.get_probe_categories(profile)
        assert len(probes) > 0
        assert len(probes) <= 8  # Max 8 categories

    def test_ac_t031_2_unexplored_categories_probed(self):
        """AC-T031.2: Unexplored categories get probed occasionally."""
        from nikita.engine.vice.service import ViceService
        from nikita.engine.vice.models import ViceProfile
        from datetime import datetime, timezone
        from uuid import uuid4

        service = ViceService()

        # Profile with some vices discovered
        profile = ViceProfile(
            user_id=uuid4(),
            intensities={
                "dark_humor": Decimal("0.70"),
                "risk_taking": Decimal("0.50"),
            },
            top_vices=["dark_humor", "risk_taking"],
            updated_at=datetime.now(timezone.utc),
        )

        probes = service.get_probe_categories(profile)

        # Should not include already discovered vices
        assert "dark_humor" not in probes
        assert "risk_taking" not in probes

    def test_ac_t031_3_probe_frequency_decreases(self):
        """AC-T031.3: Probe frequency decreases as profile stabilizes."""
        from nikita.engine.vice.service import ViceService
        from nikita.engine.vice.models import ViceProfile
        from datetime import datetime, timezone
        from uuid import uuid4

        service = ViceService()

        # Well-established profile (many vices discovered)
        profile = ViceProfile(
            user_id=uuid4(),
            intensities={
                "dark_humor": Decimal("0.80"),
                "risk_taking": Decimal("0.70"),
                "vulnerability": Decimal("0.60"),
                "intellectual_dominance": Decimal("0.50"),
                "emotional_intensity": Decimal("0.40"),
            },
            top_vices=["dark_humor", "risk_taking", "vulnerability"],
            updated_at=datetime.now(timezone.utc),
        )

        probes = service.get_probe_categories(profile)

        # Should have fewer probes for established profiles
        assert len(probes) <= 3  # Only a few unexplored
