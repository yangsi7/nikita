---
feature: 215-heartbeat-engine
created: 2026-04-17
status: Draft
priority: P1
technology_agnostic: true
constitutional_compliance:
  article_iv: specification_first
---

# Feature Specification: Heartbeat Engine

**IMPORTANT**: Technology-agnostic. Implementation details (Hawkes math, pg_cron, asyncpg JSONB, von Mises, FastAPI endpoints) live in plan.md. Spec describes WHAT and WHY only.

---

## Summary

Today, the AI girlfriend Nikita "exists" only while a player is messaging her. The pipeline runs reactively per-message, and her "what I have been doing" backstory is fabricated post-hoc when the player breaks a silence. This breaks immersion: players sense the absence between conversations and notice the inconsistency of fabricated histories.

The Heartbeat Engine gives Nikita a continuous, time-varying internal life so that she feels present even when the player is silent: she has a planned day (work, hobbies, social blocks, sleep), her thoughts about the player follow that day's rhythm, and the timing of her proactive outreach reflects what she is doing. When the player reappears, what she "has been up to" is genuinely what she was simulated to be doing, not a confabulation.

**Problem Statement**: Nikita has no autonomous behavior. Without a heartbeat she only thinks/acts at conversation time. Players notice the absence and the post-hoc fabrications that try to paper over it.

**Value Proposition**: Players experience Nikita as a person with her own life. Proactive outreach, response timing, and silence patterns become probabilistically realistic and personalized to each player. Game retention and immersion improve. The system gains a measurable, validatable simulation surface (offline model versus live production parity) that supports principled tuning instead of vibes.

### CoD^Σ Overview

```
Player ↔ Nikita_present ⊕ Nikita_living
            ↓                ↓
        Reactive          Proactive (NEW)
            ↓                ↓
        Conversation     Heartbeat ≫ Plan ≫ Touchpoint

Requirements: R := {FR_i} ⊕ {NFR_j}
Phasing: P1 (MVE) ≪ P2 (self-scheduling) ≪ P3 (Bayesian)
Stories: US-1..US-4 ⇒ P1 | US-5..US-7 ⇒ P2 | US-8..US-9 ⇒ P3
```

---

## Functional Requirements

**Current [NEEDS CLARIFICATION] Count**: 0 / 3

### FR-001: Continuous internal life simulation
System MUST simulate Nikita's internal state (planned activity, time-of-day mood) on a continuous 24-hour cycle, independent of whether the player is active.
**Rationale**: Without continuous simulation, the player perceives Nikita as a request/response chatbot, not a person.
**Priority**: Must Have

### FR-002: Daily plan generation
System MUST generate, once per day per active player, a structured day-arc describing what Nikita is doing across the day, including both a structured form (for execution) and a narrative form (for prompt context).
**Rationale**: Both forms are needed: structured for the engine to act on; narrative for the text agent to reference when speaking to the player.
**Priority**: Must Have (P1; default OD2: BOTH structured + narrative)

### FR-003: Activity-distribution probability never zero
System MUST represent Nikita's "what she is doing right now" as a probability distribution over activities at every clock instant, with NO activity at exactly zero probability anywhere in the 24-hour cycle.
**Rationale**: Realistic behavior allows for surprise (Nikita texts at an unusual hour because of an unusual circumstance). Hard zeros produce robotic schedules.
**Priority**: Must Have

### FR-004: Smooth time-varying parameters
System MUST treat all activity-related parameters (peak times, breadth, weights) as smooth functions of clock time. No hard step-changes between adjacent minutes.
**Rationale**: Discontinuities produce visible "she suddenly switched at 9:00 AM" behavior, breaking immersion.
**Priority**: Must Have

### FR-005: Safety-net heartbeat tick
System MUST guarantee at least one heartbeat per active player per hour, regardless of any optimistic self-scheduling. If self-scheduling fails or stalls, the safety-net tick recovers state.
**Rationale**: A failure in self-scheduling logic must NOT take Nikita offline silently. The safety net is the durability contract.
**Priority**: Must Have

