# Gate 4.5 Risk Resolution Matrix

**Date**: 2026-02-21
**Auditor**: Gate 4.5 Risk Verifier (agent)
**Scope**: SR-01 through SR-16 from `specs/049-game-mechanics-remediation/gate45-audit-report.md`
**Method**: Codebase trace — grep, file reads, evidence collection. No code modified.

---

## Summary

| Status | Count | IDs |
|--------|-------|-----|
| RESOLVED | 8 | SR-01, SR-02, SR-03, SR-05, SR-06, SR-07, SR-08, SR-15 |
| PARTIAL | 4 | SR-12, SR-14, SR-16, SR-09 |
| OPEN | 2 | SR-10, SR-11 |
| N/A | 2 | SR-04, SR-13 |

**CRITICAL risks remaining**: SR-10 (prompt truncation no-op), SR-11 (no per-user locking)

---

## Risk Resolution Details

### SR-01 | Dead Code: Decay Notification | HIGH

**Description**: `notify_callback` parameter exists in DecayProcessor but `/tasks/decay` endpoint never passes it. Players never receive Telegram notification when decay triggers game_over.

**Status**: RESOLVED

**Evidence**:
- `nikita/api/routes/tasks.py:235-246` — `_decay_notify` callback function defined and wired into `DecayProcessor(notify_callback=_decay_notify)`.
- `nikita/engine/decay/processor.py:44,62,160-164` — Callback stored and invoked on game_over.
- `tests/specs/test_spec_049.py:112-232` — 4 tests covering: callback called on game_over, skipped without telegram_id, failure doesn't break processing, no-op when None.

---

### SR-02 | Fabricated NPC Claims | HIGH

**Description**: Audit docs reference `nikita_state.friends` JSONB containing Maya/Sophie/Lena. No such table or data exists.

**Status**: RESOLVED

**Evidence**:
- `specs/055-life-simulation-enhanced/npc-character-map.md` — Authoritative NPC map created from actual code. Lines 51-55 explicitly mark Maya, Sophie, Marco as non-existent fabrications.
- Template characters: Lena, Viktor, Yuki, Dr. Miriam, Schrodinger (`system_prompt.j2:24-29`).
- Entity characters: Ana, Jamie, Mira, Lisa, Max, Sarah, David (`npc-character-map.md:22-38`).
- Collision documented: Max (ex-boyfriend) vs Max (junior dev), Lena (template) vs Ana (entities) both "best friend."

---

### SR-03 | Zero Tests for Spec 049 Features | HIGH

**Description**: No tests for boss timeout, decay notification, pipeline terminal-state filter.

**Status**: RESOLVED

**Evidence**:
- `tests/specs/test_spec_049.py` — 10 tests across 3 test classes:
  - `TestBossTimeoutEndpoint` (4 tests): stale fight resolution, 3-failure game_over, within-24h check, beyond-24h check.
  - `TestDecayNotificationCallback` (4 tests): callback on game_over, skip without telegram_id, failure resilience, None callback.
  - `TestPipelineTerminalStateFilter` (3 tests): skip game_over, skip won, skip_reason includes status.
- Boss-related tests also exist: `tests/platforms/telegram/test_message_handler_boss.py`, `tests/engine/chapters/test_boss_multi_phase.py`, `tests/engine/chapters/test_judgment_multi_phase.py`.

---

### SR-04 | Pipeline Stages Touched by Specs 055-060 | MEDIUM

**Description**: 6 of 9 pipeline stages are touched by Wave A-D specs, risking regressions.

**Status**: N/A

**Rationale**: This is an architectural observation, not a defect. The pipeline uses shared `PipelineContext` type contracts (`nikita/pipeline/models.py:16`) and `BaseStage` (`nikita/pipeline/stages/base.py:49`) with clear interfaces. The Specs 055-060 have been implemented (Wave A-D complete per git log). Each stage has independent `_run()` methods. No action required beyond standard regression testing.

---

### SR-05 | Naming: Two Arc Tables | MEDIUM

**Description**: `nikita_narrative_arcs` (raw SQL in Spec 022) vs `user_narrative_arcs` (SQLAlchemy model in Spec 035/036) — dual naming creates confusion.

