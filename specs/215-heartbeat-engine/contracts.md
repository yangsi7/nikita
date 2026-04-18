# Spec 215 — Cross-PR Frozen Contracts

> **Status**: LOCKED 2026-04-18 to enable parallel PR 215-C / 215-D / 215-F execution.
> Mutating these shapes mid-flight requires PAUSING any in-flight subagents
> via `SendMessage` and rebasing each affected worktree branch (see Plan v6 §6.7 +
> v6.12 FIX C4 at `.claude/plans/delightful-orbiting-ladybug.md`).
>
> **Authority**: Plan v6.3 P2 (parallel orchestration brief). Approved by user 2026-04-18.

## Contract 1 — DailyArc Pydantic shape (215-C produces, 215-D consumes)

```python
# nikita/heartbeat/planner.py — 215-C ships this
from pydantic import BaseModel
from datetime import date

class ArcStep(BaseModel):
    at: str           # "HH:MM" 24h clock (e.g. "08:00", "19:30")
    state: str        # natural-language activity/mood description
    action: dict | None  # {"type": "schedule_touchpoint_if", "condition": "..."} or None

class DailyArc(BaseModel):
    steps: list[ArcStep]   # 6-12 entries
    narrative: str         # paragraph for prompt injection
    model_used: str        # e.g. "claude-haiku-4-5-20251001"

async def generate_daily_arc(
    *, user, plan_date: date, session,
) -> DailyArc:
    """Generate Nikita's daily emotional arc for `user` on `plan_date`.

    Mock all LLM calls in tests. Use Pydantic AI Agent class per
    nikita/agents/text/agent.py:1-66 pattern. Model = Haiku 4.5 per OD1.
    """
```

### Storage contract (unambiguous — chosen 2026-04-18 per QA review of PR #331)

215-D persists a `DailyArc` instance via `NikitaDailyPlanRepository.upsert_plan`
using EXACTLY these field mappings (no redundancy, single source of truth per column):

```python
# In 215-D handler body:
arc = await generate_daily_arc(user=user, plan_date=plan_date, session=session)
await repo.upsert_plan(
    user_id=user.id,
    plan_date=plan_date,
    arc_json={"steps": [step.model_dump() for step in arc.steps]},  # steps only
    narrative=arc.narrative,                                          # separate column
    model_used=arc.model_used,                                        # separate column
)
```

**Rationale**: `arc_json` is the structured-execution payload (consumed by heartbeat
handler to pick next-due step). `narrative_text` is the prompt-injection blob
(consumed by text agent for tone). `model_used` is the audit column. Storing the
full `DailyArc.model_dump()` in `arc_json` would duplicate `narrative` and
`model_used` and create drift risk if 215-D ever updates one column without the
other.
```

## Contract 2 — JobName enum entries (215-D adds, 215-E references)

```python
# nikita/db/models/job_execution.py — 215-D appends these to existing JobName enum
HEARTBEAT = "heartbeat"
GENERATE_DAILY_ARCS = "generate_daily_arcs"
```

## Contract 3 — Endpoint paths (215-D ships, 215-E calls)

| Endpoint | Idempotency window | Auth |
|---|---|---|
| `POST /tasks/heartbeat` | 55 min (per AC-FR9-001) | `verify_task_secret` |
| `POST /tasks/generate-daily-arcs` | 1440 min (daily) | `verify_task_secret` |

Both endpoints mirror the `/refresh-voice-prompts` handler at `nikita/api/routes/tasks.py:902-982` for auth + idempotency-guard pattern.

## Mutation discipline

- **No silent edits**: any change to this file requires a fresh PR (cannot ship inside a feature PR).
- **Worktree sync on change**: per Plan v6.7, paused subagents must `git fetch && git rebase origin/master` after this file changes; orchestrator rebases on subagent's behalf if subagent has exited.
- **Contract scope**: this file binds 215-C / 215-D / 215-E / 215-F only. Phase 2 (Hawkes + self-scheduling) and Phase 3 (Bayesian) introduce their own contracts in separate spec cycles (216, 217).
