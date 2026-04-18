"""Tests for Spec 215 PR 215-C — LLM-driven daily-arc planner.

Acceptance Criteria (per specs/215-heartbeat-engine/contracts.md Contract 1
and spec.md AC-FR2-001 / OD1):

- AC-1: generate_daily_arc returns a DailyArc Pydantic instance
- AC-2: DailyArc.steps contains 6-12 entries (per contracts.md line 23)
- AC-3: ArcStep.at values are chronologically ordered ("HH:MM" 24h)
- AC-4: DailyArc.narrative is a non-empty string (prompt-injection blob)
- AC-5: DailyArc.model_used is populated (audit column, per OD1: Haiku 4.5)

Timeout safety (GH #338, B4 MEDIUM, Spec 215 pre-flag-flip blocker):
- A single hung Anthropic API call must not block the daily-arcs tick to the
  Cloud Run 15-min timeout. The planner wraps `agent.run()` in
  `asyncio.wait_for(timeout=PLANNER_TIMEOUT_S)`.

All LLM calls are mocked — no live network access (per contracts.md docstring
"Mock all LLM calls in tests").
"""

from __future__ import annotations

import asyncio
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.heartbeat.planner import (
    PLANNER_TIMEOUT_S,
    ArcStep,
    DailyArc,
    _run_planner_agent,
    generate_daily_arc,
)


def _make_mock_arc(
    steps: list[ArcStep] | None = None,
    narrative: str = "Nikita's day starts with coffee and a morning walk before her studio session.",
    model_used: str = "claude-haiku-4-5-20251001",
) -> DailyArc:
    """Build a synthetic DailyArc the mocked LLM will 'return'."""
    if steps is None:
        steps = [
            ArcStep(at="07:00", state="waking up, slow start", action=None),
            ArcStep(at="09:00", state="coffee + walk", action=None),
            ArcStep(at="11:00", state="studio time", action=None),
            ArcStep(at="13:00", state="lunch with friend", action=None),
            ArcStep(at="16:00", state="errands", action=None),
            ArcStep(at="19:00", state="evening wind-down", action=None),
            ArcStep(at="22:30", state="bedtime, scrolls phone", action=None),
        ]
    return DailyArc(steps=steps, narrative=narrative, model_used=model_used)


@pytest.fixture
def mock_user() -> MagicMock:
    """Synthetic User entity (only attributes the planner reads)."""
    user = MagicMock()
    user.id = uuid4()
    user.telegram_id = 123456789
    user.first_name = "TestPlayer"
    user.game_state = "active"
    return user


@pytest.fixture
def mock_session() -> AsyncMock:
    """AsyncSession mock — planner does not write directly (215-D persists)."""
    return AsyncMock()


@pytest.fixture
def patched_agent_run():
    """Patch the planner's Pydantic AI agent .run() to return a synthetic DailyArc.

    The Pydantic AI Agent.run() returns an AgentRunResult-like object whose
    `.output` is the structured-output instance. We mirror that shape.
    """
    arc = _make_mock_arc()
    fake_result = MagicMock()
    fake_result.output = arc
    with patch(
        "nikita.heartbeat.planner._run_planner_agent",
        new=AsyncMock(return_value=arc),
    ) as mocked:
        yield mocked, arc


@pytest.mark.asyncio
async def test_returns_DailyArc_pydantic_instance(
    mock_user, mock_session, patched_agent_run
):
    """AC-1: generate_daily_arc returns a DailyArc Pydantic instance."""
    result = await generate_daily_arc(
        user=mock_user, plan_date=date(2026, 4, 18), session=mock_session
    )
    assert isinstance(result, DailyArc)


@pytest.mark.asyncio
async def test_arc_has_6_to_12_steps(mock_user, mock_session, patched_agent_run):
    """AC-2: DailyArc.steps contains 6-12 entries (contracts.md line 23)."""
    result = await generate_daily_arc(
        user=mock_user, plan_date=date(2026, 4, 18), session=mock_session
    )
    assert 6 <= len(result.steps) <= 12, (
        f"Expected 6-12 steps per contract, got {len(result.steps)}"
    )


@pytest.mark.asyncio
async def test_arc_steps_chronologically_ordered_by_at_field(
    mock_user, mock_session, patched_agent_run
):
    """AC-3: ArcStep.at values are chronologically ordered (HH:MM 24h)."""
    result = await generate_daily_arc(
        user=mock_user, plan_date=date(2026, 4, 18), session=mock_session
    )
    times_in_minutes = [
        int(step.at.split(":")[0]) * 60 + int(step.at.split(":")[1])
        for step in result.steps
    ]
    assert times_in_minutes == sorted(times_in_minutes), (
        f"Steps must be chronologically ordered, got {[s.at for s in result.steps]}"
    )