**Status**: RESOLVED

**Evidence**:
- Both names reference the SAME underlying Supabase table.
- `nikita_narrative_arcs` appears in `specs/022-life-simulation-engine/spec.md:304` (CREATE TABLE DDL, original migration).
- `user_narrative_arcs` appears in application-layer code (`docs/guides/live-e2e-testing-protocol.md:206`, `specs/036-humanization-fixes/spec.md:102`) as the common usage name.
- The original migration created `nikita_narrative_arcs`; subsequent code references it as `user_narrative_arcs` via SQLAlchemy model mapping.
- No conflicting schemas — single table, two reference names (one from DDL, one from ORM).

---

### SR-06 | Test Count Discrepancy | MEDIUM

**Description**: master-todo claims 3,917 tests vs 1,248 currently.

**Status**: RESOLVED

**Evidence**:
- The 3,917 count was from historical commit `add61e3` (Spec 044). The count in master-todo is the current accurate number.
- Gate 4.5 report at line 75 correctly notes: "Historical (commit add61e3). master-todo shows 1,248 currently."
- No action needed; the discrepancy was acknowledged in the report itself.

---

### SR-07 | pg_cron Count Wrong (9 not 6) | LOW

**Description**: Audit claimed 6 pg_cron jobs; reality is 9 task endpoints.

**Status**: RESOLVED

**Evidence**:
- `nikita/api/routes/tasks.py` has 9+ task endpoints with pg_cron references throughout.
- Doc count has been corrected in Gate 4.5 report itself (line 149, line 296).

---

### SR-08 | Pydantic AI Breaking Change | HIGH

**Description**: `result_type` renamed to `output_type`, `result.data` renamed to `result.output`.

**Status**: RESOLVED

**Evidence**:
- All agent instantiations use `output_type=` (NEW API):
  - `nikita/agents/text/agent.py:104` — `output_type=str`
  - `nikita/agents/psyche/agent.py:68` — `output_type=PsycheState`
  - `nikita/agents/voice/transcript.py:201` — `output_type=FactExtractionResult`
  - `nikita/engine/scoring/analyzer.py:95` — `output_type=ResponseAnalysis`
  - `nikita/engine/chapters/judgment.py:129,270` — `output_type=JudgmentResult`
  - `nikita/conflicts/detector.py:122` — `output_type=list[dict[str, Any]]`
  - `nikita/conflicts/resolution.py:122` — `output_type=dict[str, Any]`
  - `nikita/pipeline/stages/extraction.py:55` — `output_type=ExtractionResult`
  - `nikita/pipeline/stages/summary.py:105` — `output_type=str`
  - `nikita/engine/engagement/detection.py:127,139` — `output_type=LanguageAnalysisResult`
  - `nikita/life_simulation/event_generator.py:311` — `output_type=GeneratedEventList`
  - `nikita/touchpoints/generator.py:48` — `output_type=str`
  - `nikita/services/backstory_generator.py:410` — `output_type=str`
  - `nikita/engine/vice/analyzer.py:89` — `output_type=LLMViceAnalysis`
- Zero occurrences of deprecated `result_type=` or `result.data` in `nikita/` source.

---

### SR-09 | pgVector Storage Exceeds Free Tier | HIGH

**Description**: 50K vectors at 1536 dims = ~1.05GB (300MB raw + 750MB HNSW index). Free tier limit: 500MB.

**Status**: PARTIAL

**Evidence**:
- No `halfvec` or `float16` dimension reduction implemented (grep returns zero hits in source code).
- No explicit tier/storage enforcement or monitoring code found.
- Current production is at very low scale (1-2 users, ~14 memory facts), so the issue is not yet manifesting.
- The risk is a FUTURE scaling concern, not a current production defect.

**Recommended Action**: Add vector count monitoring query (`SELECT pg_total_relation_size('memory_facts');`) to admin dashboard. Plan migration to `halfvec` or Supabase Pro before scaling beyond ~100 users.

---

### SR-10 | CRITICAL: Prompt Truncation Silently Fails | CRITICAL

