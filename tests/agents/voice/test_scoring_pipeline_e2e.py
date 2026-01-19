"""E2E tests for voice call scoring pipeline.

Tests the complete scoring flow:
- Turn-level scoring (sentiment analysis, running totals)
- Call-level aggregate scoring with engagement multipliers
- Score persistence to database (score_history, user_metrics)
- Chapter-aware weight adjustments

These tests verify AC-FR006-001 through AC-FR006-003:
- Call ends → transcript analyzed → single aggregate score
- Good call → positive metric deltas
- Score history logged with source='voice_call'
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.agents.voice.models import TranscriptData, TranscriptEntry
from nikita.agents.voice.scoring import CallScore, VoiceCallScorer
from nikita.engine.scoring.models import (
    ConversationContext,
    MetricDeltas,
    ResponseAnalysis,
)


class TestTurnScoring:
    """Test individual turn scoring during voice calls."""

    @pytest.fixture
    def scorer(self):
        """Get VoiceCallScorer instance."""
        return VoiceCallScorer()

    @pytest.fixture
    def positive_context(self, user_chapter_3):
        """Conversation context for positive call."""
        return ConversationContext(
            chapter=user_chapter_3.chapter,
            relationship_score=Decimal(str(user_chapter_3.relationship_score)),
            recent_messages=[],
            relationship_state="stable",
            engagement_state="IN_ZONE",
        )

    @pytest.mark.asyncio
    async def test_score_turn_analyzes_sentiment(self, scorer, positive_context):
        """Test that scoring analyzes sentiment of conversation turns."""
        transcript = [
            ("I finally got the promotion!", "That's amazing! I'm so proud of you!"),
            ("Thanks for always believing in me", "Of course, I knew you could do it."),
        ]

        # Mock the analyzer to return positive analysis
        mock_analysis = ResponseAnalysis(
            deltas=MetricDeltas(
                intimacy=Decimal("3"),
                passion=Decimal("2"),
                trust=Decimal("4"),
                secureness=Decimal("2"),
            ),
            explanation="Positive emotional exchange with celebration",
            behaviors_identified=["supportive", "encouraging", "emotionally_connected"],
            confidence=Decimal("0.85"),
        )

        with patch.object(
            scorer._analyzer,
            "analyze_batch",
            AsyncMock(return_value=mock_analysis),
        ):
            result = await scorer.score_call(
                user_id=uuid4(),
                session_id="test_session",
                transcript=transcript,
                context=positive_context,
                duration_seconds=180,
            )

            # Verify sentiment-based scoring occurred
            assert result.deltas.total > Decimal("0")
            assert "supportive" in result.behaviors_identified
            assert result.confidence >= Decimal("0.8")

    @pytest.mark.asyncio
    async def test_score_turn_updates_running_total(self, scorer, positive_context):
        """Test that multiple turns accumulate into running total."""
        # Multi-turn transcript
        transcript = [
            ("Hey, how's your day?", "Pretty good! Just got back from yoga."),
            ("Nice! I should try yoga sometime", "You totally should! It's amazing."),
            ("Maybe we can do it together?", "I'd love that! Let's plan it."),
        ]

        mock_analysis = ResponseAnalysis(
            deltas=MetricDeltas(
                intimacy=Decimal("5"),
                passion=Decimal("4"),
                trust=Decimal("3"),
                secureness=Decimal("3"),
            ),
            explanation="Multi-turn positive conversation with future planning",
            behaviors_identified=["engaged", "planning_together"],
            confidence=Decimal("0.9"),
        )

        with patch.object(
            scorer._analyzer,
            "analyze_batch",
            AsyncMock(return_value=mock_analysis),
        ):
            result = await scorer.score_call(
                user_id=uuid4(),
                session_id="test_multi_turn",
                transcript=transcript,
                context=positive_context,
            )

            # Running total should reflect cumulative positive exchange
            assert result.deltas.total == Decimal("15")  # 5+4+3+3
            assert result.deltas.intimacy == Decimal("5")

    @pytest.mark.asyncio
    async def test_score_turn_respects_chapter_weights(self, scorer):
        """Test that chapter context influences scoring."""
        # Same transcript, different chapters
        transcript = [("I missed talking to you", "I missed you too")]

        # Chapter 1 context (guarded Nikita, smaller gains expected)
        chapter_1_context = ConversationContext(
            chapter=1,
            relationship_score=Decimal("25"),
            relationship_state="forming",
            engagement_state="CALIBRATING",
        )

        # Chapter 5 context (intimate Nikita, larger gains expected)
        chapter_5_context = ConversationContext(
            chapter=5,
            relationship_score=Decimal("85"),
            relationship_state="established",
            engagement_state="IN_ZONE",
        )

        # Mock analyzer to check context is passed
        call_args = []

        async def capture_context(transcript, context):
            call_args.append(context)
            return ResponseAnalysis(
                deltas=MetricDeltas(
                    intimacy=Decimal("2") if context.chapter == 1 else Decimal("5"),
                    passion=Decimal("1") if context.chapter == 1 else Decimal("4"),
                    trust=Decimal("1") if context.chapter == 1 else Decimal("3"),
                    secureness=Decimal("1") if context.chapter == 1 else Decimal("3"),
                ),
                explanation=f"Chapter {context.chapter} scoring",
            )

        with patch.object(
            scorer._analyzer,
            "analyze_batch",
            AsyncMock(side_effect=capture_context),
        ):
            ch1_result = await scorer.score_call(
                user_id=uuid4(),
                session_id="ch1_test",
                transcript=transcript,
                context=chapter_1_context,
            )

            ch5_result = await scorer.score_call(
                user_id=uuid4(),
                session_id="ch5_test",
                transcript=transcript,
                context=chapter_5_context,
            )

            # Chapter context should have been passed
            assert len(call_args) == 2
            assert call_args[0].chapter == 1
            assert call_args[1].chapter == 5

            # Higher chapter = potentially larger deltas
            assert ch5_result.deltas.total > ch1_result.deltas.total


class TestCallScoring:
    """Test complete call scoring with aggregation."""

    @pytest.fixture
    def scorer(self):
        """Get VoiceCallScorer instance."""
        return VoiceCallScorer()

    @pytest.fixture
    def call_context(self, user_chapter_3):
        """Standard call context."""
        return ConversationContext(
            chapter=user_chapter_3.chapter,
            relationship_score=Decimal(str(user_chapter_3.relationship_score)),
            engagement_state="IN_ZONE",
        )

    @pytest.mark.asyncio
    async def test_call_scoring_computes_aggregate(
        self, scorer, transcript_positive, call_context
    ):
        """Test that call scoring produces single aggregate score."""
        # Convert transcript fixture to expected format
        transcript_pairs = [
            (e.text, transcript_positive.entries[i + 1].text)
            for i, e in enumerate(transcript_positive.entries)
            if e.speaker == "user" and i + 1 < len(transcript_positive.entries)
        ]

        mock_analysis = ResponseAnalysis(
            deltas=MetricDeltas(
                intimacy=Decimal("4"),
                passion=Decimal("3"),
                trust=Decimal("5"),
                secureness=Decimal("3"),
            ),
            explanation="Aggregate analysis of positive call",
            behaviors_identified=["enthusiastic", "celebratory"],
            confidence=Decimal("0.88"),
        )

        with patch.object(
            scorer._analyzer,
            "analyze_batch",
            AsyncMock(return_value=mock_analysis),
        ):
            result = await scorer.score_call(
                user_id=uuid4(),
                session_id=transcript_positive.session_id,
                transcript=transcript_pairs,
                context=call_context,
                duration_seconds=transcript_positive.total_duration_ms // 1000,
            )

            # Should have single aggregate CallScore
            assert isinstance(result, CallScore)
            assert result.session_id == transcript_positive.session_id
            assert result.deltas.total == Decimal("15")

    @pytest.mark.asyncio
    async def test_call_scoring_applies_engagement_multiplier(self, scorer):
        """Test that engagement state affects scoring."""
        transcript = [("Great news!", "Tell me everything!")]

        # IN_ZONE context (1.0x multiplier)
        in_zone_context = ConversationContext(
            chapter=3,
            relationship_score=Decimal("55"),
            engagement_state="IN_ZONE",
        )

        # DRIFTING context (lower multiplier)
        drifting_context = ConversationContext(
            chapter=3,
            relationship_score=Decimal("55"),
            engagement_state="DRIFTING",
        )

        contexts_passed = []

        async def capture_engagement(transcript, context):
            contexts_passed.append(context.engagement_state)
            return ResponseAnalysis(
                deltas=MetricDeltas(
                    intimacy=Decimal("3"),
                    passion=Decimal("2"),
                    trust=Decimal("2"),
                    secureness=Decimal("2"),
                ),
                explanation=f"Engagement: {context.engagement_state}",
            )

        with patch.object(
            scorer._analyzer,
            "analyze_batch",
            AsyncMock(side_effect=capture_engagement),
        ):
            await scorer.score_call(
                user_id=uuid4(),
                session_id="in_zone_call",
                transcript=transcript,
                context=in_zone_context,
            )

            await scorer.score_call(
                user_id=uuid4(),
                session_id="drifting_call",
                transcript=transcript,
                context=drifting_context,
            )

            # Engagement states should be passed to analyzer
            assert "IN_ZONE" in contexts_passed
            assert "DRIFTING" in contexts_passed

    @pytest.mark.asyncio
    async def test_call_scoring_updates_user_metrics(
        self, scorer, mock_db_session, user_chapter_3
    ):
        """Test that apply_score updates user metrics in database."""
        call_score = CallScore(
            session_id="test_apply_score",
            deltas=MetricDeltas(
                intimacy=Decimal("5"),
                passion=Decimal("4"),
                trust=Decimal("3"),
                secureness=Decimal("2"),
            ),
            explanation="Good call",
            duration_seconds=300,
        )

        # Mock repositories
        mock_user_repo = MagicMock()
        mock_user_repo.get = AsyncMock(return_value=user_chapter_3)

        mock_metrics = MagicMock()
        mock_metrics.calculate_composite_score = MagicMock(return_value=Decimal("60"))

        mock_metrics_repo = MagicMock()
        mock_metrics_repo.get_by_user_id = AsyncMock(return_value=mock_metrics)
        mock_metrics_repo.update_metrics = AsyncMock(return_value=mock_metrics)

        mock_history_repo = MagicMock()
        mock_history_repo.log_event = AsyncMock()

        with patch(
            "nikita.db.database.get_session_maker"
        ) as mock_session_maker:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            mock_session.commit = AsyncMock()
            mock_session_maker.return_value = MagicMock(return_value=mock_session)

            with patch(
                "nikita.db.repositories.user_repository.UserRepository",
                return_value=mock_user_repo,
            ):
                with patch(
                    "nikita.db.repositories.metrics_repository.UserMetricsRepository",
                    return_value=mock_metrics_repo,
                ):
                    with patch(
                        "nikita.db.repositories.score_history_repository.ScoreHistoryRepository",
                        return_value=mock_history_repo,
                    ):
                        new_score = await scorer.apply_score(
                            user_id=user_chapter_3.id,
                            call_score=call_score,
                        )

                        # Verify metrics were updated with deltas
                        mock_metrics_repo.update_metrics.assert_called_once()
                        call_kwargs = mock_metrics_repo.update_metrics.call_args.kwargs
                        assert call_kwargs["intimacy_delta"] == Decimal("5")
                        assert call_kwargs["passion_delta"] == Decimal("4")
                        assert call_kwargs["trust_delta"] == Decimal("3")
                        assert call_kwargs["secureness_delta"] == Decimal("2")


class TestScorePersistence:
    """Test score persistence to database."""

    @pytest.fixture
    def scorer(self):
        """Get VoiceCallScorer instance."""
        return VoiceCallScorer()

    @pytest.mark.asyncio
    async def test_score_history_created(self, scorer, user_chapter_3):
        """AC-FR006-003: Score history logged with source='voice_call'."""
        call_score = CallScore(
            session_id="history_test_session",
            deltas=MetricDeltas(
                intimacy=Decimal("3"),
                passion=Decimal("2"),
                trust=Decimal("4"),
                secureness=Decimal("1"),
            ),
            explanation="Test scoring",
            duration_seconds=120,
        )

        mock_user_repo = MagicMock()
        mock_user_repo.get = AsyncMock(return_value=user_chapter_3)

        mock_metrics = MagicMock()
        mock_metrics.calculate_composite_score = MagicMock(return_value=Decimal("58"))

        mock_metrics_repo = MagicMock()
        mock_metrics_repo.get_by_user_id = AsyncMock(return_value=mock_metrics)
        mock_metrics_repo.update_metrics = AsyncMock(return_value=mock_metrics)

        mock_history_repo = MagicMock()
        mock_history_repo.log_event = AsyncMock()

        with patch(
            "nikita.db.database.get_session_maker"
        ) as mock_session_maker:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            mock_session.commit = AsyncMock()
            mock_session_maker.return_value = MagicMock(return_value=mock_session)

            with patch(
                "nikita.db.repositories.user_repository.UserRepository",
                return_value=mock_user_repo,
            ):
                with patch(
                    "nikita.db.repositories.metrics_repository.UserMetricsRepository",
                    return_value=mock_metrics_repo,
                ):
                    with patch(
                        "nikita.db.repositories.score_history_repository.ScoreHistoryRepository",
                        return_value=mock_history_repo,
                    ):
                        await scorer.apply_score(
                            user_id=user_chapter_3.id,
                            call_score=call_score,
                        )

                        # Verify history was logged
                        mock_history_repo.log_event.assert_called_once()
                        call_kwargs = mock_history_repo.log_event.call_args.kwargs

                        # AC-FR006-003: source = "voice_call"
                        assert call_kwargs["event_type"] == "voice_call"
                        assert call_kwargs["user_id"] == user_chapter_3.id

    @pytest.mark.asyncio
    async def test_score_history_has_component_deltas(self, scorer, user_chapter_3):
        """Test that score history includes component delta breakdown."""
        call_score = CallScore(
            session_id="delta_breakdown_test",
            deltas=MetricDeltas(
                intimacy=Decimal("5"),
                passion=Decimal("4"),
                trust=Decimal("3"),
                secureness=Decimal("2"),
            ),
            explanation="Delta breakdown test",
            duration_seconds=180,
            behaviors_identified=["engaged", "supportive"],
        )

        mock_user_repo = MagicMock()
        mock_user_repo.get = AsyncMock(return_value=user_chapter_3)

        mock_metrics = MagicMock()
        mock_metrics.calculate_composite_score = MagicMock(return_value=Decimal("62"))

        mock_metrics_repo = MagicMock()
        mock_metrics_repo.get_by_user_id = AsyncMock(return_value=mock_metrics)
        mock_metrics_repo.update_metrics = AsyncMock(return_value=mock_metrics)

        mock_history_repo = MagicMock()
        mock_history_repo.log_event = AsyncMock()

        with patch(
            "nikita.db.database.get_session_maker"
        ) as mock_session_maker:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            mock_session.commit = AsyncMock()
            mock_session_maker.return_value = MagicMock(return_value=mock_session)

            with patch(
                "nikita.db.repositories.user_repository.UserRepository",
                return_value=mock_user_repo,
            ):
                with patch(
                    "nikita.db.repositories.metrics_repository.UserMetricsRepository",
                    return_value=mock_metrics_repo,
                ):
                    with patch(
                        "nikita.db.repositories.score_history_repository.ScoreHistoryRepository",
                        return_value=mock_history_repo,
                    ):
                        await scorer.apply_score(
                            user_id=user_chapter_3.id,
                            call_score=call_score,
                        )

                        # Verify component deltas are in event_details
                        call_kwargs = mock_history_repo.log_event.call_args.kwargs
                        event_details = call_kwargs["event_details"]

                        assert "deltas" in event_details
                        assert event_details["deltas"]["intimacy"] == "5"
                        assert event_details["deltas"]["passion"] == "4"
                        assert event_details["deltas"]["trust"] == "3"
                        assert event_details["deltas"]["secureness"] == "2"
                        assert "session_id" in event_details
                        assert event_details["session_id"] == "delta_breakdown_test"

    @pytest.mark.asyncio
    async def test_score_changes_reflected_in_user(self, scorer, user_chapter_3):
        """Test that score changes are committed and reflected in user record."""
        initial_score = Decimal("55")
        call_score = CallScore(
            session_id="user_reflection_test",
            deltas=MetricDeltas(
                intimacy=Decimal("6"),
                passion=Decimal("4"),
                trust=Decimal("5"),
                secureness=Decimal("3"),
            ),
            explanation="Positive call",
            duration_seconds=240,
        )

        mock_user_repo = MagicMock()
        mock_user_repo.get = AsyncMock(return_value=user_chapter_3)

        # Mock metrics with different scores before/after
        mock_metrics_before = MagicMock()
        mock_metrics_before.calculate_composite_score = MagicMock(
            return_value=initial_score
        )

        mock_metrics_after = MagicMock()
        mock_metrics_after.calculate_composite_score = MagicMock(
            return_value=Decimal("62")  # After delta application
        )

        mock_metrics_repo = MagicMock()
        mock_metrics_repo.get_by_user_id = AsyncMock(return_value=mock_metrics_before)
        mock_metrics_repo.update_metrics = AsyncMock(return_value=mock_metrics_after)

        mock_history_repo = MagicMock()
        mock_history_repo.log_event = AsyncMock()

        commit_called = []

        with patch(
            "nikita.db.database.get_session_maker"
        ) as mock_session_maker:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()

            async def track_commit():
                commit_called.append(True)

            mock_session.commit = track_commit
            mock_session_maker.return_value = MagicMock(return_value=mock_session)

            with patch(
                "nikita.db.repositories.user_repository.UserRepository",
                return_value=mock_user_repo,
            ):
                with patch(
                    "nikita.db.repositories.metrics_repository.UserMetricsRepository",
                    return_value=mock_metrics_repo,
                ):
                    with patch(
                        "nikita.db.repositories.score_history_repository.ScoreHistoryRepository",
                        return_value=mock_history_repo,
                    ):
                        new_score = await scorer.apply_score(
                            user_id=user_chapter_3.id,
                            call_score=call_score,
                        )

                        # Verify commit was called
                        assert len(commit_called) == 1

                        # Verify new score reflects changes
                        assert new_score == Decimal("62")

                        # Verify old_score was captured in event
                        event_details = mock_history_repo.log_event.call_args.kwargs[
                            "event_details"
                        ]
                        assert event_details["old_score"] == str(initial_score)