### FR-006: Plan-driven proactive touchpoint
System MUST allow the heartbeat to schedule a proactive outreach (touchpoint) whose content references at least one element of the current day's plan.
**Rationale**: Proactive outreach is the user-visible payoff of the heartbeat. Without referencing the plan, outreach feels generic and confabulated.
**Priority**: Must Have

### FR-007: Boundaries between heartbeat and dispatcher
System MUST keep the heartbeat (deciding "now is a moment when something might happen") cleanly separated from the touchpoint dispatcher (deciding "send a message and how"). Heartbeat MUST NOT bypass the dispatcher's deduplication and rate-limit guarantees.
**Rationale**: A direct write would cause duplicate-fire and rate-limit violations. The dispatcher is already the single source of truth for outbound messages.
**Priority**: Must Have

### FR-008: Game-state respect
System MUST NOT generate heartbeats for players whose game has ended (state: game_over) and MUST NOT generate heartbeats for players whose game is `won` (per OD4 default).
**Rationale**: A game-over player should not be contacted. A won-state player has graduated; ongoing heartbeats would feel intrusive.
**Priority**: Must Have

### FR-009: Idempotency on cron double-fire
System MUST be safe against duplicate heartbeat invocations within a short window. A second invocation within the window MUST report "skipped" and produce zero side effects.
**Rationale**: Background cron infrastructure has a documented double-fire pattern. Without idempotency, every double-fire produces a duplicate touchpoint.
**Priority**: Must Have

### FR-010: Concurrent-update safety
System MUST serialize concurrent heartbeat operations targeting the same player so that two simultaneous ticks cannot corrupt or duplicate the player's heartbeat state.
**Rationale**: User messages, voice events, admin force-actions, and the safety-net cron can all target the same player at the same instant. Without serialization, state is unreliable.
**Priority**: Must Have

### FR-011: Replan on player interaction
System MUST treat a player message as an event that wakes Nikita immediately and reassesses her forward schedule. Reassessment includes both the respond-now-versus-later micro-decision AND cancellation of pending future heartbeats that the new state invalidates.
**Rationale**: A player message is the single most important signal. The system MUST respond by recomputing forward state, not by ignoring it until the next safety-net tick.
**Priority**: Must Have

### FR-012: Replan trigger catalogue
System MUST treat the following as forward-schedule reassessment triggers: player message, chapter advance, boss encounter triggered, game-over (any cause), engagement-state major transition, admin force-action, stale-boss resolution.
**Rationale**: Each of these changes Nikita's internal state in a way that invalidates her current planned forward schedule.
**Priority**: Must Have

### FR-013: Catch-up policy on stalls
System MUST drop heartbeats whose scheduled time is far in the past on resume after a stall, instead of replaying every missed tick. Drop-count MUST be observable.
**Rationale**: Replaying 30 minutes of stacked heartbeats produces a midnight burst of stale-context outreach. Drop is the safe behavior.
**Priority**: Must Have

### FR-014: Cost circuit breaker
System MUST enforce a daily aggregate language-model cost ceiling for heartbeat operations. When the ceiling is reached, heartbeat operations MUST gracefully degrade by:
(a) returning HTTP 503 Service Unavailable with `Retry-After` header pointing to the next reset boundary (midnight UTC) so cron + alerting detect via status code without parsing body JSON,
(b) emitting a structured alert (log entry tagged `circuit_breaker_engaged` + counter increment),
(c) persisting cost-ledger state in a durable store (NOT in-memory; Cloud Run scale-to-zero would lose it).
**Rationale**: At scale, daily-arc generation plus reflection per active player has non-trivial language-model cost. A runaway loop must NOT empty the budget silently.
**Priority**: Must Have

