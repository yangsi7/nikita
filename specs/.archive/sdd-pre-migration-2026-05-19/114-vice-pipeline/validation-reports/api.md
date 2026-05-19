## API Validation Report

**Spec:** specs/114-vice-pipeline/spec.md
**Status:** FAIL
**Timestamp:** 2026-03-14T12:00:00Z

### Summary
- CRITICAL: 0
- HIGH: 3
- MEDIUM: 3
- LOW: 1

### Findings

| Severity | Category | Issue | Location | Recommendation |
|----------|----------|-------|----------|----------------|
| HIGH | Request Schema | Parameter name mismatch: spec says `nikita_response` but `ViceService.process_conversation()` takes `nikita_message` | spec.md:40, plan.md:89 vs service.py:146 | Change spec FR-002 and plan line 89 to use `nikita_message=nikita_response` (kwarg rename). Or change plan's local variable from `nikita_response` to `nikita_message`. Failing to align causes `TypeError: unexpected keyword argument 'nikita_response'` at runtime. |
| HIGH | Request Schema | `ctx.raw_messages` referenced in spec FR-002 does not exist on `PipelineContext` | spec.md:39, models.py (no `raw_messages` field) | The plan correctly uses `ctx.conversation.messages` (plan.md:73). Update spec FR-002 to match: "Extract the last user message + last Nikita response from `ctx.conversation.messages`". |
| HIGH | Response Schema | `stages_total` hardcoded to `10` in `PipelineResult` default and terminal-state early return. Adding ViceStage makes it 11 stages. | orchestrator.py:184, models.py:158 | Update `stages_total: int = 10` default to `11` in models.py:158. Update hardcoded `stages_total=10` in the terminal-state early return at orchestrator.py:184. Alternatively, compute dynamically from `len(STAGE_DEFINITIONS)`. |
| MEDIUM | Observability | `STAGE_EVENT_TYPES` dict in `observability/types.py` has no entry for `"vice"`. Orchestrator silently skips observability emit when stage name is missing from this map. | types.py:21-32 | Add `VICE_COMPLETE = "vice.complete"` constant and `"vice": VICE_COMPLETE` entry to `STAGE_EVENT_TYPES`. Add to `ALL_EVENT_TYPES` set. Without this, vice stage runs produce zero observability events. |
| MEDIUM | Observability | `STAGE_FIELDS` dict in `snapshots.py` has no entry for `"vice"`. `snapshot_ctx()` returns `{}` for unknown stages; `compute_delta()` falls back to generic empty-fields logic. | snapshots.py:17-60 | Add `"vice": ["vices"]` to `STAGE_FIELDS` (the stage updates `vice_preferences` in DB, but `ctx.vices` is the closest observable field). Optionally add a `_vice_delta` builder for richer event payloads (e.g., discovered/updated counts from stage result dict). |
| MEDIUM | Env Var Docs | `VICE_PIPELINE_ENABLED` env var is not documented in `docs/deployment.md` or any operational runbook. Other feature flags have inline rollback instructions in their `description` field. | spec.md:44, settings.py (new field) | Add rollback description to the Field: `"Enable ViceStage in pipeline (GE-006). Opt-in: VICE_PIPELINE_ENABLED=true. Rollback: VICE_PIPELINE_ENABLED=false"`. Add to deployment docs alongside existing feature flag env vars. |
| LOW | Naming | Feature flag naming is inconsistent with dominant pattern. Existing flags use `{feature}_enabled` (e.g., `psyche_agent_enabled`, `observability_enabled`, `skip_rates_enabled`). Spec proposes `vice_pipeline_enabled` which follows the same pattern. Acceptable, but note that the convenience function pattern (`is_*_enabled()` in `chapters/__init__.py`) is not specified. | settings.py:172-222 | No action required. `vice_pipeline_enabled` follows the `{scope}_enabled` convention. A convenience function is optional since the flag is only checked in one place (ViceStage._run). |

### API Inventory

No new API routes or endpoints are introduced by this spec. ViceStage is an internal pipeline stage, not an HTTP endpoint.

| Method | Endpoint | Purpose | Auth | Request | Response |
|--------|----------|---------|------|---------|----------|
| N/A | N/A | Internal pipeline stage only | N/A | N/A | N/A |

### Server Actions

N/A -- Python backend, no Next.js server actions.

