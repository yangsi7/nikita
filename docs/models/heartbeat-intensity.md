# Heartbeat Intensity Model — Spec 215 Phase 1

> Companion documentation for `nikita/heartbeat/intensity.py`. Math
> authority: `/Users/yangsim/.claude/plans/delightful-orbiting-ladybug.md`
> §A.1 through §A.6 (Plan v3 Appendix A — von Mises × Hawkes × Ogata
> thinning).

**Model**: `λ_heartbeat(t | H_t, c, e) = M_chapter(c) · M_engagement(e) · Σ_a p(a | t) · ν_a + Σ_i α(k_i) · w_i · β · exp(−β · (t − t_i))`

**Status**: Phase 1 of three (math + MC validator + flag). Phase 2 adds
self-scheduling cron + weekend swap. Phase 3 adds per-player Bayesian
posteriors. See `specs/215-heartbeat-engine/` for the SDD artifacts.

---

## 1. Problem Statement

Nikita needs a quantitative model for "how often is she thinking about
the player right now?" so the heartbeat scheduler (Phase 2) can decide
when to fire a proactive touchpoint. The model must:

1. Honor circadian rhythm (more thoughts in evenings, fewer in deep
   sleep) — but never zero anywhere (Plan v3 §A.1 user constraint).
2. Respond to recent events (a user message, a chapter advance) by
   raising intensity, with the boost decaying over hours not minutes.
3. Vary by chapter (early infatuation > settled relationship) and
   engagement state (clingy ≫ distant).
4. Run cheaply per request (microseconds; called from a 5-minute cron
   loop over thousands of users).
5. Stay stable: the system must NOT self-excite into a feedback loop
   under sustained activity bursts.

The Phase 1 module ships the math + a Monte Carlo validator + a feature
flag (default off). Phase 2 wires it to a scheduler and a `/tasks/heartbeat`
endpoint; Phase 3 adds per-player learning.

---

## 2. Mathematical Model

### Layer 1 — Activity distribution `p(a | t)`

Time-varying probability over five activities `a ∈ {sleep, work, eating,
personal, social}`. Each activity's affinity is a (Bessel-normalized)
von Mises mixture in circular phase φ = 2π · (t mod 24) / 24:

```
λ_a(t) = Σ_{k=1..K_a}  w_{a,k} · exp(κ_{a,k} · cos(φ - μ_{a,k})) / I_0(κ_{a,k})
```

I_0 is the modified Bessel function of the first kind, computed via
Abramowitz & Stegun polynomial approximation 9.8.1 + 9.8.2 (no scipy
dep; max relative error ~2e-7). The I_0(κ) divisor makes each component
a proper unit-area pdf — without it, high-κ components (sharp peaks)
have peak heights that grow as exp(κ) and dwarf lower-κ components by
orders of magnitude, breaking the Dirichlet-weight controllability of
relative dominance.

Composed via softmax with a uniform noise floor ε:

```
p(a | t) = (1 − ε) · [ λ_a(t) / Σ_b λ_b(t) ]  +  ε / A
```

Default ε = 0.03, A = 5 → minimum probability 0.6% everywhere.

### Layer 2 — Activity-conditional rate ν_a

Each activity has its own base rate of "she's thinking about him"
(heartbeats/hour):