### FR-015: Privacy of personalization state
System MUST treat per-player simulation parameters (activity-distribution fingerprints, learned posteriors, daily-arc JSON, narrative text, LLM prompt body) as personally-identifying. They MUST be excluded from log payloads, error reports, and any non-admin surface. Error responses MUST use a structured envelope `{"error": "<code>", "detail": "<redacted>"}` and MUST NOT include `str(exception)` verbatim.
**Rationale**: Per-user circadian fingerprints + arc content + prompt bodies are a high-reidentification-risk surface. They must NEVER appear in logs OR in error responses (raw `str(e)` from FastAPI exception handlers is a documented leak vector).
**Priority**: Must Have

### FR-016: Live versus offline parity validator
System MUST provide a parity validator that compares production-observed heartbeat statistics against the offline simulation model and reports per-chapter divergence. The validator MUST run on a schedule and fail loudly if divergence exceeds threshold.
**Rationale**: Without parity validation, the offline model and the production system can drift apart silently. The validator is how we know the live system actually does what we designed.
**Priority**: Must Have

### FR-017: Self-scheduling (P2)
System SHOULD (Phase 2) sample Nikita's next scheduled wake time from a continuous activity-aware intensity, replacing pure hourly safety-net ticks with finer self-scheduled ticks layered on top.
**Rationale**: Hourly is the safety floor; richer outreach realism comes from finer self-scheduled ticks.
**Priority**: Should Have (Phase 2)

### FR-018: Per-player Bayesian personalization (P3)
System SHOULD (Phase 3) maintain per-player learned parameters that adjust the activity model to the player's observed interaction style, with appropriate prior + posterior update on each interaction.
**Rationale**: A first-week player and a six-week player have different rhythms; the system should learn theirs.
**Priority**: Should Have (Phase 3)

### FR-019: End-of-day reflection (P3)
System SHOULD (Phase 3) consolidate each day's events into a short narrative summary that feeds the next day's plan generation.
**Rationale**: Narrative continuity across days is what makes Nikita feel like she has memory of "yesterday."
**Priority**: Should Have (Phase 3)

### FR-020: Feature flag and rollback
System MUST be controllable by a feature flag with default-off, and MUST degrade cleanly to current behavior (reactive-only, no heartbeat) when the flag is off.
**Rationale**: Standard rollback contract; no deploy required to disable.
**Priority**: Must Have

---

## Non-Functional Requirements

### Performance
- A safety-net heartbeat tick across all active players MUST complete within the heartbeat tick interval (one hour of work must NOT take more than one hour to dispatch).
- A single per-player heartbeat operation MUST complete within 5 seconds (95th percentile).

### Security
- Heartbeat-triggered outreach MUST go through the same authentication and authorization path as conversation-triggered outreach. No new privilege boundary.
- Per-player learned parameters (FR-015) MUST be readable only by admin role.

### Scalability
- System MUST work correctly at 100 active players at MVP, scale design target 1,000 active players, with documented behavior up to 10,000 (cost circuit breaker may engage).

### Availability
- Heartbeat infrastructure MUST tolerate the dispatcher being down for 30 minutes without state corruption (catch-up policy in FR-013 governs).
- A bug in the heartbeat path MUST NOT block conversation-triggered messages from being delivered.

### Observability
- Each heartbeat invocation MUST emit structured telemetry: invocation count per cron tick, drop count from FR-013, skip-on-double-fire count from FR-009, cost-circuit-breaker engagements from FR-014.
- Live-versus-offline parity divergence (FR-016) MUST be queryable by chapter and time window.

---

## User Stories (CoD^Σ)

### US-1: Daily life arc generation (Priority: P1 - Must-Have)

```
Player → Nikita has a planned day → Nikita feels like a real person with her own life
```

**Why P1**: Without a daily plan, every other heartbeat behavior is generic. The plan is the substrate.

