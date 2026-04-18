"""LLM-driven daily-arc planner for Nikita Heartbeat Engine (Spec 215 PR 215-C).

Generates Nikita's "daily life arc" — a 6-12 step timeline of activities/moods
across the day, plus a narrative paragraph used for prompt injection in the
text agent and proactive-touchpoint scheduling (US-3).

Contract (FROZEN per `specs/215-heartbeat-engine/contracts.md` Contract 1):
    - `DailyArc` Pydantic shape with `steps`, `narrative`, `model_used` fields
    - `generate_daily_arc(*, user, plan_date, session) -> DailyArc` async signature
    - 215-D consumes this output via `NikitaDailyPlanRepository.upsert_plan`

Model (per spec.md OD1): `claude-haiku-4-5-20251001` (cheap + fast for arc
generation; daily aggregate cost stays under FR-014 ceiling).

Pattern mirrored from `nikita/agents/text/agent.py:1-66` — Pydantic AI Agent
with structured-output via `output_type=DailyArc`, model from centralized
`Models.haiku()` registry, lazy `@lru_cache`d agent factory so tests can
import without `ANTHROPIC_API_KEY` set.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date
from functools import lru_cache
from typing import TYPE_CHECKING, Final

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from nikita.config.models import Models

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from nikita.db.models.user import User

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tuning constants (per .claude/rules/tuning-constants.md)
# ---------------------------------------------------------------------------

# Per-call wall-clock budget for the planner's Pydantic AI `agent.run()` to
# the upstream Anthropic API. A single hung LLM call must NOT block the daily-
# arcs tick, which fans out across all active users inside Cloud Run's 15-min
# request budget. 30s is well above p99 Haiku 4.5 latency (~2-4s observed) yet
# small enough that one stuck call only costs that user's slot, not the tick.
#
# Current value: 30.0
# Prior values: ∞ (unbounded — no asyncio.wait_for wrapping; bug GH #338)
# Driving change: GH #338 (B4 MEDIUM, Spec 215 pre-flag-flip blocker).
# Rationale: caps the worst-case per-user planner cost so the orchestrator
# in `nikita/api/routes/tasks.py::generate_daily_arcs` can record the failure
# (handler change tracked separately in GH #336 / B2) and skip rather than
# taking down the whole tick for ~100 users due to one hung Anthropic call.
PLANNER_TIMEOUT_S: Final[float] = 30.0


# ---------------------------------------------------------------------------
# Contract 1 — frozen Pydantic shape (215-C produces, 215-D consumes)
# ---------------------------------------------------------------------------


class ArcStep(BaseModel):
    """One discrete moment in Nikita's daily arc.

    Mirrors `contracts.md` Contract 1 verbatim. Field semantics:
        at: "HH:MM" 24h clock (e.g. "08:00", "19:30")
        state: natural-language activity / mood description
        action: optional structured action descriptor, e.g.
            {"type": "schedule_touchpoint_if", "condition": "user_idle_2h"}
            (215-D may consume; 215-C only emits None for Phase 1)
    """

    at: str = Field(description="HH:MM 24h clock time of this arc step")
    state: str = Field(description="What Nikita is doing/feeling at this time")
    action: dict | None = Field(
        default=None,
        description="Optional structured action; None for Phase 1 baseline arcs",
    )


class DailyArc(BaseModel):
    """A full day of Nikita's planned activities + narrative for prompt-injection.

    Per contract: 6-12 steps. `narrative` is the prose blob the text agent
    injects into its system prompt for tonal grounding. `model_used` is the
    audit column (always populated by 215-C; per OD1 default = Haiku 4.5).
    """

    steps: list[ArcStep] = Field(
        description="6-12 chronologically ordered arc steps spanning the day"
    )
    narrative: str = Field(
        description="Paragraph-form narrative for text-agent prompt injection"
    )
    model_used: str = Field(
        description="LLM model identifier used to generate this arc (audit column)"
    )


# ---------------------------------------------------------------------------
# Pydantic AI agent — lazy init so importing this module does not require
# ANTHROPIC_API_KEY to be set (mirrors `nikita/agents/text/agent.py` pattern)
# ---------------------------------------------------------------------------

_PLANNER_SYSTEM_PROMPT = """You are an internal narrative planner for Nikita, an AI \
girlfriend in a simulation game. Your job is to draft Nikita's daily life arc — what \
she is doing, feeling, and thinking across the next 24 hours — so other game systems \
can reference her plan when she initiates conversations or responds to the player.

Produce a `DailyArc` containing:

1. `steps`: between 6 and 12 chronologically ordered `ArcStep` entries. Each step has:
   - `at`: 24-hour clock time in "HH:MM" format (e.g. "07:30", "13:00", "22:45")
   - `state`: a short natural-language description of what Nikita is doing or feeling
     at that moment (e.g. "morning coffee on the balcony, slow start", "deep work \
session at the studio, phone on do-not-disturb")
   - `action`: leave as `null` for now (reserved for future scheduled touchpoints)

   Spread the steps across waking hours (typically ~07:00 to ~23:30). Include a \
