"""Tests for all pipeline stages (T2.3-T2.10)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.pipeline.stages.base import StageError
from nikita.pipeline.models import PipelineContext


def _make_context(**overrides) -> PipelineContext:
    defaults = dict(
        conversation_id=uuid4(),
        user_id=uuid4(),
        started_at=datetime.now(timezone.utc),
        platform="text",
    )
    defaults.update(overrides)
    return PipelineContext(**defaults)


def _mock_session() -> MagicMock:
    return MagicMock()


@pytest.mark.asyncio
class TestExtractionStage:

    async def test_extraction_happy_path(self):
        from nikita.pipeline.stages.extraction import ExtractionStage, ExtractionResult
        ctx = _make_context()
        ctx.conversation = SimpleNamespace(
            messages=[SimpleNamespace(role="user", content="I love cats")]
        )
        stage = ExtractionStage(session=_mock_session())
        mock_extraction = ExtractionResult(
            facts=["User loves cats"],
            threads=["pets"],
            thoughts=["expressing warmth"],
            summary="User discussed pet preferences",
            emotional_tone="warm",
        )
        mock_agent_result = SimpleNamespace(data=mock_extraction)
        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=mock_agent_result)
        with patch.object(stage, "_get_agent", return_value=mock_agent):
            result = await stage._run(ctx)
        assert result["facts"] == ["User loves cats"]
        assert result["summary"] == "User discussed pet preferences"
        assert ctx.extracted_facts == ["User loves cats"]
        assert ctx.extraction_summary == "User discussed pet preferences"
        assert ctx.emotional_tone == "warm"

    async def test_extraction_no_conversation_raises(self):
        from nikita.pipeline.stages.extraction import ExtractionStage
        ctx = _make_context()
        ctx.conversation = None
        stage = ExtractionStage(session=_mock_session())
        with pytest.raises(StageError, match="No conversation loaded"):
            await stage._run(ctx)

    async def test_extraction_empty_messages_skips(self):
        from nikita.pipeline.stages.extraction import ExtractionStage
        ctx = _make_context()
        ctx.conversation = SimpleNamespace(messages=[])
        stage = ExtractionStage(session=_mock_session())
        result = await stage._run(ctx)
        assert result["facts"] == []
        assert result["tone"] == "neutral"

    async def test_extraction_llm_failure_raises_stage_error(self):
        from nikita.pipeline.stages.extraction import ExtractionStage
        ctx = _make_context()
        ctx.conversation = SimpleNamespace(
            messages=[SimpleNamespace(role="user", content="hi")]
        )
        stage = ExtractionStage(session=_mock_session())
        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(side_effect=RuntimeError("API timeout"))
        with patch.object(stage, "_get_agent", return_value=mock_agent):
            with pytest.raises(StageError, match="Extraction LLM call failed"):
                await stage._run(ctx)

    async def test_extraction_is_critical(self):
        from nikita.pipeline.stages.extraction import ExtractionStage
        assert ExtractionStage.is_critical is True
        assert ExtractionStage.name == "extraction"


@pytest.mark.asyncio
class TestMemoryUpdateStage:

    async def test_memory_update_stores_facts(self):
        from nikita.pipeline.stages.memory_update import MemoryUpdateStage
        ctx = _make_context()
        ctx.extracted_facts = [
            {"content": "User likes pizza", "type": "preference"},
            {"content": "User works at Google", "type": "fact"},
        ]
        stage = MemoryUpdateStage(session=_mock_session())
        mm = AsyncMock()
        mm.find_similar = AsyncMock(return_value=None)
        mm.add_fact = AsyncMock()
        ms = MagicMock()
        ms.openai_api_key = "test-key"
        with (
            patch("nikita.memory.supabase_memory.SupabaseMemory", return_value=mm) as p1,
            patch("nikita.config.settings.get_settings", return_value=ms),
        ):
            # Also patch lazy imports in the stage module
            with (
                patch.dict("sys.modules", {}),
            ):
                pass
            result = await stage._run(ctx)
        assert result["stored"] == 2
        assert result["deduplicated"] == 0
        assert ctx.facts_stored == 2
        assert mm.add_fact.call_count == 2

    async def test_memory_update_deduplicates(self):
        from nikita.pipeline.stages.memory_update import MemoryUpdateStage
        ctx = _make_context()
        ctx.extracted_facts = [{"content": "User likes pizza"}, {"content": "User likes pizza a lot"}]
        stage = MemoryUpdateStage(session=_mock_session())
        mm = AsyncMock()
        mm.find_similar = AsyncMock(side_effect=[None, [{"fact": "existing"}]])
        mm.add_fact = AsyncMock()
        ms = MagicMock()
        ms.openai_api_key = "test-key"
        with (
            patch("nikita.memory.supabase_memory.SupabaseMemory", return_value=mm),
            patch("nikita.config.settings.get_settings", return_value=ms),
        ):
            result = await stage._run(ctx)
        assert result["stored"] == 1
        assert result["deduplicated"] == 1

    async def test_memory_update_no_facts_skips(self):
        from nikita.pipeline.stages.memory_update import MemoryUpdateStage
        ctx = _make_context()
        ctx.extracted_facts = []
        stage = MemoryUpdateStage(session=_mock_session())
        result = await stage._run(ctx)
        assert result["stored"] == 0

    async def test_memory_update_fact_error_continues(self):
        from nikita.pipeline.stages.memory_update import MemoryUpdateStage
        ctx = _make_context()
        ctx.extracted_facts = [{"content": "fact1"}, {"content": "fact2"}]
        stage = MemoryUpdateStage(session=_mock_session())
        mm = AsyncMock()
        mm.find_similar = AsyncMock(return_value=None)
        mm.add_fact = AsyncMock(side_effect=[RuntimeError("DB error"), None])
        ms = MagicMock()
        ms.openai_api_key = "test-key"
        with (
            patch("nikita.memory.supabase_memory.SupabaseMemory", return_value=mm),
            patch("nikita.config.settings.get_settings", return_value=ms),
        ):
            result = await stage._run(ctx)
        assert result["stored"] == 1

    async def test_classify_graph_type_nikita(self):
        from nikita.pipeline.stages.memory_update import MemoryUpdateStage
        stage = MemoryUpdateStage(session=_mock_session())
        assert stage._classify_graph_type({"type": "nikita_event"}) == "nikita"
        assert stage._classify_graph_type({"type": "nikita_life"}) == "nikita"

    async def test_classify_graph_type_user(self):
        from nikita.pipeline.stages.memory_update import MemoryUpdateStage
        stage = MemoryUpdateStage(session=_mock_session())
        assert stage._classify_graph_type({"type": "preference"}) == "user"
        assert stage._classify_graph_type({"type": "personal_info"}) == "user"

    async def test_classify_graph_type_relationship(self):
        from nikita.pipeline.stages.memory_update import MemoryUpdateStage
        stage = MemoryUpdateStage(session=_mock_session())
        assert stage._classify_graph_type({"content": "nikita said something", "type": ""}) == "relationship"
        assert stage._classify_graph_type({"type": "random", "content": ""}) == "relationship"

    async def test_memory_update_is_critical(self):
        from nikita.pipeline.stages.memory_update import MemoryUpdateStage
        assert MemoryUpdateStage.is_critical is True


@pytest.mark.asyncio
class TestLifeSimStage:

    async def test_life_sim_generates_events(self):
        from nikita.pipeline.stages.life_sim import LifeSimStage
        ctx = _make_context()
        stage = LifeSimStage(session=_mock_session())
        mock_events = [{"type": "coffee"}, {"type": "work"}]
        with patch("nikita.life_simulation.LifeSimulator") as MS:
            MS.return_value.get_today_events = AsyncMock(return_value=mock_events)
            MS.return_value.generate_next_day_events = AsyncMock(return_value=mock_events)
            result = await stage._run(ctx)
        assert result["events_generated"] == 2
        assert ctx.life_events == mock_events

    async def test_life_sim_empty_events(self):
        from nikita.pipeline.stages.life_sim import LifeSimStage
        ctx = _make_context()
        stage = LifeSimStage(session=_mock_session())
        with patch("nikita.life_simulation.LifeSimulator") as MS:
            MS.return_value.get_today_events = AsyncMock(return_value=[])
            MS.return_value.generate_next_day_events = AsyncMock(return_value=[])
            result = await stage._run(ctx)
        assert result["events_generated"] == 0

    async def test_life_sim_is_non_critical(self):
        from nikita.pipeline.stages.life_sim import LifeSimStage
        assert LifeSimStage.is_critical is False


@pytest.mark.asyncio
class TestEmotionalStage:

    async def test_emotional_computes_4d_state(self):
        from nikita.pipeline.stages.emotional import EmotionalStage
        ctx = _make_context()
        ctx.chapter = 2
        ctx.relationship_score = Decimal("65")
        stage = EmotionalStage(session=_mock_session())
        ms = SimpleNamespace(arousal=0.6, valence=0.7, dominance=0.5, intimacy=0.4)
        with (
            patch("nikita.emotional_state.computer.StateComputer") as MC,
            patch("nikita.emotional_state.computer.EmotionalStateModel"),
        ):
            MC.return_value.compute = MagicMock(return_value=ms)
            result = await stage._run(ctx)
        assert result == {"arousal": 0.6, "valence": 0.7, "dominance": 0.5, "intimacy": 0.4}
        assert ctx.emotional_state["arousal"] == 0.6

    async def test_emotional_passes_life_events(self):
        """Life events with emotional_impact are converted to LifeEventImpact."""
        from nikita.pipeline.stages.emotional import EmotionalStage
        ctx = _make_context()
        # Simulate LifeEvent objects with emotional_impact attribute
        ctx.life_events = [
            SimpleNamespace(
                emotional_impact=SimpleNamespace(
                    arousal_delta=0.1,
                    valence_delta=-0.2,
                    dominance_delta=0.05,
                    intimacy_delta=0.0,
                ),
            )
        ]
        stage = EmotionalStage(session=_mock_session())
        ms = SimpleNamespace(arousal=0.8, valence=0.3, dominance=0.6, intimacy=0.2)
        with (
            patch("nikita.emotional_state.computer.StateComputer") as MC,
            patch("nikita.emotional_state.computer.EmotionalStateModel"),
        ):
            MC.return_value.compute = MagicMock(return_value=ms)
            await stage._run(ctx)
            kw = MC.return_value.compute.call_args[1]
            assert kw["life_events"] is not None
            assert len(kw["life_events"]) == 1
            impact = kw["life_events"][0]
            assert impact.arousal_delta == 0.1
            assert impact.valence_delta == -0.2

    async def test_emotional_passes_conversation_tone(self):
        """emotional_tone string is converted to ConversationTone enum."""
        from nikita.pipeline.stages.emotional import EmotionalStage
        ctx = _make_context()
        ctx.emotional_tone = "supportive"
        stage = EmotionalStage(session=_mock_session())
        ms = SimpleNamespace(arousal=0.5, valence=0.7, dominance=0.5, intimacy=0.6)
        with (
            patch("nikita.emotional_state.computer.StateComputer") as MC,
            patch("nikita.emotional_state.computer.EmotionalStateModel"),
        ):
            MC.return_value.compute = MagicMock(return_value=ms)
            await stage._run(ctx)
            kw = MC.return_value.compute.call_args[1]
            assert kw["conversation_tones"] is not None
            assert len(kw["conversation_tones"]) == 1
            assert kw["conversation_tones"][0].value == "supportive"

    async def test_emotional_empty_events_as_none(self):
        from nikita.pipeline.stages.emotional import EmotionalStage
        ctx = _make_context()
        ctx.life_events = []
        stage = EmotionalStage(session=_mock_session())
        ms = SimpleNamespace(arousal=0.5, valence=0.5, dominance=0.5, intimacy=0.5)
        with (
            patch("nikita.emotional_state.computer.StateComputer") as MC,
            patch("nikita.emotional_state.computer.EmotionalStateModel"),
        ):
            MC.return_value.compute = MagicMock(return_value=ms)
            await stage._run(ctx)
            kw = MC.return_value.compute.call_args[1]
            assert kw["life_events"] is None

    async def test_emotional_is_non_critical(self):
        from nikita.pipeline.stages.emotional import EmotionalStage
        assert EmotionalStage.is_critical is False


@pytest.mark.asyncio
class TestGameStateStage:

    async def test_game_state_returns_defaults_no_conversation(self):
        """With no conversation, score_delta defaults to 0."""
        from nikita.pipeline.stages.game_state import GameStateStage
        ctx = _make_context()
        stage = GameStateStage(session=_mock_session())
        result = await stage._run(ctx)
        assert result["score_delta"] == Decimal("0")
        assert result["chapter_changed"] is False
        assert ctx.score_delta == Decimal("0")

    async def test_game_state_reads_conversation_score_delta(self):
        """Reads score_delta from conversation model."""
        from nikita.pipeline.stages.game_state import GameStateStage
        ctx = _make_context()
        ctx.conversation = SimpleNamespace(score_delta=Decimal("1.50"))
        stage = GameStateStage(session=_mock_session())
        result = await stage._run(ctx)
        assert result["score_delta"] == Decimal("1.50")
        assert ctx.score_delta == Decimal("1.50")

    async def test_game_state_none_score_delta_on_conversation(self):
        """Conversation with None score_delta defaults to 0."""
        from nikita.pipeline.stages.game_state import GameStateStage
        ctx = _make_context()
        ctx.conversation = SimpleNamespace(score_delta=None)
        stage = GameStateStage(session=_mock_session())
        result = await stage._run(ctx)
        assert result["score_delta"] == Decimal("0")

    async def test_game_state_boss_threshold_near(self):
        """Detects when score is near boss threshold."""
        from nikita.pipeline.stages.game_state import GameStateStage
        ctx = _make_context()
        ctx.chapter = 1
        ctx.relationship_score = Decimal("52")  # threshold is 55, distance=3
        stage = GameStateStage(session=_mock_session())
        result = await stage._run(ctx)
        assert "boss_threshold_near" in result["events"]

    async def test_game_state_boss_threshold_reached(self):
        """Detects when score meets/exceeds boss threshold."""
        from nikita.pipeline.stages.game_state import GameStateStage
        ctx = _make_context()
        ctx.chapter = 1
        ctx.relationship_score = Decimal("55")  # equals threshold
        stage = GameStateStage(session=_mock_session())
        result = await stage._run(ctx)
        assert "boss_threshold_reached" in result["events"]

    async def test_game_state_invalid_chapter_warning(self):
        """Logs warning for invalid chapter number."""
        from nikita.pipeline.stages.game_state import GameStateStage
        ctx = _make_context()
        ctx.chapter = 99
        stage = GameStateStage(session=_mock_session())
        result = await stage._run(ctx)
        assert "invalid_chapter" in result["events"]

    async def test_game_state_populates_context(self):
        from nikita.pipeline.stages.game_state import GameStateStage
        ctx = _make_context()
        stage = GameStateStage(session=_mock_session())
        await stage._run(ctx)
        assert ctx.chapter_changed is False
        assert ctx.decay_applied is False

    async def test_game_state_is_non_critical(self):
        from nikita.pipeline.stages.game_state import GameStateStage
        assert GameStateStage.is_critical is False


@pytest.mark.asyncio
class TestConflictStage:

    async def test_conflict_no_trigger(self):
        """Default temperature (CALM zone) triggers no conflict."""
        from nikita.pipeline.stages.conflict import ConflictStage
        ctx = _make_context()
        ctx.emotional_state = {"arousal": 0.5, "valence": 0.6, "dominance": 0.5, "intimacy": 0.5}
        stage = ConflictStage(session=_mock_session())
        result = await stage._run(ctx)
        assert result["active"] is False
        assert ctx.active_conflict is False

    async def test_conflict_cold_valence_triggers(self):
        """HOT zone conflict_details triggers active conflict."""
        from nikita.pipeline.stages.conflict import ConflictStage
        ctx = _make_context()
        ctx.emotional_state = {"arousal": 0.5, "valence": 0.2, "dominance": 0.5, "intimacy": 0.5}
        ctx.conflict_details = {"temperature": 60.0, "zone": "hot", "last_temp_update": None}
        stage = ConflictStage(session=_mock_session())
        result = await stage._run(ctx)
        assert result["active"] is True
        assert result["type"] == "hot"
        assert ctx.conflict_type == "hot"

    async def test_conflict_normal_valence_no_trigger(self):
        """CALM zone does not trigger conflict."""
        from nikita.pipeline.stages.conflict import ConflictStage
        ctx = _make_context()
        ctx.emotional_state = {"arousal": 0.5, "valence": 0.4, "dominance": 0.5, "intimacy": 0.5}
        stage = ConflictStage(session=_mock_session())
        result = await stage._run(ctx)
        assert result["active"] is False

    async def test_conflict_defaults_on_empty_emotional_state(self):
        """Empty emotional_state defaults to CALM zone (no conflict)."""
        from nikita.pipeline.stages.conflict import ConflictStage
        ctx = _make_context()
        ctx.emotional_state = {}
        stage = ConflictStage(session=_mock_session())
        result = await stage._run(ctx)
        assert result["active"] is False

    async def test_conflict_error_graceful(self):
        """Temperature engine error falls back to no conflict."""
        from nikita.pipeline.stages.conflict import ConflictStage
        ctx = _make_context()
        ctx.emotional_state = {"arousal": 0.5, "valence": 0.5, "dominance": 0.5, "intimacy": 0.5}
        stage = ConflictStage(session=_mock_session())
        with patch("nikita.conflicts.models.ConflictDetails.from_jsonb", side_effect=RuntimeError("DB")):
            result = await stage._run(ctx)
        assert result["active"] is False
        assert ctx.active_conflict is False

    async def test_conflict_is_non_critical(self):
        from nikita.pipeline.stages.conflict import ConflictStage
        assert ConflictStage.is_critical is False


@pytest.mark.asyncio
class TestTouchpointStage:

    async def test_touchpoint_evaluates(self):
        from nikita.pipeline.stages.touchpoint import TouchpointStage
        ctx = _make_context()
        stage = TouchpointStage(session=_mock_session())
        with patch("nikita.touchpoints.engine.TouchpointEngine") as ME:
            ME.return_value.evaluate_and_schedule_for_user = AsyncMock(return_value=None)
            result = await stage._run(ctx)
        assert result["scheduled"] is False

    async def test_touchpoint_scheduled_true(self):
        from nikita.pipeline.stages.touchpoint import TouchpointStage
        ctx = _make_context()
        stage = TouchpointStage(session=_mock_session())
        with patch("nikita.touchpoints.engine.TouchpointEngine") as ME:
            ME.return_value.evaluate_and_schedule_for_user = AsyncMock(return_value={"id": "tp-1"})
            result = await stage._run(ctx)
        assert result["scheduled"] is True
        assert ctx.touchpoint_scheduled is True

    async def test_touchpoint_engine_error_graceful(self):
        from nikita.pipeline.stages.touchpoint import TouchpointStage
        ctx = _make_context()
        stage = TouchpointStage(session=_mock_session())
        with patch("nikita.touchpoints.engine.TouchpointEngine") as ME:
            ME.return_value.evaluate_and_schedule_for_user = AsyncMock(side_effect=RuntimeError("DB error"))
            result = await stage._run(ctx)
        assert result["scheduled"] is False
        assert ctx.touchpoint_scheduled is False

    async def test_touchpoint_is_non_critical(self):
        from nikita.pipeline.stages.touchpoint import TouchpointStage
        assert TouchpointStage.is_critical is False


@pytest.mark.asyncio
class TestSummaryStage:

    async def test_summary_with_llm_fallback(self):
        """When extraction_summary is empty, falls back to LLM summarization."""
        from nikita.pipeline.stages.summary import SummaryStage
        ctx = _make_context()
        ctx.conversation = SimpleNamespace(
            messages=[{"role": "user", "content": "I went hiking today"}],
            conversation_summary=None,
        )
        stage = SummaryStage(session=_mock_session())
        mock_result = SimpleNamespace(output="User went hiking today and enjoyed it")
        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=mock_result)
        with patch("nikita.pipeline.stages.summary.SummaryStage._summarize_with_llm", return_value="User went hiking today and enjoyed it"):
            result = await stage._run(ctx)
        assert "daily_updated" in result
        assert "summary" in result
        assert result["daily_updated"] is True
        assert "hiking" in result["summary"].lower()

    async def test_summary_with_extraction_summary(self):
        """Extraction summary is used directly when available (no LLM call)."""
        from nikita.pipeline.stages.summary import SummaryStage
        ctx = _make_context()
        ctx.extraction_summary = "User talked about hiking and feeling stressed"
        ctx.conversation = SimpleNamespace(
            messages=[{"role": "user", "content": "hi"}],
            conversation_summary=None,
        )
        stage = SummaryStage(session=_mock_session())
        result = await stage._run(ctx)
        assert result["daily_updated"] is True
        assert "hiking" in result["summary"].lower()
        assert ctx.daily_summary_updated is True

    async def test_summary_no_conversation_skips(self):
        from nikita.pipeline.stages.summary import SummaryStage
        ctx = _make_context()
        ctx.conversation = None
        ctx.extraction_summary = ""
        stage = SummaryStage(session=_mock_session())
        result = await stage._run(ctx)
        assert result["daily_updated"] is False

    async def test_summary_llm_error_graceful(self):
        """LLM error falls back to empty summary gracefully."""
        from nikita.pipeline.stages.summary import SummaryStage
        ctx = _make_context()
        ctx.conversation = SimpleNamespace(
            messages=[{"role": "user", "content": "hello"}],
            conversation_summary=None,
        )
        stage = SummaryStage(session=_mock_session())
        with patch.object(stage, "_summarize_with_llm", return_value=""):
            result = await stage._run(ctx)
        assert result["daily_updated"] is False
        assert result["summary"] == ""

    async def test_summary_is_non_critical(self):
        from nikita.pipeline.stages.summary import SummaryStage
        assert SummaryStage.is_critical is False


@pytest.mark.asyncio
class TestPromptBuilderStage:

    async def test_prompt_builder_placeholder(self):
        from nikita.pipeline.stages.prompt_builder import PromptBuilderStage
        ctx = _make_context()
        stage = PromptBuilderStage(session=_mock_session())
        result = await stage._run(ctx)
        # T3.3+T3.4: Now generates prompts for both platforms
        assert result["generated"] is True
        assert result["text_generated"] is True
        assert result["voice_generated"] is True
        assert result["text_tokens"] > 0
        assert result["voice_tokens"] > 0

    async def test_prompt_builder_is_non_critical(self):
        from nikita.pipeline.stages.prompt_builder import PromptBuilderStage
        assert PromptBuilderStage.is_critical is False
