# 25 — Implementation Roadmap: Phased Rollout Plan

**Series**: Bayesian Inference for AI Companions — Synthesis
**Date**: 2026-02-16
**Inputs**: Phase 2 ideas (12-19) + Phase 3 evaluations (20-23) + Architecture (Doc 24)
**Status**: FINAL

---

## 1. Roadmap Overview

The implementation follows Doc 23's phased investment strategy: each phase delivers standalone value and ends with a decision gate. The project can be stopped at any gate without waste.

```
Phase 1         Phase 2          Phase 3           Phase 4
(2 weeks)       (2 weeks)        (4 weeks)         (5 weeks)
   │                │                │                │
   v                v                v                v
┌─────────┐  ┌──────────┐  ┌──────────────┐  ┌──────────────┐
│ Beta     │  │ Thompson │  │ Emotional    │  │ Full         │
│ Metrics  │  │ Sampling │  │ State Machine│  │ Integration  │
│ +Shadow  │  │ Skip/Time│  │ +Surprise    │  │ +Events+Vice │
└────┬─────┘  └─────┬────┘  └──────┬───────┘  └──────┬───────┘
     │              │              │               │
  GATE 1         GATE 2         GATE 3          GATE 4
  (4 weeks      (4 weeks      (6 weeks        (launch)
   shadow)       A/B test)     A/B test)
```

**Total timeline**: 13 weeks development + 14 weeks validation = 27 weeks (~6.5 months)
**Total cost**: $65K engineering (at $5K/week loaded)
**Can stop at**: Any gate, retaining value from completed phases

---

## 2. Phase 1: Beta Metric Posteriors (Weeks 1-2)

### 2.1 Scope

Replace flat `Decimal` metric storage with Beta posteriors. Run in **shadow mode** alongside existing deterministic scoring.

### 2.2 Deliverables

| Deliverable | Files | Lines (est.) |
|-------------|-------|-------------|
| `BayesianPlayerState` dataclass | `bayesian/state.py` | 200 |
| `MetricUpdater` with observation mapping | `bayesian/metrics.py` | 150 |
| `FeatureExtractor` (rule-based only) | `bayesian/features.py` | 100 |
| `BayesianConfig` feature flags | `bayesian/config.py` | 80 |
| Database migration: `bayesian_states` table | `migrations/` | 30 |
| Shadow mode comparison logger | `bayesian/shadow.py` | 60 |
| Unit tests | `tests/bayesian/` | 200 |
| **Total** | 7 files | ~820 lines |

### 2.3 Implementation Steps

**Week 1: Core state + metrics**

1. Create `nikita/bayesian/` package with `__init__.py`
2. Implement `BayesianPlayerState` dataclass with:
   - 4 Beta posteriors (intimacy, passion, trust, secureness)
   - Dirichlet vice preferences (8 categories)
   - Serialization: `to_json()` / `from_json()`
   - Properties: `composite_score_estimate`, `metric_means`, `metric_uncertainties`