@pytest.mark.asyncio
async def test_narrative_is_non_empty_string(
    mock_user, mock_session, patched_agent_run
):
    """AC-4: DailyArc.narrative is a non-empty string (prompt-injection blob)."""
    result = await generate_daily_arc(
        user=mock_user, plan_date=date(2026, 4, 18), session=mock_session
    )
    assert isinstance(result.narrative, str)
    assert len(result.narrative.strip()) > 0


@pytest.mark.asyncio
async def test_model_used_field_populated(
    mock_user, mock_session, patched_agent_run
):
    """AC-5: DailyArc.model_used is populated (audit column; Haiku 4.5 per OD1).

    Per contracts.md line 76-80: 215-C must always populate model_used. The repo
    Optional exists for synthetic-test seeding only and is NOT a 215-D escape hatch.
    """
    result = await generate_daily_arc(
        user=mock_user, plan_date=date(2026, 4, 18), session=mock_session
    )
    assert isinstance(result.model_used, str)
    assert len(result.model_used) > 0
    # OD1: default model is Haiku 4.5 — string contains "haiku"
    assert "haiku" in result.model_used.lower(), (
        f"Per OD1 default model is Haiku 4.5, got model_used={result.model_used!r}"
    )


@pytest.mark.asyncio
async def test_planner_invokes_pydantic_ai_agent(
    mock_user, mock_session, patched_agent_run
):
    """Planner delegates to the Pydantic AI agent (mocked _run_planner_agent)."""
    mocked, _ = patched_agent_run
    await generate_daily_arc(
        user=mock_user, plan_date=date(2026, 4, 18), session=mock_session
    )
    mocked.assert_awaited_once()


# ---------------------------------------------------------------------------
# Timeout safety (GH #338, B4 MEDIUM)
# ---------------------------------------------------------------------------


def test_planner_timeout_constant_is_30_seconds():
    """Regression guard per .claude/rules/tuning-constants.md.

    Every tuning constant needs a test asserting its exact current value with
    a comment pointing to the driving issue. Silent drift is the anti-pattern;
    intentional change requires updating BOTH this assertion and the docstring
    on PLANNER_TIMEOUT_S in nikita/heartbeat/planner.py.

    Driving issue: GH #338 (B4 MEDIUM, Spec 215 pre-flag-flip blocker).
    Rationale: a single hung Anthropic LLM call must not block the
    daily-arcs tick to Cloud Run's 15-minute timeout. 30s is well above
    p99 Haiku latency (~2-4s) yet far below the per-tick budget shared
    across the user fan-out.
    """
    assert PLANNER_TIMEOUT_S == 30.0


@pytest.mark.asyncio
@pytest.mark.timeout(10)
async def test_planner_raises_timeout_when_agent_hangs_beyond_budget(
    mock_user, mock_session
):
    """GH #338: hung agent.run() must raise asyncio.TimeoutError, not block.

    Implementation note: we patch PLANNER_TIMEOUT_S to a tiny value so this
    test runs in ~0.05s wall-clock instead of 30s. The behavior under test
    (wait_for raises TimeoutError when the awaitable exceeds budget) is
    identical regardless of the timeout magnitude. The pytest.mark.timeout(10)
    is a hard upper bound: if the timeout wrapper is ever removed, this test
    will hang forever and pytest-timeout kills it after 10s.
    """

    async def _hang(*_args, **_kwargs):
        await asyncio.sleep(60)  # would exceed any sane PLANNER_TIMEOUT_S

    with (
        patch("nikita.heartbeat.planner.PLANNER_TIMEOUT_S", 0.05),
        patch(
            "nikita.heartbeat.planner.get_planner_agent",
            return_value=MagicMock(run=AsyncMock(side_effect=_hang)),
        ),
        pytest.raises(asyncio.TimeoutError),
    ):
        await _run_planner_agent(mock_user, date(2026, 4, 18))


@pytest.mark.asyncio
@pytest.mark.timeout(10)
async def test_planner_succeeds_within_timeout(mock_user, mock_session):
    """GH #338: agent.run() returning quickly must not raise TimeoutError.

    Confirms the timeout wrapper does not introduce false positives — when
    the LLM responds within budget, the structured output is returned
    unchanged.
    """
    arc = _make_mock_arc()
    fake_result = MagicMock()
    fake_result.output = arc

    with patch(
        "nikita.heartbeat.planner.get_planner_agent",
        return_value=MagicMock(run=AsyncMock(return_value=fake_result)),
    ):
        result = await _run_planner_agent(mock_user, date(2026, 4, 18))

    assert isinstance(result, DailyArc)
    assert result.model_used == arc.model_used
