"""Tests for Spec 058 warmth bonus integration in ScoringService."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from nikita.config.enums import EngagementState
from nikita.engine.scoring.models import (
    ConversationContext,
    MetricDeltas,
    ResponseAnalysis,
)
from nikita.engine.scoring.service import ScoringService


@pytest.fixture
def service():
    return ScoringService()


@pytest.fixture
def context():
    return ConversationContext(
        chapter=3,
        relationship_score=Decimal("50"),
    )


@pytest.fixture
def metrics():
    return {
        "intimacy": Decimal("50"),
        "passion": Decimal("50"),
        "trust": Decimal("50"),
        "secureness": Decimal("50"),
    }


@pytest.fixture
def vuln_analysis():
    return ResponseAnalysis(
        deltas=MetricDeltas(
            intimacy=Decimal("2"), passion=Decimal("1"),
            trust=Decimal("3"), secureness=Decimal("1"),
        ),
        explanation="Vulnerability exchange detected",
        behaviors_identified=["vulnerability_exchange"],
        confidence=Decimal("0.9"),
    )


@pytest.fixture
def normal_analysis():
    return ResponseAnalysis(
        deltas=MetricDeltas(
            intimacy=Decimal("2"), passion=Decimal("1"),
            trust=Decimal("3"), secureness=Decimal("1"),
        ),
        explanation="Normal exchange",
        behaviors_identified=["engaged"],
        confidence=Decimal("0.9"),
    )


class TestServiceWarmthBonus:
    """AC-7.5: Warmth bonus integration in ScoringService."""

    @pytest.mark.asyncio
    async def test_warmth_bonus_applied_when_flag_on(
        self, service, context, metrics, vuln_analysis,
    ):
        """V-exchange detected + flag ON = trust bonus applied."""
        with (
            patch.object(service.analyzer, "analyze", return_value=vuln_analysis),
            patch.object(service, "_is_multi_phase_boss_enabled", return_value=True),
            patch.object(service, "_update_temperature_and_gottman", return_value=None),
        ):
            result = await service.score_interaction(
                user_id=uuid4(),
                user_message="I understand...",
                nikita_response="That means a lot",
                context=context,
                current_metrics=metrics,
                engagement_state=EngagementState.IN_ZONE,
                v_exchange_count=0,
            )
            # Trust delta should include +2 warmth bonus (3 base + 2 bonus = 5)
            assert result.deltas_applied.trust == Decimal("5")

    @pytest.mark.asyncio
    async def test_no_bonus_when_flag_off(
        self, service, context, metrics, vuln_analysis,
    ):
        """V-exchange detected + flag OFF = no trust bonus."""
        with (
            patch.object(service.analyzer, "analyze", return_value=vuln_analysis),
            patch.object(service, "_is_multi_phase_boss_enabled", return_value=False),
            patch.object(service, "_update_temperature_and_gottman", return_value=None),
        ):
            result = await service.score_interaction(
                user_id=uuid4(),
                user_message="I understand...",
                nikita_response="That means a lot",
                context=context,
                current_metrics=metrics,
                engagement_state=EngagementState.IN_ZONE,
                v_exchange_count=0,
            )
            # Trust delta should be base only (3, no bonus)
            assert result.deltas_applied.trust == Decimal("3")

    @pytest.mark.asyncio
    async def test_no_bonus_without_exchange(
        self, service, context, metrics, normal_analysis,
    ):
        """No vulnerability_exchange tag = no bonus even with flag ON."""
        with (
            patch.object(service.analyzer, "analyze", return_value=normal_analysis),
            patch.object(service, "_is_multi_phase_boss_enabled", return_value=True),
            patch.object(service, "_update_temperature_and_gottman", return_value=None),
        ):
            result = await service.score_interaction(
                user_id=uuid4(),
                user_message="Hello",
                nikita_response="Hey!",
                context=context,
                current_metrics=metrics,
                engagement_state=EngagementState.IN_ZONE,
                v_exchange_count=0,
            )
            assert result.deltas_applied.trust == Decimal("3")

    @pytest.mark.asyncio
    async def test_second_exchange_reduced_bonus(
        self, service, context, metrics, vuln_analysis,
    ):
        """Second V-exchange gets +1 bonus instead of +2."""
        with (
            patch.object(service.analyzer, "analyze", return_value=vuln_analysis),
            patch.object(service, "_is_multi_phase_boss_enabled", return_value=True),
            patch.object(service, "_update_temperature_and_gottman", return_value=None),
        ):
            result = await service.score_interaction(
                user_id=uuid4(),
                user_message="I feel that too",
                nikita_response="Thank you",
                context=context,
                current_metrics=metrics,
                engagement_state=EngagementState.IN_ZONE,
                v_exchange_count=1,  # Second exchange
            )
            # Trust = 3 base + 1 bonus = 4
            assert result.deltas_applied.trust == Decimal("4")
