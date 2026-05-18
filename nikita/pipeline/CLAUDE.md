# pipeline/ — Unified 11-Stage Async Pipeline

## Diagram (W6.5, code-verified)

[**Diagram A — 11-Stage Pipeline**](https://www.figma.com/board/CgTUZGxzzNJNySxgf9IfGZ) — derived from `orchestrator.py:47-59` at master HEAD. Shows 5 invocation sites, all 11 stages with `file:line` citations, and smell badges (state collisions on `extraction_summary` and `conflict_details`, bare-Exception swallow at `:308/:343`, hardcoded `stages_total=11` at `:186`, vice stage produces no ctx output).

## Purpose

Post-conversation processing pipeline (Specs 042+067). Runs after text/voice sessions end to extract facts, persist thoughts, update memory, simulate life events, and rebuild prompts.

## Status: Complete (74 tests, 11 stages incl. PersistenceStage)

## Architecture

```
pipeline/
├── orchestrator.py         # PipelineOrchestrator — sequential stage runner
├── models.py               # PipelineContext, PipelineResult
├── stages/
│   ├── base.py             # PipelineStage base class, StageResult
│   ├── extraction.py       # ExtractionStage (CRITICAL) — LLM fact extraction
│   ├── persistence.py      # PersistenceStage (non-critical, pos 2) — nikita_thoughts DB writes (Spec 116: before memory_update)
│   ├── memory_update.py    # MemoryUpdateStage (CRITICAL) — pgVector writes
│   ├── life_sim.py         # LifeSimStage — simulated Nikita life events
│   ├── emotional.py        # EmotionalStage — relationship dynamics
│   ├── vice.py             # ViceStage (Spec 114 GE-006) — side-effects only, no ctx output
│   ├── game_state.py       # GameStateStage — chapter/boss progression
│   ├── conflict.py         # ConflictStage — argument/tension handling
│   ├── touchpoint.py       # TouchpointStage — proactive message scheduling
│   ├── summary.py          # SummaryStage — daily conversation summaries
│   └── prompt_builder.py   # PromptBuilderStage — rebuild cached system prompt
└── templates/              # Jinja2 prompt templates for LLM stages
```

## Key Concepts

- **Critical stages** (extraction, memory_update): Failure stops pipeline
- **Non-critical stages**: Failure logs and continues to next stage
- **Sequential execution**: Stages run in order, each receives PipelineContext
- **Triggered by**: pg_cron (every minute) via `POST /tasks/process-conversations`

## Usage

```python
from nikita.pipeline.orchestrator import PipelineOrchestrator

orchestrator = PipelineOrchestrator(session)
result = await orchestrator.process(conversation_id, user_id, platform="telegram")
# result.success, result.stages_completed, result.errors
```

## Stage Base Class

```python
class PipelineStage:
    name: str               # Stage identifier
    is_critical: bool       # Stop pipeline on failure?
    timeout_seconds: float  # Per-stage timeout
    max_retries: int        # Retry with exponential backoff

    async def run(self, context: PipelineContext) -> StageResult
```

## Tests

```bash
pytest tests/pipeline/ -v
```

## Documentation

- [Context Module](../context/CLAUDE.md) — legacy context engineering (pre-042)
- [Memory System](../memory/CLAUDE.md) — SupabaseMemory integration

## Callers

5 PipelineOrchestrator invocation sites repo-wide (`PipelineOrchestrator.process()`):

- `nikita/api/routes/admin.py:628` — admin trigger (re-run pipeline on a conversation).
- `nikita/api/routes/tasks.py:788` — cron-driven processing path.
- `nikita/api/routes/tasks.py:962` — secondary cron handler.
- `nikita/api/routes/voice.py:801` — post-voice-call processing.
- `nikita/onboarding/handoff.py:705` — onboarding-to-main handoff.

**Telegram `message_handler.py` does NOT directly invoke the pipeline** — flows via cron path in `tasks.py`.

## Gotchas

- **State collisions**: `extraction_summary` written by stage 0 (`extraction.py:113`) then OVERWRITTEN by stage 9 (`prompt_builder.py:410`). `conflict_details` LOADED from DB and written to ctx by stage 4 (`emotional.py:150-151`) and READ from ctx by stage 7 (`conflict.py:52`). Surfaced in W4 audit; flagged on W6.5 Diagram A.
- **`vice` stage produces NO ctx output** (`stages/vice.py:21`) — side-effects only; opaque to downstream stages.
- **Bare `except Exception` swallow** at `orchestrator.py:308` and `:343` — silent failure on non-critical stages. Watch logs.
- **`stages_total = 11` hardcoded at `orchestrator.py:186`** — drift hardcoded inside the canonical file; must match `STAGE_DEFINITIONS` length.
- **Critical stages = 2**: `extraction` (stage 0) + `memory_update` (stage 2). All others are non-critical (`is_critical = False`); failures are logged but don't abort the pipeline. Spec 116 added the persistence-stage reorder so `extraction` survives `memory_update` failure.
- **`prompt_builder` is the heaviest stage** (24 ctx writes at `:97-135+`). Most expensive stage; profile here first.

## Navigation

- Backend module map: [`../CLAUDE.md`](../CLAUDE.md)
- Architecture canonical: [`../../memory/architecture.md`](../../memory/architecture.md) §"11-Stage Async Pipeline"
- Pipeline observability spec: [`../../specs/110-pipeline-observability-event-stream/`](../../specs/110-pipeline-observability-event-stream/)

Last verified: 2026-05-18
