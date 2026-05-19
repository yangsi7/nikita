---
title: Slice 218-2 — Decorator + Route Shim + FE Dispatcher + display_name + flag
parent: ../../tasks.md
plan_brief: ~/.claude/plans/immutable-wondering-gray.md
loc_estimate: ~650 (split into 218-2a/2b if overrun)
walkable: display_name slot end-to-end via v2; v1 handles slots 2-11 via R14 handler_handoff
lifecycle: living
---

# Slice 218-2 — Decorator + First Slot (display_name)

Per plan §Slice sequencing PR-218-2 row + §Slice-1 entry checklist.

## Scope (in)

- `nikita/agents/onboarding/v2/decorator_agent.py` — Pydantic AI factory, mirrors `_create_emission_agent` at `nikita/agents/onboarding/conversation_agent.py:377-438` with `output_retries=3` (per spec §18 P3), instructions callable, `@output_validator`, `@lru_cache(maxsize=1)`.
- `nikita/agents/onboarding/v2/prompts.py` — minimal decorator system prompt for display_name + `_sanitize_for_prompt` helper.
- `nikita/agents/onboarding/v2/envelope.py` — add `HandlerHandoffAsk` shape (R14) + extend `AskUnion` discriminator with `handler_handoff` variant.
- `nikita/api/routes/portal_onboarding.py` — flag-gated v2 branch in `/answer` (R1 pattern); session-stamp resolution reads `user.onboarding_profile.state_version`.
- `nikita/api/routes/portal_onboarding.py` — `POST /api/v1/converse/onboarding/retry` per R15.
- `nikita/agents/onboarding/v2/session_helper.py` — `migration_or_init_v2_session(user_id)` reads/stamps `state_version` in JSONB.
- `nikita/config/settings.py` — `wizard_v2_enabled: bool = False` + `is_wizard_v2_enabled_for_user(user_id)` (mirrors `is_unified_pipeline_enabled_for_user`).
- `supabase/migrations/20260511120000_add_onboarding_state_version.sql` — comment-only audit marker (state stamped inside existing `onboarding_profile` JSONB; no DDL needed).
- `portal/src/app/onboarding/v2/DynamicQuestion.tsx` — dispatcher; switches on `envelope.handler` BEFORE `envelope.component` (R14); handles `invalidated` field (R2).
- `portal/src/app/onboarding/v2/text-short.tsx` — text_short shape renderer (`Input` shadcn primitive).
- Tests:
  - `tests/agents/onboarding/v2/test_decorator_agent.py` — mandatory triplet per R3.
  - `tests/api/routes/test_portal_onboarding_v2.py` — flag-gated route + display_name persist + R12 hard-error 500 + R15 retry endpoint.
  - `portal/src/__tests__/app/onboarding/v2/DynamicQuestion.test.tsx` — text_short dispatch + handler_handoff dispatch.

## Scope (out — deferred to later slices)

| Item | Slice |
|---|---|
| Phase-2 research_agent.py (T2.11) | 218-6 |
| cohort_chips.py extension (T2.9, T2.10) | 218-3 |
| Atomic v1 bulldoze (T2.12) | 218-8 |
| age / city / occupation slots | 218-3 |
| voice_or_text / phone / hangouts slots | 218-4 |
| saturday_morning / darkness_level / geek_out_on slots | 218-5 |
| phone-demo wow + Supabase Realtime | 218-7 |
| ROADMAP.md sync | 218-8 (per R9) |

## Tasks (T-2-N.M form per 217-3A.2 precedent)

### T-2-1.1: Failing test — decorator agent mandatory triplet (R3)

`tests/agents/onboarding/v2/test_decorator_agent.py` three classes: `TestCumulativeStateMonotonicity`, `TestCompletionGateTriplet`, `TestWrongComponentRecovery`. Pattern source: `tests/agents/onboarding/test_emission_union.py` first 50 lines.

### T-2-1.2: Failing test — route flag-gating + persist + R12 + R15

`tests/api/routes/test_portal_onboarding_v2.py`:
- `test_flag_off_routes_to_v1`
- `test_flag_on_fresh_session_stamps_v2`
- `test_sticky_session_honors_stamp`
- `test_display_name_persists_to_jsonb`
- `test_decorator_exception_returns_500`
- `test_retry_endpoint_idempotent`
- `test_retry_endpoint_503_after_3_retries`