| Activity | ν_a | Rationale |
|---|---|---|
| sleep | 0.05 | Dream-state thoughts only (~once per 20 h). |
| work | 0.30 | Occasional thoughts during the day. |
| eating | 0.30 | Less reflective than v1 assumed (she's eating, not pondering). |
| personal | 1.00 | Free time / hobbies = high thought-cycles. |
| social | 0.40 | Distracted by others, but reminded. |

### Layer 3 — Hawkes self-excitation

Exponential kernel, half-life 3 h:

```
g(τ) = β · exp(−β · τ),    β = ln(2) / 3 ≈ 0.231 hr⁻¹
```

Per-event excitation `α(k_i) · w_i · β`. Recursive O(1) update form
(persisted as a single scalar `R` on the user row):

```
At event j:   R(t_j⁺) = R(t_{j-1}) · exp(−β · (t_j − t_{j-1}))  +  α(k_j) · w_j · β
At query t:   λ_excite(t) = R(t_j) · exp(−β · (t − t_j))
```

`R` is capped at `R_MAX = 1.5` to bound storm spikes.

### Layer 4 — Modulators

Multiplicative on the activity baseline (NOT on Hawkes):

```
M_chapter ∈ {1.5 Ch1, 1.3 Ch2, 1.1 Ch3, 1.0 Ch4, 0.9 Ch5}    (excitement fades)
M_engagement ∈ {1.4 calibrating, 1.0 in_zone, 0.7 fading, 0.4 distant, 1.6 clingy}
```

### Layer 5 — Total intensity (the equation)

```
λ_heartbeat(t | H_t, c, e)
    = M_chapter(c) · M_engagement(e) · Σ_a p(a | t) · ν_a
      + Σ_i  α(k_i) · w_i · β · exp(−β · (t − t_i))
```

### Layer 6 — Self-scheduling: Ogata thinning

The scheduler samples the next wake by Ogata's thinning algorithm:
propose from a homogeneous Poisson with the upper-bound intensity over
the next-hour window, accept with probability λ_actual / λ_max. Pure
Python stdlib, microseconds per call. See
`nikita/heartbeat/intensity.py:sample_next_wakeup`.

---

## 3. Parameters (regression-guarded)

Every constant is a `Final` with a multi-line comment per
`.claude/rules/tuning-constants.md` and a regression test in
`tests/heartbeat/test_intensity.py` (test names `test_AC_T1_3_NNN_*`).

| Constant | Value | Source | Test |
|---|---|---|---|
| `EPSILON_FLOOR` | 0.03 | Plan v3 §A.1 | AC-T1.3-002 |
| `T_HALF_HRS` | 3.0 h | Plan v3 §A.2 | AC-T1.3-005 |
| `BETA` | ln(2)/3 ≈ 0.231 hr⁻¹ | derived | AC-T1.3-006 |
| `R_MAX` | 1.5 | Plan v3 §A.5 | AC-T1.3-007 |
| `ALPHA["user_msg"]` | 0.40 | Plan v3 §A.5 | AC-T1.3-004 |
| `ALPHA["game_event"]` | 0.15 | Plan v3 §A.5 | AC-T1.3-004 |
| `ALPHA["internal"]` | 0.05 | Plan v3 §A.5 | AC-T1.3-004 |
| `NU_PER_ACTIVITY` | (table §2 above) | Plan v3 §A.2 v2 (2026-04-17) | AC-T1.3-008 |
| `CHAPTER_MULT` | (1.5, 1.3, 1.1, 1.0, 0.9) | Plan v3 §A.4 | AC-T1.3-003 |
| `ENGAGEMENT_MULT` | (1.4, 1.0, 0.7, 0.4, 1.6) | Spec 014/057 | — |
| `DIRICHLET_PRIOR` | (32, 22, 5, 28, 13) sum=100 | Plan v3 §A.1.5 v2 | AC-T1.3-009 |

Branching ratio (stability proof): 0.40·1.2 + 0.15·1.0 + 0.05·1.0 = 0.68
< 1.0. Margin 0.32 lets E[w_user] swing up to ~2.4 before instability.

---

## 4. Monte Carlo Validation

Run via `uv run python scripts/models/heartbeat_intensity_mc.py`. Default
exits 0/1 on the 8 sanity assertions only (fast path; <5 s). Pass
`--regen-plots` to refresh the 7 PNGs in this directory.

### Sanity assertions (all 8 pass on master)

1. `activity_distribution(t)` sums to 1.0 ± 1e-6 at 100 sample points.
2. `min(p_a) ≥ ε/A` everywhere (noise-floor invariant).
3. `λ_baseline(t, ch) > 0` for all t × all chapters.
4. Hawkes branching ratio `α·E[w]` < 1 (stability).
5. Sleep peak in [01:00, 04:30] OR [22:30, 24:00] — von Mises mean
   recoverable from `p(sleep | t)`.
6. R decays to <1% of initial within 7·T_half = 21h.
7. Ch3 inter-wake median in [30 min, 240 min] (no-user-msg sim, 14 d).
8. Evening wake count > 2× sleep-trough wake count (circadian shape).

### Generated plots

Embedded in `docs/models/heartbeat-*.png`:

| File | Purpose |
|---|---|
| `heartbeat-activity-distribution.png` | 24 h stacked area of `p(a | t)` with ε floor visible |
| `heartbeat-baseline-per-chapter.png` | `λ_baseline(t)` per chapter (Ch1-Ch5 overlaid) |
| `heartbeat-hawkes-scenarios.png` | R(t) traces for 1-msg, burst-of-5, sustained-chat |
| `heartbeat-typical-day.png` | Activity + λ_total + heartbeat events for one Ch3 day |
| `heartbeat-silent-vs-chatty-week.png` | 7-day comparison, low-activity vs high-activity user |
| `heartbeat-interwake-distribution.png` | Inter-wake gap histogram per chapter (pure baseline) |
| `heartbeat-replan-effect.png` | Chapter advance mid-day cancels pending heartbeats |

---

## 5. Phase 1 ↔ Phase 2/3 Boundary

Phase 1 (this PR + PR 215-A) ships:
- ✅ Math production module + MC validator + tests
- ✅ Settings flag `heartbeat_engine_enabled` (default false; PR 215-A)
- ✅ `nikita_daily_plan` table + RLS policies (PR 215-A)
- ❌ NO weekend `ACTIVITY_PARAMS_WEEKEND` swap (deferred to Phase 2)
- ❌ NO live runtime — `sample_next_wakeup` exists but no caller
- ❌ NO per-user Bayesian state — single shared `ACTIVITY_PARAMS` table
- ❌ NO timezone awareness — Plan v4 R6 hardcodes UTC for Phase 1

Phase 2 (Spec 216) will add:
- `nikita/heartbeat/scheduler.py` — production self-scheduler
- `users.timezone` IANA column + `weekday_idx` parameter
- `ACTIVITY_PARAMS_WEEKDAY` + `ACTIVITY_PARAMS_WEEKEND` (rave-mode swap)
- Watchdog cron to re-bootstrap users with no future scheduled event
- Live-versus-offline parity validator (FR-016) wired to nightly job

Phase 3 (Spec 217) will add:
- `users.bayesian_state` JSONB with admin-only RLS
- End-of-day Beta posterior updates (Doc 30 §4)
- Reflection cycle (LLM end-of-day narrative)
- Shadow → 10% → full rollout per Doc 30 §11

---

## 6. Citations

Math model derivation references (full bibliography in Plan v3 §A.6):

- **Sparklen, Lacoste 2025** — Hawkes process inference + branching-ratio
  stability + production failure modes (novel-territory burden for
  circadian × Hawkes agents)
- **Ye, Van Niekerk, Rue 2025** (arXiv:2502.18223) — von Mises Bayesian
  conjugate priors (Damien-Walker 1999 form); used by Phase 3 update
- **Rowcliffe et al. 2014** (doi:10.1111/2041-210X.12278) — canonical
  use of von Mises kernel for 24 h activity density
- **Borbely 2016** — chronobiology Process C as cosine forcing,
  mathematically equivalent to von Mises
- **Rizoiu, Lee, Mishra, Xie 2017** (arXiv:1708.06401) — Hawkes process
  tutorial; recursive O(1) update derivation used here
- **Kobayashi & Lambiotte 2016** (TiDeH, arXiv:1603.09449) — circadian
  × Hawkes for retweets (closest published analog to our use case)
- **Ozaki 1979** (AISM 31:145-155) — foundational MLE of self-exciting
  point processes
- **ATUS 2024** (https://www.bls.gov/news.release/pdf/atus.pdf) —
  empirical activity-share priors (DIRICHLET_PRIOR)

---

## 7. Pitfalls (production gotchas)

### Bessel normalization is load-bearing

Layer 1 normalizes each von Mises component by I_0(κ). DO NOT drop the
divisor "to simplify". Without it, an activity with κ=8 (sharp peak)
has peak height exp(8)≈2980 while one with κ=2.5 (broad bell) peaks at
exp(2.5)≈12 — a 250× ratio. Softmax composition then gives the high-κ
activity ~98% probability mass even with 5× lower Dirichlet weight,
making the activity distribution effectively a single-activity step
function. PR 215-B QA iter-2 was the live demonstration of this
failure mode (eating dominated 09:00-21:00 in the plot before the fix).

### Branching-ratio drift at parameter changes

The constraint `α · E[w] < 1` is checked at module import (test
`test_AC_T1_3_004_branching_ratio_stable`). When ALPHA values change in
a future PR, that test is the regression guard — but the runtime never
re-checks. Phase 2's parameter-mutation paths (per-user weight overrides
from Bayesian state) MUST clamp at every mutation, not just init, or
self-excitation can creep in silently.

### Thinning-bound staleness at parameter discontinuities

`sample_next_wakeup` precomputes `λ_max` over a 1-hour proposal window.
At chapter-advance or rave-day swap (Phase 2), the underlying
`λ_baseline` shape changes; the cached upper bound becomes stale and may
under-bound the new intensity → biased samples. Phase 2 MUST re-bound at
parameter discontinuities explicitly.

### Recursive-intensity underflow at long gaps

For very long gaps (weeks of inactivity) `exp(−β · dt)` underflows to a
denormal. The `R = max(R, 0.0)` guard in `hawkes_decay` would NOT save
us if it were `max(R, 1.0)` (that breaks process death). The current
form (no clamp; relies on float64 monotonicity) is correct; do not
"defensively" add a clamp.

### Mardia-Jupp κ bias for small per-user samples (Phase 3 only)

The von Mises concentration estimator κ̂ ≈ R̂ · (2 − R̂²) / (1 − R̂²)
is biased upward for n < 50 events (Mardia-Jupp 2000). Phase 3 MUST
use the Banerjee approximation when per-user observation count is
below that threshold.

### Novel-territory burden

No production circadian × Hawkes agent appears in the 2024-2026
literature corpus we surveyed. The closest published analog is TiDeH
(Twitter retweet timing, 2016 — much shorter timescale). We carry the
validation burden ourselves: the live-vs-offline parity validator
(FR-016, Phase 2) is the only thing that will catch a divergence
between this offline model and production behavior in the long run.

---

## 8. Code Cross-References

- `nikita/heartbeat/intensity.py` — production module (~340 LOC)
  - `vonmises_mixture` — Layer 1 kernel
  - `activity_distribution` — Layer 1 softmax + ε floor
  - `lambda_baseline` — Layers 1-2-4 composition
  - `hawkes_decay`, `hawkes_update` — Layer 3 O(1) recursion
  - `lambda_total` — Layer 5 sum
  - `sample_next_wakeup` — Layer 6 Ogata thinning
  - `class HeartbeatIntensity` — per-instance RNG wrapper
- `tests/heartbeat/test_intensity.py` — 29 regression + behavioral tests
- `scripts/models/heartbeat_intensity_mc.py` — MC validator + 7 plots
- `nikita/config/settings.py:heartbeat_engine_enabled` — feature flag
- `supabase/migrations/20260418013800_create_nikita_daily_plan.sql` — PR
  215-A foundation table (referenced by Phase 2 planner)

---

## 9. Rollback Contract

Phase 1 ships behind `heartbeat_engine_enabled = False` (Spec 215 PR
215-A). To roll back:

1. Set `HEARTBEAT_ENGINE_ENABLED=false` in Cloud Run env (or simply leave
   default — never set to true in Phase 1).
2. No database state to clean up — `nikita_daily_plan` table can stay
   empty; nothing reads it without the flag.
3. The math module + MC + tests are pure-additive; reverting the merge
   commit is safe.

Phase 2 + 3 will document their own rollback paths in their model docs.

---

## 10. Future Work

- Phase 2: self-scheduling cron + weekend rave-mode swap + parity
  validator wiring (Spec 216 — to be created)
- Phase 3: per-user Bayesian state + reflection cycle (Spec 217 — to be
  created)
- Beyond Phase 3: voice-platform heartbeat integration; cross-user
  simulation (Nikita "having friends"); migration evaluation (pg_cron →
  Temporal.io / Prefect) if scale exceeds current substrate

---

## 11. Reproducibility

```bash
# Verify model integrity (sanity assertions only — fast)
uv run python scripts/models/heartbeat_intensity_mc.py
# Expected: 8/8 sanity checks PASS, exit 0

# Regenerate plots after parameter changes
uv run python scripts/models/heartbeat_intensity_mc.py --regen-plots
# Refreshes 7 PNGs in docs/models/

# Run all tests
uv run pytest tests/heartbeat/ -v
# Expected: 29 passed
```

Plot regeneration is opt-in (CI runs the sanity-only path). Refresh
when any tuning constant changes; the model doc table in §3 + the plot
captions are the only reviewer-visible audit trail.
