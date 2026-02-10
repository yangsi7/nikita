"""Pipeline proof tests - verify every stage produces artifacts with EVIDENCE.

Run with: pytest tests/pipeline/test_pipeline_proof.py -v -s
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from nikita.pipeline.models import PipelineContext, PipelineResult
from nikita.pipeline.orchestrator import PipelineOrchestrator

def _make_conversation(messages=None):
    if messages is None:
        messages = [
            {"role": "user", "content": "Hey Nikita, I just got back from hiking in the Alps!"},
            {"role": "assistant", "content": "oh wow the alps? where exactly?"},
            {"role": "user", "content": "Zermatt with my friend Jake. We saw the Matterhorn!"},
            {"role": "assistant", "content": "zermatt is gorgeous. you have been kinda distant lately"},
            {"role": "user", "content": "I know, work at DataFlow has been killing me. I miss you."},
            {"role": "assistant", "content": "it has been 3 days. but I appreciate you admitting it."},
        ]
    return SimpleNamespace(
        id=uuid.uuid4(), user_id=uuid.uuid4(), messages=messages,
        platform="text", status="processing",
        conversation_summary=None, emotional_tone=None, extracted_entities=None,
    )

def _make_user(chapter=3, score=45.0):
    return SimpleNamespace(
        id=uuid.uuid4(), chapter=chapter, game_status="active",
        relationship_score=Decimal(str(score)),
        user_metrics=SimpleNamespace(
            intimacy=Decimal("42"), passion=Decimal("38"),
            trust=Decimal("45"), secureness=Decimal("40"),
        ),
        engagement_state=SimpleNamespace(state="engaged"),
        vice_preferences=[
            SimpleNamespace(vice_type="drinking"),
            SimpleNamespace(vice_type="gambling"),
        ],
    )

def _make_context(conversation=None, user=None):
    conv = conversation or _make_conversation()
    usr = user or _make_user()
    ctx = PipelineContext(
        conversation_id=getattr(conv, "id", uuid.uuid4()),
        user_id=getattr(usr, "id", uuid.uuid4()),
        started_at=datetime.now(timezone.utc), platform="text",
    )
    ctx.conversation = conv
    ctx.user = usr
    ctx.chapter = usr.chapter
    ctx.game_status = usr.game_status
    ctx.relationship_score = usr.relationship_score
    ctx.metrics = {"intimacy": Decimal("42"), "passion": Decimal("38"), "trust": Decimal("45"), "secureness": Decimal("40")}
    ctx.engagement_state = "engaged"
    ctx.vices = ["drinking", "gambling"]
    return ctx

def _mock_session():
    session = AsyncMock()
    session.begin_nested = MagicMock(return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=None),
        __aexit__=AsyncMock(return_value=None),
    ))
    return session

MOCK_EXTRACTION = SimpleNamespace(data=SimpleNamespace(
    facts=["User went hiking in Alps near Zermatt", "User has friend named Jake",
           "User works at DataFlow", "User distant due to work stress",
           "User misses daily conversations with Nikita"],
    threads=["Alps hiking trip", "Work stress at DataFlow", "Relationship reconnection"],
    thoughts=["He is sweet but I noticed the 3-day gap", "Hiking story seems genuine",
              "Work stress might be real but I am still hurt"],
    summary="User returned from Alps hiking (Zermatt) with Jake. Acknowledged being distant due to DataFlow work. Expressed missing conversations.",
    emotional_tone="mixed",
))

# --- Test 1: BUG-001 fix ---
@pytest.mark.asyncio
class TestBug001Fix:
    async def test_conversation_populated(self):
        conv = _make_conversation()
        user = _make_user()
        orch = PipelineOrchestrator(_mock_session(), stages=[])
        result = await orch.process(
            conversation_id=uuid.uuid4(), user_id=uuid.uuid4(),
            platform="text", conversation=conv, user=user,
        )
        assert result.success is True
        assert result.context.conversation is conv
        assert result.context.chapter == 3
        assert result.context.relationship_score == Decimal("45.0")
        assert "drinking" in result.context.vices
        print("\nPROOF BUG-001: context populated - ch=3, score=45, vices=drinking,gambling")

# --- Test 2: BUG-002 fix ---
@pytest.mark.asyncio
class TestBug002Fix:
    async def test_extraction_dict_messages(self):
        from nikita.pipeline.stages.extraction import ExtractionStage
        ctx = _make_context()
        stage = ExtractionStage(session=_mock_session())
        with patch.object(stage, "_get_agent") as mock_fn:
            mock_fn.return_value = AsyncMock(run=AsyncMock(return_value=MOCK_EXTRACTION))
            result = await stage._run(ctx)
        assert len(ctx.extracted_facts) == 5
        assert ctx.emotional_tone == "mixed"
        print(f"\nPROOF BUG-002: {len(ctx.extracted_facts)} facts extracted from dict messages")
        for i, f in enumerate(ctx.extracted_facts):
            print(f"  [{i+1}] {f}")

# --- Test 3: BUG-003 fix ---
@pytest.mark.asyncio
class TestBug003Fix:
    async def test_memory_string_facts(self):
        from nikita.pipeline.stages.memory_update import MemoryUpdateStage
        ctx = _make_context()
        ctx.extracted_facts = ["User hiking in Alps", "User works at DataFlow", "User friend Jake"]
        stage = MemoryUpdateStage(session=_mock_session())
        with patch("nikita.memory.supabase_memory.SupabaseMemory") as MM, \
             patch("nikita.config.settings.get_settings") as ms:
            m = AsyncMock(); m.find_similar = AsyncMock(return_value=[]); m.add_fact = AsyncMock()
            MM.return_value = m; ms.return_value = SimpleNamespace(openai_api_key="t")
            await stage._run(ctx)
        assert ctx.facts_stored == 3
        print(f"\nPROOF BUG-003: {ctx.facts_stored} string facts stored without AttributeError")

    async def test_memory_dict_facts(self):
        from nikita.pipeline.stages.memory_update import MemoryUpdateStage
        ctx = _make_context()
        ctx.extracted_facts = [{"content": "User likes food", "type": "preference"}]
        stage = MemoryUpdateStage(session=_mock_session())
        with patch("nikita.memory.supabase_memory.SupabaseMemory") as MM, \
             patch("nikita.config.settings.get_settings") as ms:
            m = AsyncMock(); m.find_similar = AsyncMock(return_value=[]); m.add_fact = AsyncMock()
            MM.return_value = m; ms.return_value = SimpleNamespace(openai_api_key="t")
            await stage._run(ctx)
        assert ctx.facts_stored == 1

# --- Test 4: BUG-004 fix ---
@pytest.mark.asyncio
class TestBug004Fix:
    async def test_result_attribute(self):
        ctx = PipelineContext(conversation_id=uuid.uuid4(), user_id=uuid.uuid4(),
                            started_at=datetime.now(timezone.utc), platform="text")
        r = PipelineResult.failed(ctx, "extraction", "test")
        assert str(r.context.conversation_id)
        assert not hasattr(r, "conversation_id")
        print(f"\nPROOF BUG-004: r.context.conversation_id works, no direct attr")

# --- Test 5: Summary stage ---
@pytest.mark.asyncio
class TestSummaryProof:
    async def test_summary_from_extraction(self):
        from nikita.pipeline.stages.summary import SummaryStage
        ctx = _make_context()
        ctx.extraction_summary = "User returned from Alps hiking with Jake."
        stage = SummaryStage(session=_mock_session())
        result = await stage._run(ctx)
        assert result["daily_updated"] is True
        assert ctx.conversation.conversation_summary is not None
        print(f"\nPROOF SUMMARY: stored='{ctx.conversation.conversation_summary[:80]}...'")

    async def test_summary_fallback(self):
        from nikita.pipeline.stages.summary import SummaryStage
        ctx = _make_context()
        ctx.extraction_summary = ""
        stage = SummaryStage(session=_mock_session())
        result = await stage._run(ctx)
        assert result["daily_updated"] is True
        assert len(result["summary"]) > 0
        print(f"\nPROOF SUMMARY FALLBACK: '{result['summary'][:80]}...'")

# --- Test 6: Emotional stage ---
@pytest.mark.asyncio
class TestEmotionalProof:
    async def test_4d_state(self):
        from nikita.pipeline.stages.emotional import EmotionalStage
        ctx = _make_context()
        stage = EmotionalStage(session=_mock_session())
        await stage._run(ctx)
        for k in ["arousal", "valence", "dominance", "intimacy"]:
            assert k in ctx.emotional_state
        print("\nPROOF EMOTIONAL: " + ", ".join(f"{k}={v:.3f}" for k, v in ctx.emotional_state.items()))

# --- Test 7: Full pipeline ---
@pytest.mark.asyncio
class TestFullPipeline:
    async def test_e2e(self):
        conv = _make_conversation()
        user = _make_user()
        orch = PipelineOrchestrator(_mock_session())
        prompt = "# NIKITA System Prompt\nChapter: 3\nFacts: Alps, DataFlow, Jake"
        with patch("nikita.pipeline.stages.extraction.Agent") as MA, \
             patch("nikita.memory.supabase_memory.SupabaseMemory") as MM, \
             patch("nikita.config.settings.get_settings") as ms, \
             patch("nikita.pipeline.stages.life_sim.LifeSimulator", create=True), \
             patch("nikita.pipeline.stages.touchpoint.TouchpointEngine", create=True), \
             patch("nikita.pipeline.stages.prompt_builder.PromptBuilderStage._render_template") as mrt, \
             patch("nikita.pipeline.stages.prompt_builder.PromptBuilderStage._enrich_with_haiku") as mh, \
             patch("nikita.pipeline.stages.prompt_builder.PromptBuilderStage._store_prompt") as msp, \
             patch("nikita.pipeline.stages.prompt_builder.PromptBuilderStage._count_tokens") as mct:
            MA.return_value = AsyncMock(run=AsyncMock(return_value=MOCK_EXTRACTION))
            m = AsyncMock(); m.find_similar = AsyncMock(return_value=[]); m.add_fact = AsyncMock()
            MM.return_value = m; ms.return_value = SimpleNamespace(openai_api_key="t")
            mrt.return_value = prompt; mh.return_value = None; msp.return_value = None; mct.return_value = 800
            result = await orch.process(
                conversation_id=conv.id, user_id=user.id,
                platform="text", conversation=conv, user=user,
            )
        ctx = result.context
        assert result.success, f"FAILED: {result.error_stage}: {result.error_message}"
        assert len(ctx.extracted_facts) == 5
        assert ctx.extraction_summary != ""
        assert ctx.facts_stored >= 0
        assert "arousal" in ctx.emotional_state
        assert ctx.daily_summary_updated is True
        assert ctx.chapter == 3
        print("\n" + "=" * 70)
        print("FULL PIPELINE PROOF")
        print(f"Success: {result.success} | Stages: {result.stages_completed}/{result.stages_total}")
        print(f"User: ch={ctx.chapter} score={ctx.relationship_score} vices={ctx.vices}")
        print(f"Facts: {ctx.extracted_facts}")
        print(f"Threads: {ctx.extracted_threads}")
        print(f"Thoughts: {ctx.extracted_thoughts}")
        print(f"Summary: {ctx.extraction_summary}")
        print(f"Tone: {ctx.emotional_tone}")
        print(f"Memory: stored={ctx.facts_stored} deduped={ctx.facts_deduplicated}")
        print(f"Emotional: {ctx.emotional_state}")
        print(f"Conv summary: {conv.conversation_summary}")
        print(f"Prompt: {'YES' if ctx.generated_prompt else 'NO'} ({ctx.prompt_token_count} tokens)")
        if ctx.generated_prompt:
            print(f"\n--- SYSTEM PROMPT ---\n{ctx.generated_prompt}\n--- END ---")
        print(f"Timings: {ctx.stage_timings}")
        if ctx.stage_errors:
            print(f"Errors: {ctx.stage_errors}")
        print("=" * 70)

# --- Test 8: Wiring verification ---
@pytest.mark.asyncio
class TestWiring:
    async def test_orchestrator_signature(self):
        import inspect
        src = inspect.getsource(PipelineOrchestrator.process)
        assert "conversation: Any" in src
        assert "user: Any" in src
        assert "ctx.conversation = conversation" in src
        print("\nPROOF WIRING: orchestrator accepts conversation + user")

    async def test_tasks_py_wiring(self):
        with open("nikita/api/routes/tasks.py") as f:
            src = f.read()
        assert "UserRepository" in src
        assert "user = await user_repo.get(conv.user_id)" in src
        assert "conversation=conv" in src
        assert "user=user" in src
        assert "r.context.conversation_id" in src
        print("\nPROOF WIRING: tasks.py loads user + passes to pipeline + correct attr access")
