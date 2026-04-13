# Response Timing Model — Spec 210 v2

Log-normal × chapter × momentum model for Nikita's new-conversation reply delay.

**Code**: `nikita/agents/text/timing.py` (ResponseTimer), `nikita/agents/text/conversation_rhythm.py` (compute_momentum)
**Spec**: `specs/210-kill-skip-variable-response/spec.md`
**Validator**: `scripts/models/response_timing_mc.py`
**Artifact**: `portal/src/app/admin/research-lab/response-timing/page.tsx`

---

## 1. Problem Statement

The original timing model (`TIMING_RANGES` in `timing.py`) sampled from a Gaussian over five per-chapter ranges. The direction was **inverted**: Chapter 1 (infatuation) produced the longest delays (10 min – 8 h), while Chapter 5 (settled) produced the shortest (5 – 30 min). This caused Chapter 1 players to receive replies hours late, silently losing messages and creating a broken first impression.

Additionally, a skip-rate feature randomly suppressed responses entirely. Both behaviors are deleted in Spec 210.

---

## 2. Base Distribution: Log-Normal

Human messaging response times follow a log-normal distribution (Stouffer et al. 2006, challenging Barabási 2005's power-law claim). Properties:

- **Right-skewed**: usually fast, occasionally slow — matches human intuition
- **Multiplicative process**: delay = (notice notification) × (unlock phone) × (read) × (compose) × (send). Independent multiplicative factors → CLT on log scale → log-normal
- **Finite variance**: unlike Pareto/power-law, tail is controllable via hard cap
- **No negative values**: unlike Gaussian

The base sample:

```
delay_base = exp(μ + σ · Z)    where Z ~ N(0, 1)
```

| Parameter | Value | Meaning |
|-----------|-------|---------|
| μ | 2.996 | log-median = exp(μ) ≈ 20 seconds |
| σ | 1.714 | log-spread; p90 base ≈ 3 minutes |

---

## 3. Chapter Coefficients (Excitement-Fades Model)

Nikita's 5 chapters model relationship progression from infatuation to settled partnership. The chapter coefficient `c_ch` scales the base delay:

| Chapter | Name | Coefficient | Median delay |
|---------|------|-------------|-------------|
| 1 | Infatuation | 0.15 | 3.0 s |
| 2 | Very eager | 0.30 | 5.9 s |
| 3 | Attentive | 0.50 | 9.9 s |
| 4 | Comfortable | 0.75 | 15.3 s |
| 5 | Settled | 1.00 | 20.3 s |

**Rationale (excitement-fades)**: Romantic infatuation produces heightened responsiveness (Fisher 2004 — dopamine/norepinephrine). As relationships stabilize, response urgency decreases (Berger & Calabrese 1975 — Uncertainty Reduction Theory; Scissors et al. 2014 — established partners reply slower). Nikita is explicitly eager in early chapters per game design.

**Rejected alternative (investment-deepens)**: Ch1 slow ("playing cool"), Ch5 fast. Would fit pre-mutual-interest but contradicts Nikita's eager persona in early chapters.

---

## 4. Per-Chapter Hard Caps

Each chapter has an absolute ceiling preventing extreme tail samples from producing absurd delays:

| Chapter | Cap | Rationale |
|---------|-----|-----------|
| 1 | 10 s | Near-zero-wait guarantee. Even 10σ tail → clamped. |
| 2 | 60 s | One minute ceiling for eager phase. |
| 3 | 5 min | Attentive but not glued to phone. |
| 4 | 15 min | Comfortable pauses are natural. |
| 5 | 30 min | Settled partner; longest acceptable gap. |

At-cap rates from MC validation (N=50,000): Ch1 24.1%, Ch2 8.9%, Ch3 2.5%, Ch4 0.9%, Ch5 0.4%.

---

## 5. Momentum Coefficient M

A multiplicative layer that adapts Nikita's responsiveness to the user's recent messaging cadence.

### Formula

```
B_ch = chapter_baseline_seconds[ch]    # {1:300, 2:240, 3:180, 4:120, 5:90}
α    = 0.35                            # EWMA smoothing factor

S ← B_ch                              # seed EWMA at prior (chapter baseline)
for g in gap_history[-10:]:            # most recent ≤10 gaps, user-turn only
    S ← α · g + (1 − α) · S

M = clip(S / B_ch, 0.1, 5.0)
```

### Behavior

| User pattern | Gap range | M | Effect |
|-------------|-----------|---|--------|
| Rapid fire | 5-10 s | < 0.3 | Nikita speeds up dramatically |
| Normal conversation | ~baseline | ≈ 1.0 | Neutral |
| Slow responder | 500-800 s | > 1.5 | Nikita slows to match |
| Cold start (no history) | — | 1.0 | Falls back to prior |

### Bayesian Interpretation

The EWMA seeded at `B_ch` is equivalent to the posterior mean under a Normal-Normal conjugate model:

- **Prior**: `μ_p ~ N(log B_ch, σ_prior²)` with `σ_prior = 0.8`
- **Observations**: `log(g) ~ N(μ_p, σ_obs²)` with `σ_obs = 0.6`
- **Update weight**: `α ≈ σ_obs² / (σ_obs² + σ_prior² · N)`

At α = 0.35, the posterior contracts appropriately after ~3 observations. The chapter baseline acts as the prior; the user's actual cadence updates it. This gives rigorous Bayesian framing without introducing PyMC or a particle filter.

### Gap Extraction

`_compute_user_gaps(messages)` in `conversation_rhythm.py`:

1. Filter to `role == "user"` messages only
2. Parse timestamps via `datetime.fromisoformat()`
3. Sort chronologically (defensive)
4. Compute consecutive deltas in seconds
5. Drop deltas ≥ 900 s (session breaks, matching `TEXT_SESSION_TIMEOUT_MINUTES=15`)
6. Floor sub-second deltas at 1.0 s
7. Return last 10 deltas (oldest first)

---

## 6. Full Formula

```
delay = min(cap_ch, exp(μ + σ · Z) × c_ch × M)
```

where:
- `Z ~ N(0, 1)` — standard normal (Box-Muller in JS artifact, `random.gauss` in Python)
- `c_ch` — chapter coefficient from §3
- `M` — momentum coefficient from §5
- `cap_ch` — per-chapter hard cap from §4

**Fires only** on new-conversation starts (≥15 min gap since last message). In-session replies always return 0 delay. Boss fights always return 0 delay.

---

## 7. Parameter Summary

| Parameter | Value | Source | Override |
|-----------|-------|--------|----------|
| μ (log-median) | 2.996 | `timing.py:60` | — |
| σ (log-spread) | 1.714 | `timing.py:61` | — |
| Chapter coefficients | {1:0.15, 2:0.30, 3:0.50, 4:0.75, 5:1.00} | `timing.py:65-73` | — |
| Chapter caps (s) | {1:10, 2:60, 3:300, 4:900, 5:1800} | `timing.py:75-83` | `CHAPTER_CAPS_SECONDS_OVERRIDE` |
| Chapter baselines (s) | {1:300, 2:240, 3:180, 4:120, 5:90} | `conversation_rhythm.py:55-63` | — |
| α (EWMA) | 0.35 | `conversation_rhythm.py:67` | `MOMENTUM_ALPHA` |
| M bounds | [0.1, 5.0] | `conversation_rhythm.py:72-73` | `MOMENTUM_LO`, `MOMENTUM_HI` |
| Window size | 10 | `conversation_rhythm.py:82` | — |
| Session break | 900 s | `conversation_rhythm.py:78` | — |
| Feature flag | `momentum_enabled=True` | `settings.py` | `MOMENTUM_ENABLED=false` |

**Rollback**: `MOMENTUM_ENABLED=false` collapses M to 1.0 (model degrades to v1 log-normal × chapter).

---

## 8. Monte Carlo Validation

Run: `uv run python scripts/models/response_timing_mc.py` (exit 0 = all pass, <2 s)

### Percentile Distribution (N=50,000)

| Chapter | Coeff | Cap | p50 | p75 | p90 | p99 | @cap |
|---------|-------|-----|-----|-----|-----|-----|------|
| 1 | 0.15 | 10 s | 3.0 s | 9.5 s | 10.0 s | 10.0 s | 24.1% |
| 2 | 0.30 | 60 s | 5.9 s | 18.9 s | 53.5 s | 60.0 s | 8.9% |
| 3 | 0.50 | 5 m | 9.9 s | 31.8 s | 1.5 m | 5.0 m | 2.5% |
| 4 | 0.75 | 15 m | 15.3 s | 48.3 s | 2.3 m | 13.2 m | 0.9% |
| 5 | 1.00 | 30 m | 20.4 s | 1.1 m | 3.0 m | 18.1 m | 0.4% |

### Assertions (all pass)

1. **Ch1 cap enforcement**: max(Ch1 delays) ≤ 10 s
2. **Ch1 near-zero wait**: median(Ch1) < 5 s (actual: 3.0 s)
3. **Monotonic medians**: Ch1 < Ch2 < Ch3 < Ch4 < Ch5
4. **Feedback spiral bounded**: 200 sessions × 20 msgs with user mirroring Nikita delay ×0.5 → avg session length 1.8 min (bounded)
5. **EWMA unbiased**: 10k sessions drawn from log-normal(mean=B_ch) → E[M] = 1.00 ± 0.05

### Generated Plots

- `docs/models/response-timing-histogram.png` — log-scale histogram by chapter
- `docs/models/response-timing-cdf.png` — CDF curves by chapter
- `docs/models/response-timing-momentum-traces.png` — M vs message # for 5 canonical gap sequences
- `docs/models/response-timing-percentiles.csv` — raw percentile data

---

## 9. Pitfalls

### Feedback Spiral
If Nikita's delay feeds back into the user's gap, a positive feedback loop could amplify delays indefinitely. Bounded by:
- Hard cap per chapter (§4)
- M bounds [0.1, 5.0] (§5)
- MC validation confirms bounded sessions even at mirror_coeff=0.5

### Session Contamination
Gaps ≥ 900 s are session breaks, not conversational rhythm. Including them would inflate M toward the ceiling. `_compute_user_gaps` filters them out. The 900 s threshold matches `TEXT_SESSION_TIMEOUT_MINUTES=15` exactly.

### Chapter-Transition Discontinuity
When a user advances from Ch3 to Ch4, the chapter coefficient jumps from 0.50 to 0.75 (50% increase). The momentum baseline also shifts from 180 s to 120 s. This produces a one-shot discontinuity in expected delay. Acceptable because chapter transitions are infrequent (days/weeks apart) and the change direction matches design intent (settling produces longer delays).

### α Sensitivity
α = 0.35 means ~65% weight on the prior after 1 observation, ~42% after 2, ~28% after 3. The MC validator sweeps α ∈ {0.2, 0.35, 0.5} to confirm the chosen value balances responsiveness against stability. Lower α → smoother, slower adaptation. Higher α → noisier, faster adaptation.

### Timezone Naivety
`add_message()` writes naive local-time ISO strings. Gap deltas are computed within the same naive space (consistent). Do not mix with `last_message_at` (tz-aware UTC column).

---

## 10. Citations

- Barabási, A.-L. (2005). "The origin of bursts and heavy tails in human dynamics." *Nature*, 435, 207–211.
- Stouffer, S.A., Malmgren, R.D., & Amaral, L.A.N. (2006). "Log-normal statistics in e-mail communication." Critique of Barabási — log-normal outperforms power-law.
- Wu, Y., Zhou, C., Xiao, J., Kurths, J., & Schellnhuber, H.J. (2010). "Evidence for a bimodal distribution in human communication." *PNAS*, 107(44), 18803–18808.
- Malmgren, R.D., Stouffer, D.B., Campanharo, A.S., & Amaral, L.A.N. (2009). "On universality in human correspondence activity." *Science*, 325(5948), 1696–1700.
- Hawkes, A.G. (1971). "Spectra of some self-exciting and mutually exciting point processes." *Biometrika*, 58(1), 83–90.
- Sacks, H., Schegloff, E.A., & Jefferson, G. (1974). "A simplest systematics for the organization of turn-taking for conversation." *Language*, 50(4), 696–735.
- Avrahami, D., & Hudson, S.E. (2006). "Responsiveness in instant messaging." *CHI*, 731–740.
- Jacobson, D. (1988). "The technological transformation of the social sciences." *British Journal of Sociology*, 39(2), 152–178.
- Fisher, H. (2004). *Why We Love: The Nature and Chemistry of Romantic Love.* Henry Holt.
- Berger, C.R., & Calabrese, R.J. (1975). "Some explorations in initial interaction and beyond." *Human Communication Research*, 1(2), 99–112.
- Scissors, L., Burke, M., & Wengrovitz, S. (2014). "In Text We Trust: The Role of Texting in Romantic Relationships." *CSCW*.

---

## 11. Deprecation Notes

This model supersedes:
- **Spec 026 AC-5.x**: Original per-chapter Gaussian timing ranges
- **`TIMING_RANGES`**: Kept in `timing.py` for reference but no longer used by `calculate_delay()`
- **Skip-rate feature**: `skip.py` module is dead code; handler ignores it. Delete in follow-up PR.