### T-2-1.3: Failing test — FE dispatcher (R14 + R2)

`portal/src/__tests__/app/onboarding/v2/DynamicQuestion.test.tsx`:
- `renders Input for text_short display_name`
- `dispatches handler_handoff to v1 wizard mount`
- `invalidated list re-renders affected slot`

### T-2-2.1: settings flag + per-user gate

```python
wizard_v2_enabled: bool = Field(default=False, ...)
wizard_v2_rollout_pct: int = Field(default=0, ge=0, le=100, ...)

def is_wizard_v2_enabled_for_user(self, user_id: str) -> bool:
    if not self.wizard_v2_enabled: return False
    if self.wizard_v2_rollout_pct >= 100: return True
    if self.wizard_v2_rollout_pct <= 0: return False
    return (hash(str(user_id)) % 100) < self.wizard_v2_rollout_pct
```

### T-2-2.2: `migration_or_init_v2_session(user_id)`

`nikita/agents/onboarding/v2/session_helper.py`. Reads `users.onboarding_profile` JSONB; stamps `state_version` if absent; returns `(use_v2: bool, profile)`.

### T-2-3.1: `decorator_agent.py`

Mirror `_create_emission_agent` (lines 377-438): `output_type=[ToolOutput(TextShortAsk, name="ask_text_short"), ToolOutput(HandlerHandoffAsk, name="handoff_to_v1")]`, `output_retries=3`, `instructions=inject_v2_per_turn_context`, `@agent.output_validator`, `@lru_cache(maxsize=1)`, `deps_type=V2Deps`.

### T-2-3.2: `prompts.py`

Minimal system prompt for display_name + `_sanitize_for_prompt(text)`.

### T-2-3.3: `envelope.py` extension

```python
class HandlerHandoffAsk(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    component: Literal["handler_handoff"]
    handler: Literal["v1"]
    next_url: str
```

Add `handler: Literal["v2"] = "v2"` optional field to every other shape. Extend `AskUnion`.

### T-2-4.1: /answer v2 branch (R1)

In `/answer` handler BEFORE first persist: `(use_v2, profile) = migration_or_init_v2_session(current_user.id)` → if `use_v2` → `_v2_handler(...)` → R12 500 on exception. Else v1 unchanged.

### T-2-4.2: /retry endpoint (R15)

`POST /api/v1/converse/onboarding/retry` body `{session_id, retry_token}`. Idempotent via `IdempotencyStore`. Counts toward `CostGuard.check_flow_ceiling`. 3rd retry → 503.

### T-2-5.1: FE `DynamicQuestion.tsx` + `text-short.tsx`

Dispatcher switches on `envelope.handler` first, then `envelope.component`. `text-short.tsx` uses shadcn `Input`.

### T-2-6.1: Pre-PR grep gates

Per `.claude/rules/testing.md`: zero-assertion shells, PII leakage, raw cache_key — all empty.

### T-2-7.1: Open PR-218-2

`gh pr create` with Summary + Local tests + Slice scope + Walkable result sections.

## Acceptance criteria (slice-level)

- [ ] Mandatory triplet tests RED → GREEN.
- [ ] Flag-on fresh user → v2 text_short envelope for display_name; JSONB stamped `state_version="v2"`.
- [ ] User types display_name → persists into `user.onboarding_profile.slots.display_name`.
- [ ] Slot 2 reached → `HandlerHandoffAsk(handler="v1")`.
- [ ] Decorator exception → HTTP 500 + `error_code: v2_decorator_failure`.
- [ ] Retry endpoint idempotent + counts toward cost guard + 3rd retry → 503.
- [ ] FE dispatcher mounts `Input` for text_short; falls back to v1 wizard on `handler="v1"`.
- [ ] DAG invalidation: back-edit → `invalidated` non-empty → FE re-renders.
- [ ] Pre-push full suite green (R6).
- [ ] `/qa-review` fresh-context 0 findings (R7).
- [ ] Post-merge subagent smoke probe + scoped live walk green (R8).

## References

- Plan brief: `~/.claude/plans/immutable-wondering-gray.md`
- Parent tasks: `../../tasks.md` (T2.1-T2.14 cluster; this slice owns decorator + display_name subset)
- Pattern source: `nikita/agents/onboarding/conversation_agent.py:377-438`
- Rules: `.claude/rules/{agentic-design-patterns,testing,pr-workflow,parallel-agents}.md`
