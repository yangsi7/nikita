"""Tests for NarrativeArcManager (Spec 022, T011).

AC-T011.1: NarrativeArcManager class
AC-T011.2: create_arc() starts new narrative arc
AC-T011.3: progress_arc() advances arc state
AC-T011.4: resolve_arc() ends arc
AC-T011.5: Probabilistic resolution (70/20/10)
AC-T011.6: Unit tests for arc lifecycle
"""

from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.life_simulation.models import (
    ArcStatus,
    EventDomain,
    NarrativeArc,
)
from nikita.life_simulation.narrative_manager import (
    ARC_TYPES,
    NarrativeArcManager,
    get_narrative_manager,
)


class TestNarrativeArcManager:
    """Tests for NarrativeArcManager class (AC-T011.1)."""

    @pytest.fixture
    def mock_store(self):
        """Create mock EventStore."""
        store = MagicMock()
        store.save_arc = AsyncMock()
        store.update_arc_state = AsyncMock(return_value=True)
        store.update_arc_status = AsyncMock(return_value=True)
        store.get_active_arcs = AsyncMock(return_value=[])
        return store

    @pytest.fixture
    def manager(self, mock_store):
        """Create manager with mock store."""
        return NarrativeArcManager(store=mock_store)

    @pytest.fixture
    def user_id(self):
        """Test user ID."""
        return uuid4()

    # ==================== CREATE ARC TESTS (AC-T011.2) ====================

    @pytest.mark.asyncio
    async def test_create_arc_returns_arc(self, manager, user_id):
        """Create arc returns NarrativeArc object."""
        arc = await manager.create_arc(user_id, "project_deadline")

        assert isinstance(arc, NarrativeArc)
        assert arc.user_id == user_id

    @pytest.mark.asyncio
    async def test_create_arc_sets_type(self, manager, user_id):
        """Create arc sets correct arc type."""
        arc = await manager.create_arc(user_id, "project_deadline")

        assert arc.arc_type == "project_deadline"

    @pytest.mark.asyncio
    async def test_create_arc_sets_domain(self, manager, user_id):
        """Create arc sets domain from arc type config."""
        arc = await manager.create_arc(user_id, "project_deadline")

        assert arc.domain == EventDomain.WORK

    @pytest.mark.asyncio
    async def test_create_arc_sets_entities(self, manager, user_id):
        """Create arc sets provided entities."""
        entities = ["Lisa", "the redesign"]
        arc = await manager.create_arc(user_id, "project_deadline", entities=entities)

        assert arc.entities == entities

    @pytest.mark.asyncio
    async def test_create_arc_generates_initial_state(self, manager, user_id):
        """Create arc generates initial state if not provided."""
        arc = await manager.create_arc(user_id, "project_deadline")

        assert arc.current_state is not None
        assert len(arc.current_state) > 0

    @pytest.mark.asyncio
    async def test_create_arc_uses_provided_state(self, manager, user_id):
        """Create arc uses provided initial state."""
        arc = await manager.create_arc(
            user_id, "project_deadline", initial_state="Custom state"
        )

        assert arc.current_state == "Custom state"

    @pytest.mark.asyncio
    async def test_create_arc_sets_possible_outcomes(self, manager, user_id):
        """Create arc sets possible outcomes from config."""
        arc = await manager.create_arc(user_id, "project_deadline")

        assert len(arc.possible_outcomes) >= 1
        assert "completed_successfully" in arc.possible_outcomes

    @pytest.mark.asyncio
    async def test_create_arc_sets_active_status(self, manager, user_id):
        """Create arc starts with ACTIVE status."""
        arc = await manager.create_arc(user_id, "project_deadline")

        assert arc.status == ArcStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_create_arc_saves_to_store(self, manager, mock_store, user_id):
        """Create arc saves to store."""
        await manager.create_arc(user_id, "project_deadline")

        mock_store.save_arc.assert_called_once()

    # ==================== PROGRESS ARC TESTS (AC-T011.3) ====================

    @pytest.mark.asyncio
    async def test_progress_arc_updates_state(self, manager, mock_store):
        """Progress arc updates state in store."""
        arc_id = uuid4()
        new_state = "Deadline extended by two weeks"

        success = await manager.progress_arc(arc_id, new_state)

        assert success is True
        mock_store.update_arc_state.assert_called_once_with(arc_id, new_state)

    @pytest.mark.asyncio
    async def test_progress_arc_returns_false_on_failure(self, manager, mock_store):
        """Progress arc returns False if store update fails."""
        mock_store.update_arc_state.return_value = False
        arc_id = uuid4()

        success = await manager.progress_arc(arc_id, "New state")

        assert success is False

    # ==================== RESOLVE ARC TESTS (AC-T011.4) ====================

    @pytest.mark.asyncio
    async def test_resolve_arc_updates_status(self, manager, mock_store):
        """Resolve arc updates status to RESOLVED."""
        arc_id = uuid4()

        success = await manager.resolve_arc(arc_id, "completed_successfully")

        assert success is True
        mock_store.update_arc_status.assert_called_once()
        call_args = mock_store.update_arc_status.call_args
        assert call_args[0][0] == arc_id
        assert call_args[0][1] == ArcStatus.RESOLVED

    @pytest.mark.asyncio
    async def test_resolve_arc_sets_resolved_at(self, manager, mock_store):
        """Resolve arc sets resolved_at timestamp."""
        arc_id = uuid4()

        await manager.resolve_arc(arc_id, "completed_successfully")

        call_args = mock_store.update_arc_status.call_args
        assert call_args[1]["resolved_at"] is not None
        assert isinstance(call_args[1]["resolved_at"], datetime)

    @pytest.mark.asyncio
    async def test_resolve_arc_updates_final_state(self, manager, mock_store):
        """Resolve arc updates final state if provided."""
        arc_id = uuid4()

        await manager.resolve_arc(
            arc_id, "completed_successfully", final_state="Project delivered!"
        )

        mock_store.update_arc_state.assert_called_once_with(arc_id, "Project delivered!")

    @pytest.mark.asyncio
    async def test_resolve_arc_without_final_state(self, manager, mock_store):
        """Resolve arc works without final state."""
        arc_id = uuid4()

        await manager.resolve_arc(arc_id, "completed_successfully")

        # Should not call update_arc_state
        mock_store.update_arc_state.assert_not_called()

    # ==================== PROBABILISTIC RESOLUTION (AC-T011.5) ====================

    @pytest.mark.asyncio
    async def test_check_resolution_returns_tuple(self, manager, user_id):
        """Check resolution returns (bool, outcome) tuple."""
        arc = NarrativeArc(
            user_id=user_id,
            domain=EventDomain.WORK,
            arc_type="project_deadline",
            start_date=date.today() - timedelta(days=30),  # Old arc
            entities=[],
            current_state="Test state",
        )

        result = await manager.check_arc_resolution(arc)

        assert isinstance(result, tuple)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_check_resolution_new_arc_unlikely(self, manager, user_id):
        """New arcs are unlikely to resolve immediately."""
        arc = NarrativeArc(
            user_id=user_id,
            domain=EventDomain.WORK,
            arc_type="project_deadline",
            start_date=date.today(),  # Brand new
            entities=[],
            current_state="Test state",
        )

        # Run multiple times to check probability
        resolved_count = 0
        for _ in range(100):
            should_resolve, _ = await manager.check_arc_resolution(arc, days_active=0)
            if should_resolve:
                resolved_count += 1

        # Should rarely resolve on day 0
        assert resolved_count < 20

    @pytest.mark.asyncio
    async def test_check_resolution_old_arc_likely(self, manager, user_id):
        """Old arcs are likely to resolve."""
        arc = NarrativeArc(
            user_id=user_id,
            domain=EventDomain.WORK,
            arc_type="project_deadline",
            start_date=date.today() - timedelta(days=30),
            entities=[],
            current_state="Test state",
        )

        # Run multiple times
        resolved_count = 0
        for _ in range(100):
            should_resolve, _ = await manager.check_arc_resolution(arc, days_active=30)
            if should_resolve:
                resolved_count += 1

        # Should often resolve after many days
        assert resolved_count > 50

    @pytest.mark.asyncio
    async def test_resolution_outcome_matches_config(self, manager, user_id):
        """Resolution outcomes come from arc type config."""
        arc = NarrativeArc(
            user_id=user_id,
            domain=EventDomain.WORK,
            arc_type="project_deadline",
            start_date=date.today() - timedelta(days=30),
            entities=[],
            current_state="Test state",
        )

        valid_outcomes = ARC_TYPES["project_deadline"]["outcomes"]

        for _ in range(50):
            should_resolve, outcome = await manager.check_arc_resolution(arc, days_active=30)
            if should_resolve:
                assert outcome in valid_outcomes

    # ==================== GET ACTIVE ARCS ====================

    @pytest.mark.asyncio
    async def test_get_active_arcs(self, manager, mock_store, user_id):
        """Get active arcs delegates to store."""
        mock_store.get_active_arcs.return_value = []

        result = await manager.get_active_arcs(user_id)

        assert result == []
        mock_store.get_active_arcs.assert_called_once_with(user_id)

    # ==================== MAYBE RESOLVE ARCS ====================

    @pytest.mark.asyncio
    async def test_maybe_resolve_arcs_checks_all(self, manager, mock_store, user_id):
        """Maybe resolve arcs checks all active arcs."""
        arcs = [
            NarrativeArc(
                user_id=user_id,
                domain=EventDomain.WORK,
                arc_type="project_deadline",
                start_date=date.today() - timedelta(days=30),
                entities=[],
                current_state="Test state",
            )
        ]
        mock_store.get_active_arcs.return_value = arcs

        await manager.maybe_resolve_arcs(user_id)

        mock_store.get_active_arcs.assert_called_once_with(user_id)

    # ==================== MAYBE CREATE ARC ====================

    @pytest.mark.asyncio
    async def test_maybe_create_arc_respects_limit(self, manager, mock_store, user_id):
        """Maybe create arc respects 3 active arcs limit."""
        # Already have 3 arcs
        mock_store.get_active_arcs.return_value = [
            MagicMock() for _ in range(3)
        ]

        result = await manager.maybe_create_arc(user_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_maybe_create_arc_filters_by_domain(self, manager, mock_store, user_id):
        """Maybe create arc can filter by domain."""
        mock_store.get_active_arcs.return_value = []

        with patch("random.random", return_value=0.1):  # Will try to create
            with patch("random.choice", return_value="project_deadline"):
                result = await manager.maybe_create_arc(user_id, domain=EventDomain.WORK)

        if result is not None:
            assert result.domain == EventDomain.WORK


class TestArcTypes:
    """Tests for arc type configuration."""

    def test_arc_types_not_empty(self):
        """Arc types are defined."""
        assert len(ARC_TYPES) > 0

    def test_arc_types_have_domain(self):
        """All arc types have a domain."""
        for arc_type, config in ARC_TYPES.items():
            assert "domain" in config, f"{arc_type} missing domain"

    def test_arc_types_have_outcomes(self):
        """All arc types have outcomes."""
        for arc_type, config in ARC_TYPES.items():
            assert "outcomes" in config, f"{arc_type} missing outcomes"
            assert len(config["outcomes"]) >= 2

    def test_arc_types_have_weights(self):
        """All arc types have outcome weights."""
        for arc_type, config in ARC_TYPES.items():
            assert "outcome_weights" in config, f"{arc_type} missing weights"
            assert len(config["outcome_weights"]) == len(config["outcomes"])

    def test_arc_type_weights_sum_to_one(self):
        """Outcome weights approximately sum to 1."""
        for arc_type, config in ARC_TYPES.items():
            weight_sum = sum(config["outcome_weights"])
            assert 0.9 <= weight_sum <= 1.1, f"{arc_type} weights don't sum to ~1"

    def test_work_arcs_exist(self):
        """Work domain arcs exist."""
        work_arcs = [
            t for t, c in ARC_TYPES.items() if c["domain"] == EventDomain.WORK
        ]
        assert len(work_arcs) >= 2

    def test_social_arcs_exist(self):
        """Social domain arcs exist."""
        social_arcs = [
            t for t, c in ARC_TYPES.items() if c["domain"] == EventDomain.SOCIAL
        ]
        assert len(social_arcs) >= 2

    def test_personal_arcs_exist(self):
        """Personal domain arcs exist."""
        personal_arcs = [
            t for t, c in ARC_TYPES.items() if c["domain"] == EventDomain.PERSONAL
        ]
        assert len(personal_arcs) >= 2


class TestGetNarrativeManager:
    """Tests for singleton factory."""

    def test_singleton_pattern(self):
        """get_narrative_manager returns same instance."""
        import nikita.life_simulation.narrative_manager as nm_module

        nm_module._default_manager = None

        manager1 = get_narrative_manager()
        manager2 = get_narrative_manager()

        assert manager1 is manager2
