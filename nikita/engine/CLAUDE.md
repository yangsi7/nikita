# engine/ - Game Engine

## Purpose

Core game logic: scoring, chapter progression, decay, vice discovery, conflict handling.

## Current State

**Status**: ✅ Complete — All engine modules implemented and tested

```
engine/
├── constants.py         ✅ COMPLETE (148 lines)
│   ├─ CHAPTER_NAMES
│   ├─ BOSS_THRESHOLDS
│   ├─ DECAY_RATES
│   ├─ GRACE_PERIODS
│   ├─ METRIC_WEIGHTS
│   └─ CHAPTER_BEHAVIORS (5 chapters x 7 lines each)
│   # BOSS_ENCOUNTERS and CHAPTER_DAY_RANGES removed from __all__ (GE-004 — unused)
├── scoring/             ✅ COMPLETE (60 tests)
│   ├── models.py        # ResponseAnalysis, ViceSignal
│   ├── analyzer.py      # LLM-based analysis
│   ├── calculator.py    # ScoreCalculator class
│   └── service.py       # Scoring service
├── engagement/          ✅ COMPLETE (179 tests)
│   ├── models.py        # EngagementState enum
│   ├── state_machine.py # 6-state FSM
│   ├── detection.py     # Clingy/distant detection
│   ├── calculator.py    # Calibration multiplier
│   └── recovery.py      # Recovery mechanics
├── decay/               ✅ COMPLETE (44 tests)
│   ├── models.py        # Decay models
│   ├── calculator.py    # DecayCalculator
│   └── processor.py     # Decay processor
├── chapters/            ✅ COMPLETE (142 tests)
│   ├── __init__.py      # Exports
│   ├── boss.py          # BossStateMachine (threshold, pass/fail, game over, victory)
│   ├── prompts.py       # BOSS_PROMPTS (5 chapters)
│   └── judgment.py      # BossJudgment, BossResult, JudgmentResult
├── vice/                ✅ COMPLETE (70 tests)
│   ├── __init__.py      # Exports
│   ├── models.py        # ViceSignal, ViceAnalysisResult, ViceProfile
│   ├── analyzer.py      # ViceAnalyzer (LLM-based)
│   ├── scorer.py        # ViceScorer (profile management)
│   ├── injector.py      # VicePromptInjector (chapter-aware)
│   ├── boundaries.py    # ViceBoundaryEnforcer (ethical limits)
│   └── service.py       # ViceService (orchestration)
└── conflicts/           ✅ Integrated via Spec 027
    └── __init__.py
```

## Key Constants

### Scoring Formula (constants.py:51-57)
```python
METRIC_WEIGHTS = {
    "intimacy": Decimal("0.30"),    # 30% weight
    "passion": Decimal("0.25"),     # 25% weight
    "trust": Decimal("0.25"),       # 25% weight
    "secureness": Decimal("0.20"),  # 20% weight
}

# Composite = intimacy*0.30 + passion*0.25 + trust*0.25 + secureness*0.20
```

### Chapter System (YAML config via ConfigLoader — Spec 117)
```python
CHAPTER_NAMES = {
    1: "Curiosity",      # Days 1-14,   Boss: 55%, Decay: -0.8%/hr, Grace: 8h
    2: "Intrigue",       # Days 15-35,  Boss: 60%, Decay: -0.6%/hr, Grace: 16h
    3: "Investment",     # Days 36-70,  Boss: 65%, Decay: -0.4%/hr, Grace: 24h
    4: "Intimacy",       # Days 71-120, Boss: 70%, Decay: -0.3%/hr, Grace: 48h
    5: "Established",    # Days 121+,   Boss: 75%, Decay: -0.2%/hr, Grace: 72h
}
# Grace periods from YAML config (Spec 117): NATURAL order — veterans (Ch5)
# earn MORE grace (72h) than newcomers (Ch1=8h). Production uses get_config().
# Note: constants.py GRACE_PERIODS has INVERTED values (legacy, deprecated).
```

### Chapter Behaviors (constants.py:60-110)
```python
CHAPTER_BEHAVIORS[1] = """
- Response rate: 60-75% (skip messages)
- Response timing: 10min to 8 HOURS (unpredictable)
- Guarded, challenging, skeptical
"""

CHAPTER_BEHAVIORS[5] = """
- Response rate: 95-100%
- Response timing: CONSISTENT
- Complete authenticity with healthy boundaries
"""
```


## Vice Categories (8 Total)

```python
VICE_CATEGORIES = [
    "intellectual_dominance",  # Enjoys intellectual challenges
    "risk_taking",            # Attracted to danger, risk
    "substances",             # Open about drugs, alcohol
    "sexuality",              # Sexual content, innuendo
    "emotional_intensity",    # Deep emotional exchanges
    "rule_breaking",          # Anti-authority, norms
    "dark_humor",             # Morbid, dark jokes
    "vulnerability",          # Emotional openness, fears
]
```

## Patterns

### LLM-Based Analysis
```python
result = await agent.run(
    f"""Analyze this interaction:
    User: {user_message}
    Nikita: {nikita_response}

    Return metric deltas (-10 to +10).
    """,
)

analysis: ResponseAnalysis = result.data
# Returns: intimacy_delta, passion_delta, trust_delta, secureness_delta
```