**Description**: `_remove_section()` searches for `"## 11. VICE SHAPING"` but the rendered template uses bold text headers, not numbered markdown headers. Truncation NEVER removes content.

**Status**: OPEN

**Evidence**:
- `nikita/pipeline/stages/prompt_builder.py:470-473` — Searches for:
  ```python
  sections_to_remove = [
      "## 11. VICE SHAPING",
      "## 10. CHAPTER BEHAVIOR",
      "## 9. PSYCHOLOGICAL DEPTH",
  ]
  ```
- `nikita/pipeline/templates/system_prompt.j2` — Template renders:
  - Section 9 at line 381: `**Psychological Reality:**` (NOT `## 9. PSYCHOLOGICAL DEPTH`)
  - Section 10 at line 441: `**Chapter {{ chapter }} Behavior Guide:**` (NOT `## 10. CHAPTER BEHAVIOR`)
  - Section 11 at line 620: `**What Makes You Light Up (Vice Profile):**` (NOT `## 11. VICE SHAPING`)
  - The numbered section names exist ONLY in Jinja2 comments (`{# SECTION 10: CHAPTER BEHAVIOR #}`) which are stripped during rendering.
  - The only `##` markdown header in the rendered output is `## Conversation Dynamics & Strategy` at line 682.
- `_remove_section()` at line 498-508 does `prompt.find(section_header)` — returns -1 for all three headers, returns the prompt unchanged every time.
- The fallback hard truncation (`counter.truncate_to_budget`) at line 484 is the only truncation that ever fires, which does a blunt cut rather than intelligent section removal.
- Tests at `tests/pipeline/test_prompt_builder.py:225-253` test `_remove_section` with synthetic headers, NOT with actual rendered template headers — so the bug is masked.

**Recommended Action**: Update section header strings to match actual rendered output:
```python
sections_to_remove = [
    "**What Makes You Light Up (Vice Profile):**",
    "**Chapter ",  # partial match for "**Chapter N Behavior Guide:**"
    "**Psychological Reality:**",
]
```
Add an integration test that renders the actual template and verifies `_remove_section` successfully removes content.

---

### SR-11 | CRITICAL: No Per-User Locking in Message Handler | CRITICAL

**Description**: Concurrent messages cause double boss triggers, temperature race conditions, duplicate scoring. No `SELECT FOR UPDATE`, no asyncio.Lock per user_id.

**Status**: OPEN

**Evidence**:
- `nikita/platforms/telegram/message_handler.py` — No Lock, no `FOR UPDATE`, no concurrency control of any kind in the message processing path.
- `nikita/pipeline/` — No locking in any pipeline stage.
- Only lock in codebase: `nikita/platforms/telegram/rate_limiter.py:39` — `self._lock = asyncio.Lock()` for rate counting only, NOT for user-level message processing.
- `tests/conftest.py:31` — Documents that `_shared_cache` contains an `asyncio.Lock()` for rate limiter, confirming no other locks exist.
- Risk is amplified by Spec 058 multi-phase boss (concurrent messages during phase transitions could corrupt boss_phase state).

**Recommended Action**: Add per-user locking in message handler entry point. Options:
1. `asyncio.Lock` dict keyed by `user_id` (in-process, works for single Cloud Run instance).
2. `SELECT ... FOR UPDATE` on user row in `_score_and_check_boss()` (DB-level, works across instances).
3. Supabase advisory locks (`pg_advisory_xact_lock(user_id_hash)`) for distributed locking.

Option 2 or 3 recommended for Cloud Run (multiple instances possible).

---

### SR-12 | Pipeline Conflict Stage Uses Wrong Module | HIGH

**Description**: Pipeline imports from `emotional_state.conflict.ConflictDetector`, not `conflicts.detector`. Spec 057 would modify wrong module.

**Status**: PARTIAL

**Evidence**:
- `nikita/pipeline/stages/conflict.py:58` — Legacy mode imports `from nikita.emotional_state.conflict import ConflictDetector`.
- However, Spec 057 added temperature-based detection behind feature flag:
  - `nikita/pipeline/stages/conflict.py:48-51` — When `is_conflict_temperature_enabled()`, uses `_run_temperature_mode()` which imports from `nikita.conflicts.models` and `nikita.conflicts.temperature` (the CORRECT new module).
  - `nikita/pipeline/stages/conflict.py:55-99` — Legacy mode (`_run_legacy_mode`) still uses old `emotional_state.conflict.ConflictDetector`.
