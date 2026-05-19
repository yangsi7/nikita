# Plan — Spec 114: Vice Pipeline Activation

## Story 1: ViceStage + feature flag (AC-001–AC-006)

**Files**:
- `nikita/config/settings.py` — add flag
- `nikita/pipeline/stages/vice.py` — new stage
- `nikita/pipeline/orchestrator.py` — insert stage; stages_total 10→11
- `nikita/pipeline/models.py` — stages_total default 10→11
- `nikita/observability/types.py` — add VICE_COMPLETE + STAGE_EVENT_TYPES entry
- `nikita/observability/snapshots.py` — add STAGE_FIELDS entry
- `tests/pipeline/stages/test_vice_stage.py`
- `tests/config/test_vice_setting.py`

### T1 — RED tests

Write failing tests in `tests/pipeline/stages/test_vice_stage.py`:

- `test_vice_stage_position` — inspect `PipelineOrchestrator.STAGE_DEFINITIONS` class var directly (no instance needed):
  ```python
  names = [d[0] for d in PipelineOrchestrator.STAGE_DEFINITIONS]
  idx = names.index("vice")
  assert names[idx - 1] == "emotional"
  assert names[idx + 1] == "game_state"
  assert PipelineOrchestrator.STAGE_DEFINITIONS[idx][2] is False  # is_critical
  ```
- `test_vice_stage_calls_service` — ViceService.process_conversation called with last user+nikita messages AND correct `chapter` kwarg; mock `nikita.engine.vice.service.ViceService` with `AsyncMock` for `process_conversation`
- `test_vice_stage_flag_disabled` — ViceService not called when vice_pipeline_enabled=False
- `test_vice_stage_failure_non_fatal` — set `stage._run = AsyncMock(side_effect=RuntimeError("boom"))`, call `await stage.execute(ctx)` (not `_run` directly), assert `result.success is False`; non-fatal contract is in `BaseStage.execute()`
- `test_vice_stage_insufficient_messages` — single-message conversation → ViceService not called

Add `TestExtractLastExchange` class for `_extract_last_exchange()` pure helper:
- text format (`role:"user"/"nikita"` + `content` key) → returns pair
- empty list → (None, None)
- single message only → (None, None)
- multiple exchanges → returns LAST pair
- non-consecutive roles (user, user, nikita) → returns pair where prev is user
- messages with empty content → skipped

Write in `tests/config/test_vice_setting.py`:
- `test_vice_flag_setting_default` — `Settings().vice_pipeline_enabled == False`; provide required kwargs from `tests/pipeline/test_feature_flags.py` pattern (supabase_url, supabase_key, etc.)

### T2 — GREEN implementation

**1. `nikita/config/settings.py`** — add field after existing flags:
```python
vice_pipeline_enabled: bool = Field(default=False, description="Enable ViceStage in pipeline (GE-006). Opt-in: set VICE_PIPELINE_ENABLED=true. Rollback: VICE_PIPELINE_ENABLED=false.")
```

**2. `nikita/pipeline/stages/vice.py`** — new stage:
```python
"""Vice profile update stage (Spec 114, GE-006).

Non-critical: analyzes last conversation exchange, updates vice_preferences.
Skipped when vice_pipeline_enabled=False (safe rollout gate).
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Any
import structlog
from nikita.pipeline.stages.base import BaseStage

if TYPE_CHECKING:
    from nikita.pipeline.models import PipelineContext
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


class ViceStage(BaseStage):
    """Analyze last exchange for vice signals and update vice_preferences.

    Non-critical — failure does not stop the pipeline.
    Gated by settings.vice_pipeline_enabled (default False).
    """

    name = "vice"
    is_critical = False
    timeout_seconds = 45.0

    def __init__(self, session: AsyncSession = None, **kwargs) -> None:
        super().__init__(session=session, **kwargs)

    async def _run(self, ctx: PipelineContext) -> dict | None:
        """Analyze last user+nikita exchange for vice signals."""
        from nikita.config.settings import get_settings
        settings = get_settings()
        if not settings.vice_pipeline_enabled:
            return {"skipped": True, "reason": "vice_pipeline_disabled"}

        # Extract last (user, nikita) exchange from conversation messages
        messages = []
        if ctx.conversation is not None and hasattr(ctx.conversation, "messages"):
            messages = ctx.conversation.messages or []

        user_message, nikita_response = _extract_last_exchange(messages)
        if not user_message or not nikita_response:
            logger.info("[VICE] Insufficient messages for analysis, skipping")
            return {"skipped": True, "reason": "insufficient_messages"}

        from nikita.engine.vice.service import ViceService

        # ViceService() takes no args — ViceScorer manages its own session internally
        vice_service = ViceService()
        result = await vice_service.process_conversation(
            user_id=ctx.user_id,
            user_message=user_message,
            nikita_message=nikita_response,   # NOTE: parameter is nikita_message, not nikita_response
            conversation_id=ctx.conversation_id,
            chapter=ctx.chapter,
        )
        logger.info(
            "[VICE] Vice analysis: discovered=%d updated=%d",
            result.get("discovered", 0),
            result.get("updated", 0),
        )
        return result


def _extract_last_exchange(messages: list[dict[str, Any]]) -> tuple[str | None, str | None]:
    """Return the last (user_message, nikita_response) pair from messages.

    Iterates in reverse to find a user+nikita consecutive pair.
    Returns (None, None) if no such pair exists.
    """
    i = len(messages) - 1
    while i > 0:
        curr = messages[i]
        prev = messages[i - 1]
        curr_role = curr.get("role", "")
        prev_role = prev.get("role", "")
        if curr_role in ("nikita", "agent") and prev_role == "user":
            user_content = prev.get("content") or prev.get("message", "")
            nikita_content = curr.get("content") or curr.get("message", "")
            if user_content and nikita_content:
                return str(user_content), str(nikita_content)
        i -= 1
    return None, None
```

**3. `nikita/pipeline/orchestrator.py`** — insert after EmotionalStage AND update stages_total:
```python
("emotional", "nikita.pipeline.stages.emotional.EmotionalStage", False),
("vice", "nikita.pipeline.stages.vice.ViceStage", False),  # Spec 114 GE-006
("game_state", "nikita.pipeline.stages.game_state.GameStateStage", False),
```
Also change `stages_total=10` → `stages_total=11` at `orchestrator.py:184`.

**4. `nikita/pipeline/models.py`** — update default:
```python
stages_total: int = 11  # was 10; +1 for ViceStage (Spec 114)
```

**5. `nikita/observability/types.py`** — add VICE_COMPLETE constant and register it:
```python
VICE_COMPLETE = "vice.complete"

# In STAGE_EVENT_TYPES dict:
"vice": VICE_COMPLETE,

# In ALL_EVENT_TYPES set:
VICE_COMPLETE,
```

**6. `nikita/observability/snapshots.py`** — add STAGE_FIELDS entry (stage writes to DB, not ctx):
```python
"vice": [],  # ViceStage writes to user_vice_preferences DB table, not PipelineContext fields
```

### T3 — Run all tests green

```bash
pytest tests/pipeline/stages/test_vice_stage.py tests/config/test_vice_setting.py -v
pytest tests/pipeline/ -q  # regression check
```

---

## Commit Sequence

1. `test(pipeline): Spec 114 — ViceStage + flag tests (RED)`
2. `feat(pipeline): Spec 114 — ViceStage + vice_pipeline_enabled flag (GREEN)`