**Acceptance Criteria**:
- **AC-FR2-001**: Given an active player at start-of-day, When the daily-arc generation runs, Then a plan exists for that player for that date containing both a structured form and a narrative form.
- **AC-FR2-002**: Given an active player, When daily-arc generation runs twice for the same date, Then only one plan persists (idempotent).
- **AC-FR8-001**: Given a player in `game_over` state, When daily-arc generation runs, Then no plan is created for that player.

**Independent Test**: Trigger daily-arc generation for 5 throwaway players in a controlled environment; query persisted plans; assert each non-`game_over` player has exactly one plan with both forms.

**Dependencies**: None

---

### US-2: Safety-net hourly heartbeat (Priority: P1 - Must-Have)

```
Player → Nikita is "alive" between messages → Player feels she has continuity
```

**Why P1**: The hourly tick is the durability contract. Phase 2's richer self-scheduling layers on top of this; it is never removed.

**Acceptance Criteria**:
- **AC-FR5-001**: Given an active player who has not messaged in 6 hours, When the hourly tick fires, Then exactly one heartbeat operation is invoked for that player.
- **AC-FR9-001**: Given a heartbeat tick has just completed, When a duplicate tick fires within the idempotency window, Then the second tick reports "skipped" and produces zero side effects.
- **AC-FR10-001**: Given two simultaneous heartbeat operations target the same player, When they execute concurrently, Then exactly one succeeds and the other observes the serialized lock.
- **AC-FR13-001**: Given the dispatcher is down for 30 minutes, When it recovers and the safety-net tick fires, Then heartbeats older than the catch-up cutoff are dropped and the drop count is emitted as telemetry.

**Independent Test**: Deploy with feature flag on, observe over 24 hours that each active player receives at least 24 (one per hour) safety-net invocations. Idempotency probe via two manual invocations within the window. Concurrency probe via parallel asynchronous tasks.

**Dependencies**: None

---

### US-3: Plan-driven proactive touchpoint (Priority: P1 - Must-Have)

```
Player → Nikita occasionally reaches out based on her plan → "she's actually thinking about her day, not just me"
```

**Why P1**: The user-visible payoff of P1. Without this, the heartbeat is invisible and indistinguishable from the existing reactive system.

**Acceptance Criteria**:
- **AC-FR6-001**: Given a player has not been contacted today and the current heartbeat tick coincides with a plan step that authorizes outreach, When the heartbeat invocation completes, Then a touchpoint is scheduled for delivery whose content references at least one plan element.
- **AC-FR6-002**: Given a touchpoint has been scheduled in the last hour, When the next heartbeat tick attempts to schedule another for the same player, Then the second is suppressed (rate limit honored via dispatcher).
- **AC-FR7-001**: Given the heartbeat handler runs, When it wishes to outreach, Then it delegates to the dispatcher rather than writing directly to the outbound queue.

**Independent Test**: Run 24-hour observation across 5 controlled players; query touchpoints generated; assert each player received between 1 and 3 touchpoints (not 0, not 6+); language-model judge confirms each touchpoint references a plan element with success rate at least 80%.

**Dependencies**: US-1 (need a plan to reference)

---

### US-4: Live-versus-offline parity validator (Priority: P1 - Must-Have)

```
Operator → Compare production heartbeat behavior against offline simulation predictions → confidence the system does what we designed
```

**Why P1**: Without parity validation we cannot detect silent drift between the model and production. Drift in a stochastic system is invisible without explicit measurement.

**Acceptance Criteria**:
- **AC-FR16-001**: Given 7 days of production heartbeat data, When the parity validator runs, Then it produces a report with per-chapter empirical statistics versus offline simulation statistics.
- **AC-FR16-002**: Given divergence exceeds the configured threshold for any chapter, When the validator completes, Then it exits with non-zero status and files an alert.
- **AC-FR16-003**: Given divergence is within threshold, When the validator completes, Then it exits zero and produces a comparison artifact.

**Independent Test**: Inject a synthetic drift into a test cohort; run the validator; assert it detects the drift and alerts. Restore baseline; rerun; assert pass.

**Dependencies**: US-2 (need production heartbeat data to validate)

