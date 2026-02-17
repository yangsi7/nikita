# pipeline/ — Unified 9-Stage Async Pipeline

## Purpose

Post-conversation processing pipeline (Spec 042). Runs after text/voice sessions end to extract facts, update memory, simulate life events, and rebuild prompts.

## Status: Complete (74 tests)

## Architecture

```
pipeline/
├── orchestrator.py         # PipelineOrchestrator — sequential stage runner
├── models.py               # PipelineContext, PipelineResult
├── stages/
│   ├── base.py             # PipelineStage base class, StageResult
│   ├── extraction.py       # ExtractionStage (CRITICAL) — LLM fact extraction
│   ├── memory_update.py    # MemoryUpdateStage (CRITICAL) — pgVector writes
│   ├── life_sim.py         # LifeSimStage — simulated Nikita life events
│   ├── emotional.py        # EmotionalStage — relationship dynamics
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