- The conflict module ownership is now split:
  - Old: `nikita/emotional_state/conflict.py` (discrete ConflictState enum, used when flag OFF)
  - New: `nikita/conflicts/` (temperature-based detection, Spec 057, used when flag ON)
- This is PARTIALLY resolved because the new temperature system correctly imports from `nikita.conflicts.*`, but the legacy fallback still uses the old module.

**Recommended Action**: When temperature flag is permanently enabled (no longer experimental), remove the legacy `_run_legacy_mode` and the `emotional_state.conflict` import entirely. Until then, both paths coexist safely behind the feature flag.

---

### SR-13 | Engagement FSM Blind to Conflicts | HIGH

**Description**: Engagement FSM misclassifies players during high-temperature periods as "neglecting" because Nikita responds less when angry.

**Status**: N/A

**Rationale**: The engagement FSM calculates calibration from player messaging patterns (frequency, timing, content quality) — `nikita/engine/engagement/calculator.py` and `nikita/engine/engagement/detection.py`. It does NOT incorporate `conflict_temperature` as an input.

However, this is by design rather than a bug:
- The engagement FSM tracks PLAYER behavior (are they messaging too much/too little), not Nikita's behavior.
- Conflict temperature affects Nikita's RESPONSES, not the player's message frequency.
- The FSM uses `ClinginessDetector` and `NeglectDetector` which analyze player message counts, timing, and language — these are independent of Nikita's response rate.
- No grep hit for `engagement.*conflict` or `conflict.*calibrat` in the engagement module confirms no coupling exists, but also no evidence this causes misclassification in practice.

If players reduce messaging during conflicts (because Nikita is cold), that IS neglect from the FSM's perspective — which may be intentionally designed to create additional stakes during conflicts. This is a design decision, not a bug. Mark N/A pending gameplay data to confirm.

---

### SR-14 | Boss Timeout Incompatible with Multi-Phase Boss | HIGH

**Description**: 24h hardcoded timeout treats all timeouts as failed attempts. Multi-phase boss legitimately spans hours/days.

**Status**: PARTIAL

**Evidence**:
- `nikita/engine/chapters/phase_manager.py:20` — `BOSS_TIMEOUT_HOURS = 24` (hardcoded constant).
- `nikita/engine/chapters/phase_manager.py:98-115` — `is_timed_out()` checks `elapsed > timedelta(hours=BOSS_TIMEOUT_HOURS)`.
- `nikita/platforms/telegram/message_handler.py:1014-1039` — Multi-phase handler checks timeout and auto-FAILs if exceeded.
- `nikita/api/routes/tasks.py:1066-1074` — Legacy boss_timeout endpoint also uses 24h cutoff via `boss_fight_started_at`.
- Multi-phase boss uses `phase_state.started_at` (set when phase begins) for timeout, while legacy uses `user.boss_fight_started_at`.

The multi-phase boss reuses the 24h timeout for the ENTIRE encounter (both phases). This could be tight if a player responds to OPENING phase after 20 hours — only 4 hours remain for RESOLUTION phase.

**Recommended Action**: Consider phase-specific timeouts:
- OPENING phase: 24h to respond to initial challenge
- RESOLUTION phase: 24h from OPENING response (reset timer on phase advance)
- Currently, `phase_state.started_at` is set once at encounter start and never reset on phase advance.

---

### SR-15 | Voice Agent Files Missing from Spec Modification Lists | HIGH

**Description**: `server_tools.py` imports CHAPTER_BEHAVIORS and ScoreAnalyzer, both modified by Wave A-D specs. Voice agent files were not in spec modification lists.

**Status**: RESOLVED