---

### US-5: Self-scheduling next wake (Priority: P2 - Phase 2)

```
Player → Nikita decides her own next "thinking about you" moment → outreach feels less mechanical, more bursty/realistic
```

**Why P2**: Enhances P1 by making heartbeat timing emerge from a continuous activity-aware intensity rather than a flat hourly cadence. Hourly safety-net stays as floor.

**Acceptance Criteria**:
- **AC-FR17-001**: Given an active player at any clock time, When the heartbeat handler completes, Then it schedules a next wake whose timing is sampled from the current activity-aware intensity (subject to FR-005 hourly floor and a 24-hour ceiling).
- **AC-FR17-002**: Given a 7-day production window with self-scheduling enabled, When inter-wake intervals are aggregated by hour-of-day, Then the empirical distribution matches the circadian curve (FR-016 parity passes).

**Independent Test**: Compare 7-day inter-wake distributions per hour-of-day against offline simulation; KS-test or equivalent distributional check.

**Dependencies**: US-2 complete (safety-net floor exists)

---

### US-6: Activity-aware intensity (Priority: P2 - Phase 2)

```
Player → Nikita's outreach pattern follows her activity (less at 3 AM, more after work) → realism via implicit context
```

**Why P2**: Implements the activity-distribution math (FR-003, FR-004) at the runtime layer. P1 ships the math infrastructure offline; P2 wires it into runtime self-scheduling.

**Acceptance Criteria**:
- **AC-FR3-001**: Given the empirical heartbeat distribution over 7 days, When bucketed by hour, Then the curve has a sleep trough (3-5 AM) and at least one waking peak.
- **AC-FR4-001**: Given any two adjacent minutes in the 24-hour cycle, When the intensity is computed at each, Then the values differ by less than the configured smoothness bound (no step changes).

**Independent Test**: Same as AC-FR17-002 plus a smoothness check.

**Dependencies**: US-5

---

### US-7: Reactive replan on player interaction (Priority: P2 - Phase 2)

```
Player messages → Nikita reassesses her forward schedule → her response timing reflects the new state, not pre-planned timing
```

**Why P2**: Without replan, a player message that arrives during Nikita's planned "social activity" block does not interrupt the planned post-block touchpoint, producing duplicate outreach. Replan eliminates this.

**Acceptance Criteria**:
- **AC-FR11-001**: Given Nikita has 3 pending future heartbeats, When the player sends a message, Then the 3 pending heartbeats are cancelled and exactly 1 new next-wake is computed and scheduled.
- **AC-FR11-002**: Given a player message arrives, When the respond-now-versus-later decision runs, Then the resulting decision is one of {respond now, defer with explicit timer} with logged rationale.
- **AC-FR12-001**: Given a chapter advance event, When the event handler completes, Then the player's pending heartbeats are cancelled and recomputed against the new chapter modulator.

**Independent Test**: Set up a player with N pending heartbeats; trigger each replan trigger; assert the cancellation and recomputation observed in scheduled-events table.

**Dependencies**: US-5

---

### US-8: Per-player Bayesian personalization (Priority: P3 - Phase 3)

```
Player → Nikita learns my rhythm specifically → "she actually knows me"
```

**Why P3**: Personalization is the long-term realism gain. Premature shipping risks under-tuned posteriors and bad early experiences. Phase 3 only after Phase 2 has 14 days of clean monitoring.

**Acceptance Criteria**:
- **AC-FR18-001**: Given a synthetic player with a known true interaction propensity, When 30 days of simulated interactions are observed, Then the posterior estimate of that propensity converges within 2 standard deviations of true.
- **AC-FR18-002**: Given the Bayesian feature flag is off, When the heartbeat runs, Then sampling falls back to chapter-level constants (no per-player learned values used).
- **AC-FR15-001**: Given the per-player learned parameters exist, When any log statement is emitted, Then the parameters do NOT appear in the log payload.

