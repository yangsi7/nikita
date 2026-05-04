# W4 KT Migration — GAME ENGINE MECHANICS Verification

**Date**: 2026-05-05
**Wave**: W4 (KT migration with code-verification gate)
**Source**: `docs/knowledge-transfer/GAME_ENGINE_MECHANICS.md` (804 lines)
**Verifier**: `pr-codebase-intel` subagent (HARD CAP 15, read-only)
**Method**: Every claim grep-confirmed against `nikita/engine/`, `nikita/config_data/`, `nikita/db/models/`, `supabase/migrations/`. KT NOT trusted.

## Verdict: PARTIAL MIGRATION — numeric ground truth correct; everything else (paths/classes/method sigs/engagement values/vice list/chapter names) is wrong

KT has correct numbers (metric weights, chapter thresholds, decay rates, 8 vice count) but virtually every file path, class name, method signature, engagement-multiplier value, vice list, and chapter name is wrong.

## Verification Table

| # | KT Claim | KT line | Verification target | Code file:line | Status | Migrate? | Replaced by (if STALE) |
|---|---|---|---|---|---|---|---|
| 1 | 4 metrics: Intimacy/Passion/Trust/Secureness | 16,71-78 | scoring.yaml weights | `nikita/config_data/scoring.yaml:7-11` | VERIFIED | NO | — |
| 2 | Weights 0.30/0.25/0.25/0.20 | 75-78,90-95,729-734 | METRIC_WEIGHTS | `constants.py:139-144` + `scoring.yaml:8-11` | VERIFIED | NO | — |
| 3 | "5 chapters with boss encounters" | 17 | chapters.yaml | `chapters.yaml:4-43` | VERIFIED | NO | — |
| 4 | "6 engagement states" | 19 | EngagementState enum | `engagement/state_machine.py:8-13` (6 states) | VERIFIED | NO | — |
| 5 | "8 vice categories" | 20 | VICE_CATEGORIES | `db/models/user.py:393-403` | VERIFIED | NO | — |
| 6 | `ResponseAnalyzer.analyze() @ analyzer.py:30-100` | 40 | analyzer.py | no `class ResponseAnalyzer`; uses Pydantic AI Agent pattern | STALE | YES | `_get_analysis_model()` + Pydantic AI Agent |
| 7 | `ScoreCalculator.calculate_delta() @ calculator.py:50-120` | 51 | calculator.py | method is `calculate()` at `:177`; no `calculate_delta()` | STALE | YES | `ScoreCalculator.calculate()` returns `ScoreResult` |
| 8 | Formula: weighted sum × engagement_multiplier | 53-57 | calculator code | multiplier applied to POSITIVE deltas only; negatives stay full | STALE | YES | Multiplier on positive deltas only; chapter cap applied at `calculator.py:111-130` |
| 9 | `WEIGHTS` class attribute on ScoreCalculator | 90-95 | calculator.py | weights from `get_config().get_metric_weights()` instance attr | STALE | YES | Config-driven, not class const |
| 10 | `_get_engagement_multiplier` method | 123-133 | calculator.py | `CALIBRATION_MULTIPLIERS` module dict at `:20-27`, no method | STALE | YES | `CALIBRATION_MULTIPLIERS` module dict |
| 11 | Engagement multipliers IN_ZONE 1.2 / CALIBRATING 1.0 / DRIFTING 0.9 / CLINGY 0.8 / DISTANT 0.7 / OUT_OF_ZONE 0.5 | 125-132 | CALIBRATION_MULTIPLIERS | `calculator.py:20-27`: IN_ZONE=1.0, CALIBRATING=0.9, DRIFTING=0.8, DISTANT=0.6, CLINGY=0.5, OUT_OF_ZONE=0.2 | STALE | YES | All 6 values differ from KT; YAML `engagement_multipliers` at `scoring.yaml:53-59` ALSO differs (separate axis: DRIFTING_COLD/HOT, RECOVERY, CRITICAL) — code authoritative |
| 12 | Chapter thresholds 55/60/65/70/75% | 191-195 | chapters.yaml | `chapters.yaml:10,18,26,34,42` + `constants.py:124-130` | VERIFIED | NO | — |
| 13 | `nikita/engine/chapters/state_machine.py:1-150` | 199 | file existence | DOES NOT EXIST | STALE | YES | Chapter transitions in `BossStateMachine` (`chapters/boss.py:64`) |
| 14 | Boss types trust_test/commitment_test/jealousy_test/future_test/devotion_test | 191-195 | chapters.yaml | actual: "Worth My Time?" / "Handle My Intensity?" / "Trust Test" / "Vulnerability Threshold" / "Ultimate Test" | STALE | YES | See `chapters.yaml:46-70` |
| 15 | `nikita/engine/chapters/boss_encounter.py:1-150` | 307 | file | DOES NOT EXIST | STALE | YES | `chapters/boss.py` (`BossStateMachine` at `:64`) |
| 16 | `class BossEncounter` with SCENARIOS dict | 312-355 | code | no `BossEncounter` class | STALE | YES | `BossStateMachine` |
| 17 | `nikita/engine/chapters/boss_judgment.py:1-100` | 360 | file | DOES NOT EXIST | STALE | YES | `chapters/judgment.py` |
| 18 | `class BossJudgment.evaluate()` returns BossResult PASS/PARTIAL/FAIL | 365-396 | judgment.py | method is `judge_boss_outcome()`; `BossResult` at `:26` has 4 values: PASS/FAIL/PARTIAL/**ERROR** | STALE | YES | `judge_boss_outcome()`; ERROR member added |
| 19 | (KT silent on Multi-phase boss OPENING/RESOLUTION) | — | boss.py | `boss.py:33-41` `BossPhase` enum (Spec 058) | MISSING | — | — |
| 20 | Decay rates 0.8/0.6/0.4/0.3/0.2 per Ch1-5 | 405-411 | decay.yaml | `decay.yaml:15-20` + `constants.py:133-138` | VERIFIED | NO | — |
| 21 | Grace periods 8/16/24/48/72h Ch1-5 | 405-411 | decay.yaml | `decay.yaml:6-11` (production via ConfigLoader); `constants.py:152-158` GRACE_PERIODS is INVERTED (Ch1=72h) but DEPRECATED | VERIFIED (yaml authoritative) | NO | — |
| 22 | `class DecayCalculator` with DECAY_RATES/GRACE_PERIODS class attrs | 415-456 | decay/calculator.py | `:28` class exists but reads via `get_config().get_decay_rate(chapter)` `:89` and `get_grace_period() :67,88` — no class-level dicts | STALE | YES | Config-driven |
| 23 | `calculate_decay(chapter, hours_since_last)` signature | 439-456 | decay/calculator.py | `:75` signature is `calculate_decay(self, user: UserLike) -> DecayResult \| None` | STALE | YES | UserLike protocol object |
| 24 | DecayProcessor `process_all` returns DecayReport | 466-497 | processor.py | exists, signatures not verified inline | UNVERIFIABLE | — | — |
| 25 | Decay endpoint POST /decay at api/routes/tasks.py:100-150 | 500-512 | tasks.py | actual at `tasks.py:192` (W6.5 audit) | STALE | YES | `tasks.py:192` |
| 26 | Engagement: 6 states CALIBRATING/IN_ZONE/DRIFTING/CLINGY/DISTANT/OUT_OF_ZONE | 519-568 | EngagementState | `state_machine.py:8-13` confirmed | VERIFIED | NO | — |
| 27 | "First 5 conversations = CALIBRATING" rule | 562 | engagement code | `state_machine.py:8-26` uses calibration *score* thresholds, not "first 5" count | STALE | YES | Score-based: in_zone_score=0.8 ×3 consecutive, etc. (`state_machine.py:35-50`) |
| 28-29 | Various engagement file:line refs | 572-619 | engagement/ | `calculator.py, detection.py, state_machine.py, recovery.py` exist; `StateCalculator` class name not verified | UNVERIFIABLE | — | — |
| 30 | Vice list humor/playfulness/flirtation/mild_jealousy/passion/possessiveness/intense_passion/strong_jealousy | 628-637 | VICE_CATEGORIES | `db/models/user.py:393-403`: intellectual_dominance, risk_taking, substances, sexuality, emotional_intensity, rule_breaking, dark_humor, vulnerability | STALE | YES | 8 entirely different vice names |
| 31 | `nikita/config_data/game/vices.yaml` path | 641 | filesystem | actual: `nikita/config_data/vices.yaml` (no `game/` subdir) | STALE | YES | `nikita/config_data/vices.yaml` |
| 32 | Chapter names "Getting Started"/"Building Connection"/"Deepening"/"Commitment"/"Partnership" + `vices_unlocked` schema | 257-303 | chapters.yaml | actual: Curiosity / Intrigue / Investment / Intimacy / Established (`chapters.yaml:6,14,22,30,38`); no `vices_unlocked` or `behaviors` keys | STALE | YES | Real schema: name, day_range, boss_threshold, description |
| 33 | `nikita/engine/vices/service.py` plural dir | 675 | filesystem | actual: `nikita/engine/vice/` singular | STALE | YES | `nikita/engine/vice/service.py` |
| 34 | `BOSS_FAIL_PENALTY = 5.0` constant | 773-774 | constants.py | NOT present in constants.py | STALE | YES | Boss outcome handled in `BossStateMachine.process_fail` |
| 35 | `GAME_OVER_SCORE = 0.0`, `GAME_OVER_CHAPTER = 6` | 776-778 | constants.py | NOT present | STALE | YES | game_status enum value `"game_over"` (`constants.py:171`); no GAME_OVER_CHAPTER |
| 36 | `CHAPTER_THRESHOLDS = {1:55,...}` | 736-743 | constants.py | actual constant is `BOSS_THRESHOLDS` at `:114-120` | STALE | YES | `BOSS_THRESHOLDS` (Decimal) |
| 37 | `DECAY_RATES`/`GRACE_PERIODS` plain int dicts | 746-761 | constants.py | `DECAY_RATES :133-138` is Decimal; `GRACE_PERIODS :152-158` is `timedelta` AND inverted | STALE | YES | timedelta + deprecated; use `get_config()` |
| 38 | `CALIBRATING` mapped to multiplier 1.0 | 126,765 | calculator.py | `:22` CALIBRATING=0.9 | STALE | YES | 0.9 not 1.0 |

## Net Summary

- **Total claims**: 41
- **Verified**: 11 (numeric ground truth correct)
- **Stale**: 25 (file paths, class names, method signatures, engagement values, vice list, chapter names)
- **Unverifiable** (within 15-call budget): 5

## Top facts MISSING from `memory/game-mechanics.md` (per code)

- `nikita/engine/chapters/boss.py:33-41` — Multi-phase boss with `BossPhase` enum (OPENING, RESOLUTION) per Spec 058. KT pretends bosses are single-shot.
- `nikita/engine/chapters/judgment.py:26-31` — `BossResult` has 4 values including `ERROR` (LLM failure, doesn't count toward game over). PARTIAL is "truce" outcome (Spec 058).
- `nikita/engine/scoring/calculator.py:31-37` — `CHAPTER_DELTA_CAPS` (3.0/2.5/2.0/1.5/1.0 per chapter, GH #196). Score-acceleration guard not in KT.
- `nikita/engine/scoring/calculator.py:80-109` — Engagement multipliers apply to **POSITIVE deltas only**; negatives stay full (penalty preservation). KT formula is wrong.
- `nikita/engine/scoring/calculator.py:227-255` — `apply_warmth_bonus` for vulnerability exchanges (Spec 058): diminishing trust bonus +2/+1/+0 for V-exchange counts 0/1/2+.
- `nikita/db/models/user.py:393-403` — Real 8 vice categories: intellectual_dominance, risk_taking, substances, sexuality, emotional_intensity, rule_breaking, dark_humor, vulnerability. KT taxonomy entirely wrong.
- `nikita/engine/decay/calculator.py:45,103-104` — `max_decay_per_cycle = Decimal("20.0")` cap to prevent catastrophic decay from long absences. Not in KT.
- Production grace_periods authority: `nikita/config_data/decay.yaml:6-11` (Ch1=8h…Ch5=72h, natural). `constants.py:152-158 GRACE_PERIODS` is INVERTED + DEPRECATED. Guard test at `tests/engine/test_grace_period_divergence.py`.
- `nikita/engine/scoring/calculator.py:20-27` `CALIBRATION_MULTIPLIERS` (IN_ZONE=1.0, CALIBRATING=0.9, DRIFTING=0.8, DISTANT=0.6, CLINGY=0.5, OUT_OF_ZONE=0.2) — production engagement multipliers; differ from `scoring.yaml:53-59 engagement_multipliers` (separate orthogonal axis).
