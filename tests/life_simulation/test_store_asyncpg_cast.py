"""Regression tests for asyncpg :param::cast syntax bug (GH #638).

asyncpg parameter parser interprets :user_id::uuid as ambiguous;
Postgres returns "syntax error at or near ':'". All 3 INSERT
statements must use cast(:param AS type) instead.

These tests verify the SQL text passed to session.execute() contains
no `::<type>` cast syntax, and that the correct `cast(... AS ...)` form
is used instead. Tests fail against the unfixed store.py and pass after
the fix — satisfying the TDD RED → GREEN gate.
"""

import re
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, call
from uuid import uuid4

import pytest

from nikita.life_simulation.models import (
    EmotionalImpact,
    EntityType,
    EventDomain,
    EventType,
    LifeEvent,
    NarrativeArc,
    NikitaEntity,
    TimeOfDay,
)
from nikita.life_simulation.store import EventStore

# Regex that matches the broken asyncpg cast syntax: :param_name::type
BROKEN_CAST_PATTERN = re.compile(r":[a-zA-Z_]+::[a-zA-Z_]+")


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_session():
    """AsyncMock session that records all execute() calls."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def mock_session_factory(mock_session):
    """Session factory returning mock_session via context manager."""

    class MockContextManager:
        async def __aenter__(self):
            return mock_session

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    def factory():
        return MockContextManager()

    return factory


@pytest.fixture
def store(mock_session_factory):
    return EventStore(session_factory=mock_session_factory)


@pytest.fixture
def user_id():
    return uuid4()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _extract_sql_text(mock_session) -> list[str]:
    """Return all SQL strings passed as the first positional arg to execute()."""
    sql_texts = []
    for c in mock_session.execute.call_args_list:
        # Use c.args (robust) instead of c[0][0] (positional, fragile)
        sql_arg = c.args[0] if c.args else c.kwargs.get("statement")
        if sql_arg is not None:
            # SQLAlchemy TextClause stringifies to the SQL text
            sql_texts.append(str(sql_arg))
    return sql_texts


# ---------------------------------------------------------------------------
# save_entity — nikita_entities INSERT (:user_id::uuid at L356)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_save_entity_sql_no_asyncpg_cast_syntax(store, mock_session, user_id):
    """save_entity must NOT use :param::type cast syntax (asyncpg crashes).

    Regression test for GH #638: :user_id::uuid in nikita_entities INSERT.
    """
    entity = NikitaEntity(
        user_id=user_id,
        entity_type=EntityType.COLLEAGUE,
        name="Alice",
        description="Works in finance",
        relationship="Friendly colleague",
    )
    await store.save_entity(entity)

    sql_texts = _extract_sql_text(mock_session)
    assert sql_texts, "save_entity must call session.execute()"

    insert_sql = next(
        (s for s in sql_texts if "nikita_entities" in s.lower()), None
    )
    assert insert_sql is not None, "Expected an INSERT INTO nikita_entities statement"

    matches = BROKEN_CAST_PATTERN.findall(insert_sql)
    assert not matches, (
        f"save_entity SQL contains asyncpg-incompatible ::cast syntax: {matches}\n"
        f"SQL:\n{insert_sql}"
    )


@pytest.mark.asyncio
async def test_save_entity_sql_uses_cast_as_syntax(store, mock_session, user_id):
    """save_entity SQL must use cast(:user_id AS uuid) for uuid columns."""
    entity = NikitaEntity(
        user_id=user_id,
        entity_type=EntityType.FRIEND,
        name="Bob",
    )
    await store.save_entity(entity)

    sql_texts = _extract_sql_text(mock_session)
    insert_sql = next(
        (s for s in sql_texts if "nikita_entities" in s.lower()), None
    )
    assert insert_sql is not None

    # Must contain cast(... AS uuid) for user_id
    assert re.search(r"cast\s*\(\s*:user_id\s+AS\s+uuid\s*\)", insert_sql, re.IGNORECASE), (
        f"save_entity SQL must use cast(:user_id AS uuid), got:\n{insert_sql}"
    )


# ---------------------------------------------------------------------------
# save_event — nikita_life_events INSERT (:user_id::uuid, :entities::jsonb,
#              :emotional_impact::jsonb, :narrative_arc_id::uuid at L71-73)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_save_event_sql_no_asyncpg_cast_syntax(store, mock_session, user_id):
    """save_event must NOT use :param::type cast syntax (asyncpg crashes).

    Regression test for GH #638: L71-73 in nikita_life_events INSERT.
    """
    event = LifeEvent(
        user_id=user_id,
        event_date=date.today(),
        time_of_day=TimeOfDay.MORNING,
        domain=EventDomain.WORK,
        event_type=EventType.MEETING,
        description="Team standup meeting about Q2 planning",
        entities=["team"],
        emotional_impact=EmotionalImpact(valence_delta=0.1),
    )
    await store.save_event(event)

    sql_texts = _extract_sql_text(mock_session)
    assert sql_texts, "save_event must call session.execute()"

    insert_sql = next(
        (s for s in sql_texts if "nikita_life_events" in s.lower()), None
    )
    assert insert_sql is not None, "Expected an INSERT INTO nikita_life_events statement"

    matches = BROKEN_CAST_PATTERN.findall(insert_sql)
    assert not matches, (
        f"save_event SQL contains asyncpg-incompatible ::cast syntax: {matches}\n"
        f"SQL:\n{insert_sql}"
    )


@pytest.mark.asyncio
async def test_save_event_sql_uses_cast_as_syntax_for_all_typed_cols(
    store, mock_session, user_id
):
    """save_event SQL must use cast(... AS type) for all typed params."""
    event = LifeEvent(
        user_id=user_id,
        event_date=date.today(),
        time_of_day=TimeOfDay.AFTERNOON,
        domain=EventDomain.PERSONAL,
        event_type=EventType.GYM,
        description="Afternoon gym session to reset and recharge",
        entities=["gym"],
        emotional_impact=EmotionalImpact(valence_delta=0.2),
    )
    await store.save_event(event)

    sql_texts = _extract_sql_text(mock_session)
    insert_sql = next(
        (s for s in sql_texts if "nikita_life_events" in s.lower()), None
    )
    assert insert_sql is not None

    # user_id → cast AS uuid
    assert re.search(r"cast\s*\(\s*:user_id\s+AS\s+uuid\s*\)", insert_sql, re.IGNORECASE), (
        f"save_event SQL must use cast(:user_id AS uuid):\n{insert_sql}"
    )
    # entities → cast AS jsonb
    assert re.search(r"cast\s*\(\s*:entities\s+AS\s+jsonb\s*\)", insert_sql, re.IGNORECASE), (
        f"save_event SQL must use cast(:entities AS jsonb):\n{insert_sql}"
    )
    # emotional_impact → cast AS jsonb
    assert re.search(
        r"cast\s*\(\s*:emotional_impact\s+AS\s+jsonb\s*\)", insert_sql, re.IGNORECASE
    ), (
        f"save_event SQL must use cast(:emotional_impact AS jsonb):\n{insert_sql}"
    )
    # narrative_arc_id → cast AS uuid
    assert re.search(
        r"cast\s*\(\s*:narrative_arc_id\s+AS\s+uuid\s*\)", insert_sql, re.IGNORECASE
    ), (
        f"save_event SQL must use cast(:narrative_arc_id AS uuid):\n{insert_sql}"
    )


# ---------------------------------------------------------------------------
# save_arc — nikita_narrative_arcs INSERT (:user_id::uuid, :entities::jsonb,
#            :possible_outcomes::jsonb at L251-252)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_save_arc_sql_no_asyncpg_cast_syntax(store, mock_session, user_id):
    """save_arc must NOT use :param::type cast syntax (asyncpg crashes).

    Regression test for GH #638: L251-252 in nikita_narrative_arcs INSERT.
    """
    arc = NarrativeArc(
        user_id=user_id,
        domain=EventDomain.WORK,
        arc_type="project_deadline",
        start_date=date.today(),
        entities=["the project", "Lisa"],
        current_state="Project is on track",
    )
    await store.save_arc(arc)

    sql_texts = _extract_sql_text(mock_session)
    assert sql_texts, "save_arc must call session.execute()"

    insert_sql = next(
        (s for s in sql_texts if "nikita_narrative_arcs" in s.lower()), None
    )
    assert insert_sql is not None, "Expected an INSERT INTO nikita_narrative_arcs statement"

    matches = BROKEN_CAST_PATTERN.findall(insert_sql)
    assert not matches, (
        f"save_arc SQL contains asyncpg-incompatible ::cast syntax: {matches}\n"
        f"SQL:\n{insert_sql}"
    )


@pytest.mark.asyncio
async def test_save_arc_sql_uses_cast_as_syntax_for_all_typed_cols(
    store, mock_session, user_id
):
    """save_arc SQL must use cast(... AS type) for all typed params."""
    arc = NarrativeArc(
        user_id=user_id,
        domain=EventDomain.PERSONAL,
        arc_type="fitness_goal",
        start_date=date.today(),
        entities=["gym"],
        current_state="Started tracking workouts",
    )
    await store.save_arc(arc)

    sql_texts = _extract_sql_text(mock_session)
    insert_sql = next(
        (s for s in sql_texts if "nikita_narrative_arcs" in s.lower()), None
    )
    assert insert_sql is not None

    # user_id → cast AS uuid
    assert re.search(r"cast\s*\(\s*:user_id\s+AS\s+uuid\s*\)", insert_sql, re.IGNORECASE), (
        f"save_arc SQL must use cast(:user_id AS uuid):\n{insert_sql}"
    )
    # entities → cast AS jsonb
    assert re.search(r"cast\s*\(\s*:entities\s+AS\s+jsonb\s*\)", insert_sql, re.IGNORECASE), (
        f"save_arc SQL must use cast(:entities AS jsonb):\n{insert_sql}"
    )
    # possible_outcomes → cast AS jsonb
    assert re.search(
        r"cast\s*\(\s*:possible_outcomes\s+AS\s+jsonb\s*\)", insert_sql, re.IGNORECASE
    ), (
        f"save_arc SQL must use cast(:possible_outcomes AS jsonb):\n{insert_sql}"
    )