**Independent Test**: Synthetic-user MC convergence test. Log-grep for parameter leakage.

**Dependencies**: US-5, US-6, US-7 complete

---

### US-9: End-of-day reflection (Priority: P3 - Phase 3)

```
Player → Nikita's tomorrow plan reflects today's events → narrative continuity across days
```

**Why P3**: Narrative continuity is the polish layer. Without P1+P2 there is nothing meaningful to reflect on.

**Acceptance Criteria**:
- **AC-FR19-001**: Given a player has had a day of interactions, When end-of-day reflection runs, Then a short narrative summary is persisted and is referenced by the next day's plan generation prompt.
- **AC-FR19-002**: Given reflection content quality is judged by language-model evaluator, When 20 reflection outputs are scored against reference, Then the average score meets the configured quality threshold.

**Independent Test**: Generate 20 reflections; LLM-judge eval against hand-graded reference set.

**Dependencies**: US-1 complete (plan exists to reflect on)

---

## Intelligence Evidence

### Queries Executed (during Plan v4 brief assembly, 2026-04-17)

```
pr-codebase-intel agent (af7fe98404d53bd16): blast-radius mapping
pr-pattern-scout agent (aac5625b707ff0443): prior-art file paths
pr-test-coverage-auditor agent (ad8c9e8dfc3bf8d06): test pyramid + parity validator
pr-hygiene-auditor agent (a0b76a11981830664): spec slot + Doc 28 archive
pr-scope-reviewer agent (aa008d295305d390d): R1-R7 critical risks + Phase 1 ACs
pr-approach-evaluator agent (abdc0deaca4f778f1): A1 selected (7.75 weighted)
pr-devils-advocate agent (aaf696ef516bb1d1d): G1-G7 gaps including TZ + cost + PII
prompt-architect agent (a7e077ac14e3d942c): 6 brief-completeness fixes applied
```

### Findings

**Existing Patterns** (cited for plan.md, not spec.md):
- Reactive pipeline runs only at message time (no continuous loop today)
- Existing scheduled-events queue dispatches on `platform` field, not `event_type`
- Existing dispatcher already handles deduplication and rate limiting

**Related Features**:
- Reactive proactive-touchpoint subsystem already exists; heartbeat is the upstream timing layer that decides WHEN to invoke it
- Reactive life-simulation event generator already exists; heartbeat will eventually feed it instead of running only post-hoc

### Assumptions

- **A1**: Players accept proactive outreach (existing touchpoint system already does this; heartbeat just makes its timing principled)
- **A2**: Stochastic timing is preferred over deterministic schedules for realism (user-confirmed 2026-04-17)
- **A3**: 24-hour clock cycle is the right base period (no weekly arcs in P1)

---

## Scope

### In-Scope (Phase 1 - MVE)

- Daily plan generation (structured + narrative form per OD2)
- Safety-net hourly heartbeat with idempotency guard
- Plan-driven proactive touchpoint via existing dispatcher
- Live versus offline parity validator
- Feature flag with default-off
- Cost circuit breaker
- Privacy of per-player parameters (FR-015)
- Game-state respect (FR-008)
- Catch-up policy on stalls (FR-013)

### In-Scope (Phase 2)

- Self-scheduling next wake (FR-017)
- Activity-aware continuous intensity at runtime (FR-003 + FR-004 wired in)
- Reactive replan on all triggers in FR-012
- Per-player timezone honoring (deferred from Phase 1)
- Modality state (vacation/sick/normal/crunch)
- Weekend-mode activity overlay (deferred from Phase 1)

### In-Scope (Phase 3)