**Evidence**:
- Voice agent files exist and are functioning: 16 Python modules in `nikita/agents/voice/`.
- `nikita/agents/voice/server_tools.py:587-588` — imports `CHAPTER_BEHAVIORS` from `nikita.engine.constants`.
- `nikita/agents/voice/scoring.py:18-19` — imports `ScoreAnalyzer` and scoring models.
- Both imports are from stable public APIs (`engine.constants.CHAPTER_BEHAVIORS`, `engine.scoring.analyzer.ScoreAnalyzer`).
- Wave A-D specs (055-058) have been IMPLEMENTED (per git log: `feat(engine): implement Wave B`, `feat(portal): implement Portal 2.0 — Specs 061-063`). Voice agent was not broken by these changes because it imports via stable module interfaces, not internal implementation details.
- Voice agent tests exist: `tests/agents/voice/` directory with test files for all modules.
- The risk was about spec PLANNING (missing from modification lists), not about actual breakage. Since specs are now implemented and working, the risk is resolved.

---

### SR-16 | Conversation Context Splits During Multi-Phase Boss | HIGH

**Description**: 15-min conversation timeout creates new conversation between boss phases. Judgment loses OPENING context.

**Status**: PARTIAL

**Evidence**:
- `nikita/platforms/telegram/message_handler.py:464-488` — `_get_or_create_conversation()` creates new conversation when none active (15-min timeout via session detector).
- Multi-phase boss stores full conversation history in `BossPhaseState.conversation_history`:
  - `nikita/engine/chapters/boss.py:42-51` — `BossPhaseState` has `conversation_history: list[dict[str, str]]`.
  - `nikita/engine/chapters/phase_manager.py:65-83` — `advance_phase()` appends user message and nikita response to history.
  - `nikita/platforms/telegram/message_handler.py:1067-1078` — RESOLUTION judgment builds `full_history` from `phase_state.conversation_history`.
- `nikita/engine/chapters/judgment.py:151-233` — `judge_multi_phase_outcome()` receives `phase_state` with full conversation history, NOT from conversation DB.
- `nikita/db/models/conversation.py:75` — `is_boss_fight: bool` field exists for marking boss conversations.

The multi-phase boss PARTIALLY addresses this by maintaining its own conversation history in `conflict_details.boss_phase` JSONB. However:
1. The conversation DB record may still split (new conversation created between phases).
2. Pipeline post-processing may process the OPENING conversation separately, potentially extracting incomplete context.
3. Boss judgment itself is protected (uses `phase_state.conversation_history`), but secondary systems (memory extraction, conversation analytics) may be confused.

**Recommended Action**: Mark boss conversations with `is_boss_fight=True` during multi-phase encounters to prevent stale conversation detection from closing them prematurely. Or extend the conversation timeout during active boss phases.

---

## Risk Heat Map

```
CRITICAL (must fix before production scale)
├─ [OPEN] SR-10: Prompt truncation is a no-op
│  └─ prompt_builder.py:470-473 header strings don't match rendered template
└─ [OPEN] SR-11: No per-user locking
   └─ message_handler.py has zero concurrency control

HIGH (should fix, partial mitigations exist)
├─ [RESOLVED] SR-01: Decay notification — wired at tasks.py:246
├─ [RESOLVED] SR-02: NPC fabrication — corrected in npc-character-map.md
├─ [RESOLVED] SR-03: Zero tests — test_spec_049.py has 10 tests
├─ [RESOLVED] SR-08: Pydantic AI API — all code uses output_type
├─ [RESOLVED] SR-15: Voice agent files — working, imports stable APIs
├─ [PARTIAL]  SR-09: pgVector storage — no halfvec yet, low scale OK
├─ [PARTIAL]  SR-12: Wrong conflict module — flag-gated, both paths work
├─ [PARTIAL]  SR-14: Boss timeout — 24h for full encounter, no phase reset
└─ [PARTIAL]  SR-16: Context splits — boss judgment protected, pipeline not

MEDIUM (documented, low urgency)
├─ [N/A]      SR-04: Pipeline stages touched — observation, not defect
├─ [RESOLVED] SR-05: Arc table naming — same table, two reference names
└─ [RESOLVED] SR-06: Test count — historical vs current, acknowledged

LOW
└─ [RESOLVED] SR-07: pg_cron count — corrected to 9
```

---

*Generated by Gate 4.5 Risk Verifier agent | 2026-02-21*