### Internal Call Signatures

| Caller | Callee | Parameters | Issue |
|--------|--------|------------|-------|
| ViceStage._run() | ViceService.process_conversation() | user_id, user_message, **nikita_response**, conversation_id, chapter | **HIGH**: actual param name is `nikita_message` (service.py:146), not `nikita_response` |

**Actual signature** (service.py:142-148):
```python
async def process_conversation(
    self,
    user_id: UUID,
    user_message: str,
    nikita_message: str,       # <-- NOT nikita_response
    conversation_id: UUID,
    chapter: int = 3,
) -> dict:
```

**Plan calls it as** (plan.md:86-92):
```python
result = await vice_service.process_conversation(
    user_id=ctx.user_id,
    user_message=user_message,
    nikita_response=nikita_response,  # <-- TypeError: unexpected keyword argument
    conversation_id=ctx.conversation_id,
    chapter=ctx.chapter,
)
```

**Fix**: Change plan.md line 89 to `nikita_message=nikita_response,`

### Affected Modules Checklist

| Module | Change Needed | Documented in Spec | Gap |
|--------|--------------|-------------------|-----|
| settings.py | Add `vice_pipeline_enabled` field | Yes (spec.md:66) | None |
| orchestrator.py STAGE_DEFINITIONS | Insert vice tuple at position 6 | Yes (spec.md:67) | None |
| orchestrator.py terminal return | Update stages_total 10 -> 11 | No | HIGH |
| models.py PipelineResult | Update stages_total default 10 -> 11 | No | HIGH |
| observability/types.py | Add VICE_COMPLETE event type | No | MEDIUM |
| observability/snapshots.py | Add "vice" to STAGE_FIELDS | No | MEDIUM |

### Env Var Naming Consistency Check

| Existing Flag | Env Var (auto-derived) | Default |
|--------------|----------------------|---------|
| `enable_post_processing_pipeline` | ENABLE_POST_PROCESSING_PIPELINE | True |
| `life_sim_enhanced` | LIFE_SIM_ENHANCED | True |
| `conflict_temperature_enabled` | CONFLICT_TEMPERATURE_ENABLED | True |
| `skip_rates_enabled` | SKIP_RATES_ENABLED | True |
| `psyche_agent_enabled` | PSYCHE_AGENT_ENABLED | True |
| `multi_phase_boss_enabled` | MULTI_PHASE_BOSS_ENABLED | True |
| `observability_enabled` | OBSERVABILITY_ENABLED | True |
| `unified_pipeline_enabled` | UNIFIED_PIPELINE_ENABLED | True |
| **`vice_pipeline_enabled`** (new) | **VICE_PIPELINE_ENABLED** | **False** |

Naming is consistent. Pydantic Settings with `case_sensitive=False` auto-maps `vice_pipeline_enabled` to env var `VICE_PIPELINE_ENABLED`. Default `False` is correct for safe rollout (matches Feature Flag Validation Pattern in agent memory).

### Recommendations

1. **HIGH -- Fix parameter name mismatch**: In plan.md line 89, change `nikita_response=nikita_response` to `nikita_message=nikita_response`. In spec.md line 40, change "nikita_response" to "nikita_message" to match the actual `ViceService.process_conversation()` signature. This is a runtime TypeError if implemented as written.

2. **HIGH -- Fix stale ctx field reference**: In spec.md line 39, change `ctx.raw_messages` to `ctx.conversation.messages`. The plan already uses the correct field (plan.md:73), but the spec is the source of truth and should be accurate.

3. **HIGH -- Update stages_total**: Add to spec's "Files to modify" section that `models.py:158` default `stages_total=10` must become `11`, and `orchestrator.py:184` hardcoded `stages_total=10` must become `11`. Alternatively, recommend computing dynamically: `stages_total=len(self.STAGE_DEFINITIONS)`.

4. **MEDIUM -- Add observability integration**: Add `observability/types.py` and `observability/snapshots.py` to the spec's "Files to modify" list. Without this, the vice stage silently produces no observability events, breaking the Spec 110 contract that all stages emit completion events.

5. **MEDIUM -- Add rollback description to Field**: Match the pattern used by other flags (e.g., `psyche_agent_enabled` at settings.py:199) by including `"Rollback: VICE_PIPELINE_ENABLED=false"` in the field description.