- Per-player Bayesian posteriors (FR-018) — REQUIRES `users.bayesian_state` JSONB column with admin-only-read RLS policy. Phase 1 explicitly defers admin-RLS pattern definition; Phase 3 MUST NOT begin until: (a) `is_admin()` SQL helper exists, (b) admin-RLS policy template documented, (c) the pattern is reviewed by Auth validator.
- End-of-day reflection (FR-019)
- Shadow → 10% → full rollout
- Phase 1 hold-the-line note: per user decision 2026-04-18 (GATE 2 iter-1 Decision D), admin-RLS pattern + per-player timezone column + modality enum + weekend-mode overlay all stay in Phase 2/3 boundaries. They MUST NOT be pulled into Phase 1 even when adjacent fixes touch the same files.

### Out-of-Scope (deferred)

- Voice-platform heartbeat integration (text-only Phase 1 per OD6; voice follows in a later spec)
- Cross-player simulation (Nikita having "friends" with their own arcs)
- Multi-day or week-long narrative arcs (existing narrative manager handles this)
- Replacing the existing reactive touchpoint subsystem (heartbeat composes with it)
- Migrating to a workflow-engine substrate (current background-job substrate is sufficient at scale targets)
- Dream-state events during sleep block (per OD3 default, skip)
- Heartbeat for `won`-state players (per OD4, stop)
- Archetype-cluster planning (per OD5, defer to Phase 2)

---

## Constraints

### Business Constraints

- Daily aggregate language-model cost MUST stay under the configured ceiling (default $50/day at 1000 active players, per OD1 Haiku 4.5 sizing)
- Phase 1 MVE MUST ship on existing background-job substrate (no new infrastructure dependencies)
- The existing reactive touchpoint subsystem's behavior MUST NOT regress

### User Constraints

- Players in any timezone MUST experience plausible behavior (Phase 1 honors UTC ± 3 hours; Phase 2 honors all)
- Players MUST be able to be in `game_over` or `won` without receiving heartbeats
- No heartbeat MAY produce more than one outreach per player per dispatcher rate-limit window

### Regulatory Constraints

- Per-player learned parameters are PII-adjacent and MUST follow existing data-handling rules (admin-only read, never in logs, redacted in error reports)

---

## Risks & Mitigations

### Risk 1: Branching ratio drift in self-exciting timing layer (Phase 2)
**Likelihood**: Medium (0.5)
**Impact**: High (8)
**Risk Score**: 4.0
**Mitigation**: Clamp the branching ratio at every parameter mutation, NOT just at initialization. Continuous monitoring telemetry. Validator (FR-016) detects drift in production statistics.

### Risk 2: Cron double-fire produces duplicate outreach
**Likelihood**: High (0.8)
**Impact**: Medium (5)
**Risk Score**: 4.0
**Mitigation**: FR-009 idempotency guard required; documented existing pattern; FR-007 dispatcher handoff inherits dispatcher dedup.

### Risk 3: Concurrent state updates from cron + player message + admin action
**Likelihood**: Medium (0.5)
**Impact**: High (8)
**Risk Score**: 4.0
**Mitigation**: FR-010 serialization required from Phase 1, NOT deferred.

### Risk 4: Per-player parameters leak in logs (re-identification risk)
**Likelihood**: Medium (0.5)
**Impact**: High (8)
**Risk Score**: 4.0
**Mitigation**: FR-015 explicit constraint; pre-PR grep gate to extend testing rules; admin-only-read policy on storage.

### Risk 5: Cron stall produces midnight burst on resume
**Likelihood**: Low (0.2)
**Impact**: High (8)
**Risk Score**: 1.6
**Mitigation**: FR-013 catch-up policy: drop stale heartbeats; emit drop count telemetry.

### Risk 6: Cost runaway at scale
**Likelihood**: Medium (0.5)
**Impact**: Medium (5)
**Risk Score**: 2.5
**Mitigation**: FR-014 daily ceiling with graceful degradation; per OD1 default model is the cheaper Haiku tier.

### Risk 7: Phase 1 plan-step schema does not survive into Phase 2 continuous-distribution model
**Likelihood**: High (0.8)
**Impact**: Low (2)
**Risk Score**: 1.6
**Mitigation**: Acknowledge Phase 1 schema as throwaway in plan.md; Phase 2 introduces parallel storage rather than mutating the Phase 1 schema. No data migration required.