3. Implement `MetricUpdater`:
   - Observation mapping (Doc 12's `EVENT_OBSERVATION_MAP`)
   - Cold start damping: half-weight for first 10 messages (Doc 20 recommendation)
   - Decay toward priors with chapter-specific grace periods
4. Implement `FeatureExtractor`:
   - Message length, response time, question detection, basic sentiment, consistency
   - No LLM extraction in Phase 1
5. Create Supabase migration for `bayesian_states` table

**Week 2: Shadow mode + testing**

6. Implement shadow mode comparison:
   - After each message, compute both deterministic and Bayesian scores
   - Log divergence to `bayesian_shadow_log` table
   - No user-facing changes
7. Add `BayesianConfig` with feature flags (all defaulting to shadow/disabled)
8. Write unit tests:
   - Beta update correctness (positive increases mean, negative decreases)
   - Property-based tests (Hypothesis): posterior mean always in [0,1]
   - Decay regression toward prior
   - Cold start damping
   - Serialization round-trip
9. Integration test: process 50 messages through both systems, verify divergence <10%
10. Deploy to staging environment, enable shadow mode

### 2.4 Decision Gate 1 (After 4 Weeks of Shadow Data)

**Pass criteria** (ALL required):

| Criterion | Metric | Threshold |
|-----------|--------|-----------|
| Score correlation | Pearson r between Bayesian and deterministic composite scores | r > 0.85 |
| Mean divergence | Average absolute difference in composite scores | < 5 points (out of 100) |
| Stability | No player's Bayesian score crosses a chapter threshold without their deterministic score also crossing | 100% agreement |
| Debugging value | Engineering team reports Bayesian state useful for investigation | Qualitative YES from >=1 engineer |
| Performance | p99 shadow mode latency | < 15ms |

**If PASS**: Proceed to Phase 2.
**If FAIL**: Investigate divergence causes. Likely issues: observation weights need recalibration, decay rates mismatched. Budget 1 additional week for tuning.

---

## 3. Phase 2: Thompson Sampling Decisions (Weeks 3-4)

### 3.1 Scope

Enable Bayesian skip rate and response timing. First user-visible behavioral change. Requires A/B testing.

### 3.2 Deliverables

| Deliverable | Files | Lines (est.) |
|-------------|-------|-------------|
| `BayesianSkipDecision` | `bayesian/skip.py` | 80 |
| `BayesianTimingDecision` | `bayesian/timing.py` | 100 |
| A/B test assignment logic | `bayesian/ab_test.py` | 60 |
| Skip/timing integration into pipeline | `pipeline/orchestrator.py` (modify) | 30 |
| Tests | `tests/bayesian/` | 150 |
| **Total** | 4 new files + 1 modified | ~420 lines |

### 3.3 Implementation Steps

**Week 3: Skip + timing decisions**

1. Implement `BayesianSkipDecision`:
   - Thompson Sample from Beta(skip_alpha, skip_beta)
   - Hard cap: max 3 consecutive skips (Doc 12)
   - Chapter-dependent priors (Doc 19)
   - Secure base constraint: if player pattern is "hyperactive", use consistent skip rate (Doc 21)
2. Implement `BayesianTimingDecision`:
   - Dirichlet over timing buckets [instant, fast, moderate, slow, very_slow]
   - Sample bucket, then uniform within bucket range
   - Chapter-dependent bucket definitions
3. Wire into `orchestrator.py`:
   - Check `BayesianConfig.thompson_skip_enabled` flag
   - If enabled, use Bayesian skip/timing; else, use existing logic
4. Implement A/B test assignment:
   - 50/50 split by user_id hash
   - Log assignment to `ab_test_assignments` table

**Week 4: A/B infrastructure + testing**

5. Add A/B test metrics collection:
   - Session length (messages per session)
   - Messages per day
   - Day-7 retention (requires 7+ days to measure)
   - Skip acceptance rate (does the player continue after a skip?)
6. Write property-based tests:
   - Skip rate bounded by hard caps
   - Timing always within chapter bounds
   - Thompson Sampling converges toward observed engagement rate
7. Trajectory simulation tests:
   - Simulate 200 messages with different player behaviors
   - Verify skip rate adapts (more engagement → lower skip rate)
8. Deploy A/B test to production

### 3.4 Decision Gate 2 (After 4 Weeks of A/B Data)

**Pass criteria** (ALL required):

| Criterion | Metric | Threshold |
|-----------|--------|-----------|
| Session length | Bayesian cohort vs. control | >= -5% (non-inferior) |
| Day-7 retention | Bayesian cohort vs. control | >= -2% (non-inferior) |
| Skip acceptance | Players continue chatting after skip events | > 70% |
| Player qualitative | Survey: "Does Nikita feel natural?" | No regression |
| Adaptation evidence | Skip rate variance between players | Higher than control (proves personalization) |

**If PASS**: Proceed to Phase 3.
**If FAIL**: Possible issues: skip rates too aggressive, timing feels "off." Tune priors and hard caps. Budget 1-2 weeks for recalibration.

---

## 4. Phase 3: Emotional State Machine + Surprise (Weeks 5-8)

### 4.1 Scope

Deploy the Bayesian state machine for emotional inference (replacing the full DBN per Doc 22). Enable surprise-based conflict triggering with directional surprise (Doc 20).

### 4.2 Deliverables

| Deliverable | Files | Lines (est.) |
|-------------|-------|-------------|
| `BayesianStateMachine` (6 states) | `bayesian/emotional.py` | 200 |
| `SurpriseDetector` (KL divergence) | `bayesian/surprise.py` | 120 |
| `NarrativeFilter` (Doc 20) | `bayesian/narrative_filter.py` | 100 |
| `SecureBaseConstraint` + `EmotionalSafetyGuard` (Doc 21) | `bayesian/safety.py` | 150 |
| Dual-decay stress model (Doc 21 Section 7) | In `bayesian/emotional.py` | 50 |
| `BayesianEngine` orchestrator | `bayesian/engine.py` | 150 |
| `BayesianContext` for pipeline injection | `bayesian/context.py` | 80 |
| Pipeline integration (modify Stages 4, 5, 6, 9) | `pipeline/` (modify) | 60 |
| Tests | `tests/bayesian/` | 300 |
| **Total** | 7 new + 4 modified | ~1,210 lines |

### 4.3 Implementation Steps

**Week 5: State machine + surprise**

1. Implement `BayesianStateMachine`:
   - 6 states: content, playful, anxious, guarded, confrontational, withdrawn
   - Base transition matrix (6x6)
   - Situation-triggered modulation (Doc 21 Section 8.2)
   - Metric-posterior modulation (trust, stress affect transitions)
   - Minimum 3-message transition constraint (Doc 21 Section 9.3)
   - Transition cause tracking (narrative accountability)
2. Implement dual-decay stress model:
   - Acute stress: half-life ~3 messages
   - Chronic stress: half-life ~23 messages
   - Relational stressors build both components
3. Implement `SurpriseDetector`:
   - KL divergence between pre-update and post-update Beta posteriors
   - **Negative directional only** for boss triggers (Doc 20 Section 4.2)
   - Positive surprise → milestone moments (separate handler)
   - Tier 1/2/3 escalation thresholds

**Week 6: Safety + narrative filter**

4. Implement `NarrativeFilter`:
   - Check: does the behavioral change have a perceivable cause?
   - If no cause available: suppress the change and resample
   - Signal-gradient enforcement (Doc 20 Section 2.3): positive action → positive response
5. Implement `SecureBaseConstraint`:
   - Detect "hyperactive" and "withdrawn" engagement patterns
   - Constrain Bayesian decisions to promote consistent, warm behavior
6. Implement `EmotionalSafetyGuard`:
   - Max negative-to-positive ratio: 1:4
   - No back-to-back emotional reversals
   - Force positive when ratio exceeded

**Week 7: Integration + engine**

7. Implement `BayesianEngine`:
   - Orchestrate: extract → load → update → state machine → surprise → filter → save
   - Async DB operations (load + save)
   - Escalation routing (Tier 2 → Sonnet, Tier 3 → Opus)
8. Implement `BayesianContext`:
   - `to_prompt_guidance()`: natural language behavioral hints for Stage 9
   - Emotional state injection for Stage 4
   - Surprise level for Stage 6 conflict detection
9. Wire into pipeline:
   - Add Bayesian pre-stage before Stage 1
   - Modify Stage 4: use Bayesian emotional state if available
   - Modify Stage 5: use Bayesian composite score if available
   - Modify Stage 6: use surprise-based conflict trigger if available
   - Modify Stage 9: inject behavioral guidance

**Week 8: Testing + deployment**

10. Write comprehensive tests:
    - State machine transitions (correct probabilities, situation modulation)
    - Surprise computation (directional, threshold classification)
    - Narrative filter (blocks causeless transitions, preserves signal gradient)
    - Safety constraints (secure base, emotional guard, consistency floor)
    - Integration: full engine process on 100 simulated conversations
11. Trajectory simulations:
    - "Consistently positive player" → reaches Chapter 2 at expected pace
    - "Absent player" → decays toward prior without crashing
    - "Conflict-prone player" → boss encounters at organic moments
    - "Repair attempt" → conflict de-escalation
12. Deploy with A/B test (separate cohort from Phase 2)

### 4.4 Decision Gate 3 (After 6 Weeks of A/B Data)

**Pass criteria** (ALL required):

| Criterion | Metric | Threshold |
|-----------|--------|-----------|
| Session engagement | Messages per session | >= -5% vs. control |
| Boss encounter quality | Survey: "Did this crisis feel earned?" | > 60% positive |
| Emotional coherence | Survey: "Does Nikita's mood make sense?" | > 70% positive |
| Escalation rate | % messages triggering Tier 2/3 | 5-15% (not too high, not too low) |
| Safety interventions | % messages with safety override | < 10% |
| No trauma bonding signals | Escalation spirals lasting >5 messages | < 2% of conflicts |

**If PASS**: Proceed to Phase 4.
**If FAIL**: Most likely causes: state machine transitions feel abrupt (increase minimum transition messages), surprise thresholds too sensitive (raise them), safety constraints too aggressive (loosen). Budget 2-3 weeks for tuning.

---

## 5. Phase 4: Full Integration (Weeks 9-13)

### 5.1 Scope

Enable remaining components: Bayesian event selection, Dirichlet vice discovery, emotional contagion, controlled randomness. Deploy full Bayesian architecture.

### 5.2 Deliverables

| Deliverable | Files | Lines (est.) |
|-------------|-------|-------------|
| `BayesianEventSelector` | `bayesian/events.py` | 120 |
| Template-based narration for low-importance events | `bayesian/templates.py` | 80 |
| Vice discovery with Dirichlet exploration | Enhanced `bayesian/state.py` | 40 |
| Situation-triggered personality variation (Doc 21) | Enhanced `bayesian/emotional.py` | 60 |
| Engagement-dependent contagion (Doc 21 Section 4.3) | `bayesian/contagion.py` | 100 |
| Observation quality monitor (Doc 22 Section 5.3) | `bayesian/monitoring.py` | 80 |
| Portal API for Bayesian state display | `api/bayesian_routes.py` | 60 |
| A/B test analysis dashboard | `portal/` pages | 150 |
| Comprehensive test suite | `tests/bayesian/` | 300 |
| Performance benchmarks | `tests/bayesian/benchmarks/` | 100 |
| **Total** | 6 new + 3 modified + tests | ~1,090 lines |

### 5.3 Implementation Steps

**Week 9: Event selection + vice discovery**

1. Implement `BayesianEventSelector`:
   - Weighted random over 3 domains (personal, social, reflective) — not 15 categories (Doc 22 simplification)
   - Per-player weight update based on engagement with previous events
   - Template narration for low-importance events (40% LLM savings)
2. Enable Dirichlet vice discovery:
   - Update vice_dirichlet on keyword detection
   - Thompson Sampling for vice probing (which vice topic to introduce next)

**Week 10: Contagion + randomness**

3. Implement engagement-dependent contagion (Doc 21 recommendation):
   - Coupling constant varies by engagement pattern: responsive=0.15, hyperactive=0.45, withdrawn=0.05
   - Repair attempt detection breaks negative contagion loops
   - Asymmetric coupling: player→Nikita moderate, Nikita→player(inferred) weak
4. Implement situation-triggered personality variation (Doc 21 Section 8.2):
   - Replace Doc 17's tail sampling with situation-driven modulation
   - Contextual triggers: stressful_topic, playful_exchange, vulnerability_moment, etc.
   - Personality is fixed; expression varies with context

**Week 11: Monitoring + quality**

5. Implement observation quality monitor:
   - 5% of messages: compare rule-based vs. LLM observations
   - Track agreement rate per observation type
   - Alert if agreement drops below 70%
6. Add Portal API endpoints for Bayesian state display:
   - Abstract indicators (not raw numbers): warmth meter, mystery meter, trend arrows
   - Uncertainty as "how well do you know Nikita?"
7. Performance benchmarking:
   - Measure p50/p90/p99 latency for full Bayesian pipeline
   - Ensure <25ms at p99

**Week 12-13: Full integration testing + deployment**

8. End-to-end integration tests:
   - 500-message simulated player journeys (3 archetypes: engaged, casual, difficult)
   - Verify chapter progression timing matches design intent
   - Verify boss encounters feel organic (manual review of 20 simulated conflicts)
   - Verify no trauma bonding patterns in simulated trajectories
9. A/B test: full Bayesian system vs. Phase 3 Bayesian system vs. deterministic control
10. Sensitivity analysis on top 10 parameters (Doc 22 Section 6.2)
11. Production deployment with staged rollout: 10% → 25% → 50% → 100%

### 5.4 Decision Gate 4 (Launch Decision — After 4 Weeks)

**Pass criteria** (ALL required):

| Criterion | Metric | Threshold |
|-----------|--------|-----------|
| All Phase 2/3 criteria | (inherited) | Still passing |
| Token cost reduction | Bayesian vs. deterministic | >= 10% savings |
| Personalization evidence | Per-player behavioral variance | Higher than deterministic |
| Event engagement | Player response rate to Bayesian-selected events | >= control |
| Vice discovery accuracy | Player confirms top vice matches in survey | > 60% |
| No ethical red flags | Review by team + external advisor | Approved |

**If PASS**: Full Bayesian system is live.
**If FAIL**: Identify failing component, disable it, continue with working components.

---

## 6. Risk Mitigation Timeline

| Risk | Phase Detected | Mitigation |
|------|---------------|------------|
| Observation weights wrong | Phase 1 (shadow divergence) | Recalibrate from shadow data |
| Skip rates too aggressive | Phase 2 (A/B test) | Tighten hard caps, widen priors |
| State machine transitions jarring | Phase 3 (qualitative) | Increase min transition messages |
| Surprise thresholds wrong | Phase 3 (escalation rate) | Adjust tier thresholds |
| Contagion spirals | Phase 4 (safety monitor) | Reduce coupling, increase repair sensitivity |
| Performance regression | Any phase (latency monitor) | Simplify computation, add caching |

---

## 7. Staffing & Resource Requirements

| Role | Phases | Commitment |
|------|--------|------------|
| Backend engineer (primary) | 1-4 | Full-time, 13 weeks |
| Backend engineer (review) | 1-4 | 20% time (code review, pair programming) |
| Game designer (calibration) | 2-4 | 30% time (parameter tuning, A/B analysis) |
| QA/Testing | 3-4 | 50% time (trajectory simulations, A/B monitoring) |
| Ethics review | 3-4 | 5 hours total (safety constraint review) |

---

## 8. Success Metrics (12 Months Post-Launch)

| Metric | Target | Measurement |
|--------|--------|-------------|
| Token cost reduction | >= 10% | Monthly billing comparison |
| p99 pipeline latency | < 25ms (Bayesian stage) | Prometheus monitoring |
| Player retention (D7) | >= 2% improvement | A/B cohort comparison |
| Boss encounter satisfaction | > 65% "felt earned" | In-game survey |
| Personalization awareness | > 50% "she gets me" | In-game survey |
| Escalation rate | 85/12/3 (Tier 1/2/3) | Prometheus counters |
| Safety intervention rate | < 5% of messages | Safety counter |
| Engineering debugging time | 50% reduction | Time tracking |