### Score Update
```python
metrics.intimacy = clamp(metrics.intimacy + analysis.intimacy_delta, 0, 100)
metrics.passion = clamp(metrics.passion + analysis.passion_delta, 0, 100)
metrics.trust = clamp(metrics.trust + analysis.trust_delta, 0, 100)
metrics.secureness = clamp(metrics.secureness + analysis.secureness_delta, 0, 100)

composite = metrics.calculate_composite_score()
user.relationship_score = composite
```

## Documentation

- [Game Mechanics](../../memory/game-mechanics.md)
- [Scoring System](../../memory/game-mechanics.md#scoring-system-defined-in-constants)
- [Chapter System](../../memory/game-mechanics.md#chapter-system-constants-defined)

## Callers

- `nikita/pipeline/stages/game_state.py:25` — applies score deltas + chapter transitions per turn.
- `nikita/pipeline/stages/vice.py:21` — wires `engine/vice/service.py` (vice analyzer + boundaries + injector).
- `nikita/pipeline/stages/conflict.py:27` — uses `engine/conflict/` (conflict types + temperature).
- `nikita/api/routes/tasks.py:193 apply_daily_decay` — calls `engine/decay/processor.py` for hourly decay sweep.
- `nikita/api/routes/tasks.py:1006 touchpoints` — uses `engine/touchpoint/` for proactive scheduling.
- `nikita/agents/text/agent.py` — instructions imports `engine.chapters.prompts.get_boss_prompt(chapter)` for per-chapter context.

## Gotchas

- **`GRACE_PERIODS` in `constants.py:152-158` is INVERTED vs yaml** (Ch1=72h ↔ Ch5=8h). Production reads `nikita/config_data/decay.yaml:6-11` via `ConfigLoader`; constants kept as DEPRECATED mirror. Guard test at `tests/engine/test_grace_period_divergence.py`.
- **`CALIBRATION_MULTIPLIERS` python literals at `scoring/calculator.py:20-27` (IN_ZONE=1.0/CALIBRATING=0.9/DRIFTING=0.8/DISTANT=0.6/CLINGY=0.5/OUT_OF_ZONE=0.2) CONTRADICT `engagement_multipliers` in `scoring.yaml:53-59`**. The yaml has different state names + values. Both are live; production code uses python literals (W4 audit).
- **Engagement multipliers apply ONLY to POSITIVE deltas** (`scoring/calculator.py:80-109`). Negative deltas stay full (penalty preservation). KT framing of "weighted sum × multiplier" is wrong.
- **`CHAPTER_DELTA_CAPS` (3.0/2.5/2.0/1.5/1.0 per Ch1-5)** at `scoring/calculator.py:31-37` — bare Decimal literals not surfaced in YAML/settings. GH #196 score-acceleration guard.
- **Boss is a SINGLE class** `BossStateMachine` at `chapters/boss.py:64`. NO chapter-specific subclasses. NO `boss_encounter.py` / `boss_judgment.py` / `state_machine.py` files (KT names are stale; W4 audit).
- **`BossPhase` enum has only 2 values** (`OPENING`, `RESOLUTION`) at `chapters/boss.py:33-41`. Spec 058 multi-phase.
- **`BossResult` enum has 4 values** (`PASS`, `FAIL`, `PARTIAL`, `ERROR`) at `chapters/judgment.py:26`. `ERROR` doesn't count toward 3-fail game-over.
- **Real metric names = `intimacy / passion / trust / secureness`** — NOT arousal/attachment/respect/compatibility (KT/audit drift; corrected in W4).
- **`apply_warmth_bonus`** at `scoring/calculator.py:227-255` — vulnerability-exchange trust bonus +2/+1/+0 (diminishing) for V-exchange counts 0/1/2+. Spec 058.
- **`max_decay_per_cycle = Decimal("20.0")`** at `decay/calculator.py:45,103-104` — cap to prevent catastrophic decay from long absences.
- **Deprecated constants still in `__all__`** (`constants.py:113-138`): `BOSS_THRESHOLDS`, `DECAY_RATES`, `GRACE_PERIODS`, `METRIC_WEIGHTS`, `CHAPTER_NAMES`. Production reads via `get_config()` (yaml-authoritative); the constants are legacy mirrors. Don't import from `constants.py` for new code.
- **Real chapter names**: Curiosity / Intrigue / Investment / Intimacy / Established (`config_data/chapters.yaml:6,14,22,30,38`). Schema is `name, day_range, boss_threshold, description` (no `vices_unlocked` or `behaviors` keys — those are KT fabrication).
- **Vice subsystem in `engine/vice/`** (singular `vice/`, NOT `vices/`). 8 vice categories at `nikita/db/models/user.py:393-403`: intellectual_dominance, risk_taking, substances, sexuality, emotional_intensity, rule_breaking, dark_humor, vulnerability.

## Navigation

- Backend module map: [`../CLAUDE.md`](../CLAUDE.md)
- Game mechanics canonical: [`../../memory/game-mechanics.md`](../../memory/game-mechanics.md) (W4 code-verified additions)
- Vice subsystem: [`vice/CLAUDE.md`](vice/CLAUDE.md)
- Stochastic-model rule: [`../../.claude/rules/stochastic-models.md`](../../.claude/rules/stochastic-models.md)
- Tuning-constants rule: [`../../.claude/rules/tuning-constants.md`](../../.claude/rules/tuning-constants.md)

Last verified: 2026-05-05