### Risk 8: Server-time-zone assumption misfires for shift-workers and travelers
**Likelihood**: Medium (0.5)
**Impact**: Medium (5)
**Risk Score**: 2.5
**Mitigation**: Phase 1 limits behavior to UTC ± 3-hour offset users; out-of-band users get flat (TZ-agnostic) intensity. Phase 2 honors per-player IANA timezone.

---

## Success Metrics

### User-Centric

- Qualitative survey: "Does Nikita feel like a real person with her own life?" target ≥4.0/5 average vs pre-heartbeat baseline
- Player retention 7-day: target ≥5% lift attributable to heartbeat (A/B between flag-on and flag-off cohorts in shadow mode)
- Inter-message-gap perception: players in flag-on cohort report fewer "she's a chatbot" sentiments

### Technical

- Live-vs-offline parity validator (FR-016): per-chapter divergence within configured threshold for ≥7 consecutive days
- Idempotency probe: 0 duplicate outreach events caused by double-fire
- Concurrent-update probe: 0 state corruption events under simulated concurrent load
- Cost: daily aggregate within configured ceiling on 30 of 30 days
- Coverage: ≥80% line coverage on new heartbeat module (per project test rules)

### Business

- Touchpoint open-rate (where measurable via Telegram): target ≥X% lift over reactive-only baseline
- Game progression rate: heartbeat cohort progresses through chapters at parity or better with control

---

## Open Questions

All Open Decisions OD1-OD8 from Plan v4 §4.5 have been resolved by applying defaults per `apply-OD-defaults` invocation. Defaults documented inline in this spec at the relevant FRs and Scope sections:

- **OD1** (LLM model): Haiku 4.5 for daily-arc generation and reflection
- **OD2** (plan storage shape): BOTH structured and narrative
- **OD3** (sleep-hours behavior): Skip dream-state events
- **OD4** (game-state `won`): Stop heartbeat entirely
- **OD5** (multi-tenant cost strategy): Per-user Phase 1, archetype Phase 2
- **OD6** (voice platform): Text-only Phase 1
- **OD7** (planner type): LLM-generated
- **OD8** (Phase 1 weekend behavior): Weekday-only Phase 1; weekend overlay Phase 2

If the user reverses any default, that becomes a spec amendment + re-validation event.

---

## Stakeholders

**Owner**: Solo dev (Simon)
**Created By**: Claude (delightful-orbiting-ladybug worktree session, 2026-04-17), via Wave 1+2+3 multi-agent orchestration synthesizing into Plan v4 brief
**Reviewers**: SDD GATE 2, 6 parallel sdd-*-validator agents (mandatory per `.claude/CLAUDE.md` SDD enforcement #3)
**Informed**: Project ROADMAP.md (Domain 3 entry registered)

---

## Approvals

- [ ] **Product Owner**: Simon, pending
- [ ] **Engineering Lead**: Simon, pending
- [ ] **GATE 2 Validators**: 6 sdd-*-validator agents, pending

---

## Specification Checklist

**Before Planning**:
- [x] All [NEEDS CLARIFICATION] resolved (0 / 3 used)
- [x] All user stories have ≥2 acceptance criteria
- [x] All user stories have priority (P1, P2, P3)
- [x] All user stories have independent test criteria
- [x] P1 stories define MVP scope (US-1 through US-4)
- [x] No technology implementation details in spec (math model and tech stack live in plan.md)
- [x] Intelligence evidence provided (Wave 1+2+3 agent IDs cited)
- [ ] Stakeholder approvals obtained (pending)

**Status**: Draft, ready for /plan and GATE 2 validation

---

**Version**: 1.0
**Last Updated**: 2026-04-17
**Next Step**: Auto-chain to /plan (SDD Phase 5) for implementation plan, then /tasks (Phase 6), then /audit (Phase 7) with mandatory 6-validator GATE 2.
