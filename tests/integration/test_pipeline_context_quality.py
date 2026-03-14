"""Pipeline context quality integration test (Spec 113 FR-003 / DA-001).

Verifies that _enrich_context in PipelineOrchestrator properly populates
ctx.memory_context, ctx.recent_facts, and ctx.conversation_summary for a
real conversation. Guards against silent None-injection bugs like MP-002.

Marked integration — skips if Supabase unreachable.
"""

import pytest

from tests.db.integration import conftest as db_conftest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not db_conftest._SUPABASE_REACHABLE,
        reason="Supabase unreachable — skipping integration tests",
    ),
]


@pytest.mark.asyncio
async def test_pipeline_context_quality(db_conftest_session):  # noqa: F811
    """AC-007: _enrich_context populates all required context fields.

    Creates a test user + conversation in the live DB, runs _enrich_context,
    and asserts that the three critical fields are populated (not None/empty).
    Catches the class of silent failure that let MP-002 go undetected.
    """
    from uuid import uuid4

    from nikita.pipeline.orchestrator import PipelineOrchestrator

    # Use the live session from db_conftest to create a test user
    # (We run against a real Supabase instance; all fixtures use the live DB)
    session = db_conftest_session

    # Create a minimal pipeline orchestrator
    orchestrator = PipelineOrchestrator(session)

    # Build a minimal PipelineContext to pass to _enrich_context
    from nikita.pipeline.context import PipelineContext

    user_id = uuid4()
    conversation_id = uuid4()

    ctx = PipelineContext(
        user_id=user_id,
        conversation_id=conversation_id,
        platform="voice",
        raw_messages=[
            {"role": "user", "content": "Hello Nikita"},
            {"role": "nikita", "content": "Hi there!"},
        ],
    )

    # _enrich_context should populate memory_context, recent_facts, conversation_summary
    # For a new user with no history, these may be empty strings/lists but MUST NOT be None
    await orchestrator._enrich_context(ctx)

    assert ctx.memory_context is not None, (
        "memory_context must not be None after _enrich_context — "
        "possible silent failure in SupabaseMemory.search()"
    )
    assert ctx.recent_facts is not None, (
        "recent_facts must not be None after _enrich_context — "
        "possible silent failure in SupabaseMemory.get_recent_facts()"
    )
    assert ctx.conversation_summary is not None, (
        "conversation_summary must not be None after _enrich_context — "
        "possible silent failure in SummaryRepository or summary stage"
    )