realistic mix: morning routine, focused work, social moments, transitions, evening \
wind-down. Order them strictly by time (earliest first).

2. `narrative`: a single paragraph (3-5 sentences) written in third person, present \
tense, that summarizes Nikita's day in evocative prose. This is injected into the text \
agent's prompt so she can reference her own plans naturally in conversation. Avoid \
mentioning the player by name; write it as Nikita's own internal log of the day.

3. `model_used`: always set this to the exact model identifier you are running on, \
e.g. "claude-haiku-4-5-20251001". This is an audit field.

Keep the tone grounded and specific — favour concrete details over generic phrasing. \
Nikita is a real person with a real life; the arc should feel like a believable day."""


def _user_prompt_for(user: User, plan_date: date) -> str:
    """Build the user-message for the planner agent."""
    first_name = getattr(user, "first_name", None) or "Nikita"
    weekday = plan_date.strftime("%A")
    return (
        f"Generate today's daily arc for {first_name} on {plan_date.isoformat()} "
        f"({weekday}). Return a DailyArc with 6-12 chronologically ordered steps, "
        f"a 3-5 sentence narrative, and the model identifier you are running on."
    )


@lru_cache(maxsize=1)
def get_planner_agent() -> Agent:
    """Return the Pydantic AI agent that drafts daily arcs.

    Lazy-cached so `import nikita.heartbeat.planner` does not require
    `ANTHROPIC_API_KEY` (matches the pattern in `nikita/agents/text/agent.py`).
    """
    return Agent(
        model=Models.haiku(),
        output_type=DailyArc,
        system_prompt=_PLANNER_SYSTEM_PROMPT,
    )


async def _run_planner_agent(user: User, plan_date: date) -> DailyArc:
    """Invoke the Pydantic AI planner agent.

    Isolated as its own coroutine so unit tests can mock this single seam
    (`patch("nikita.heartbeat.planner._run_planner_agent")`) without touching
    Pydantic AI internals or requiring an `ANTHROPIC_API_KEY`.

    Wraps `agent.run()` in `asyncio.wait_for(timeout=PLANNER_TIMEOUT_S)` so
    a single hung Anthropic call cannot block the daily-arcs fan-out tick
    (GH #338, B4 MEDIUM). On timeout, raises `asyncio.TimeoutError` for the
    `generate_daily_arcs` handler in `nikita/api/routes/tasks.py` to record
    + skip the offending user (handler change tracked in GH #336).
    """
    agent = get_planner_agent()
    result = await asyncio.wait_for(
        agent.run(_user_prompt_for(user, plan_date)),
        timeout=PLANNER_TIMEOUT_S,
    )
    return result.output


# ---------------------------------------------------------------------------
# Public API — frozen contract per contracts.md Contract 1
# ---------------------------------------------------------------------------


async def generate_daily_arc(
    *,
    user: User,
    plan_date: date,
    session: AsyncSession,
) -> DailyArc:
    """Generate Nikita's daily emotional arc for ``user`` on ``plan_date``.

    Args:
        user: The active player whose Nikita-instance is generating an arc.
        plan_date: The calendar date the arc is for (YYYY-MM-DD).
        session: AsyncSession passed through for symmetry with 215-D's
            persistence call site; the planner itself does not write.

    Returns:
        A `DailyArc` with 6-12 chronologically-ordered steps, a narrative
        blob for prompt injection, and the model identifier used.

    Notes:
        - Mock all LLM calls in tests (per contracts.md docstring). Patch
          `nikita.heartbeat.planner._run_planner_agent` with an `AsyncMock`
          returning a `DailyArc` instance.
        - 215-D persists the result via `NikitaDailyPlanRepository.upsert_plan`
          using the field mapping documented in contracts.md.
    """
    # `session` is part of the frozen signature for forward-compat with future
    # callers that may want to read user state mid-planning; 215-C does not use
    # it directly. Access it lightly to satisfy linters / signal intent.
    del session  # noqa: F841 — reserved by frozen contract

    arc = await _run_planner_agent(user, plan_date)

    # Defensive: guarantee model_used is populated even if a mock omits it
    # (per contracts.md line 76-80 — 215-C MUST always populate this field).
    if not arc.model_used:
        arc = arc.model_copy(update={"model_used": Models.haiku()})

    logger.info(
        "heartbeat.planner.daily_arc_generated",
        extra={
            "user_id": str(getattr(user, "id", "unknown")),
            "plan_date": plan_date.isoformat(),
            "step_count": len(arc.steps),
            "model_used": arc.model_used,
        },
    )
    return arc
