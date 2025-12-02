# engine/ - Game Engine

## Purpose

Core game logic: scoring, chapter progression, decay, vice discovery, conflict handling.

## Current State

**Phase 1 ✅**: Constants defined and audited (Dec 2025)
**Phase 3 ❌**: Implementation TODO (see specs 003, 004, 005, 006, 014)

```
engine/
├── constants.py         ✅ COMPLETE (148 lines)
│   ├─ CHAPTER_NAMES
│   ├─ BOSS_THRESHOLDS
│   ├─ DECAY_RATES
│   ├─ GRACE_PERIODS
│   ├─ METRIC_WEIGHTS
│   ├─ CHAPTER_BEHAVIORS (5 chapters x 7 lines each)
│   └─ BOSS_ENCOUNTERS
├── scoring/             ❌ TODO Phase 3
│   ├── calculator.py    # ScoreCalculator class
│   ├── analyzer.py      # ResponseAnalysis (LLM-based)
│   └── metrics.py       # Metric update logic
├── chapters/            ❌ TODO Phase 3
│   ├── state_machine.py # ChapterStateMachine
│   └── boss_encounters.py # Boss logic
├── decay/               ❌ TODO Phase 3
│   ├── calculator.py    # DecayCalculator
│   └── scheduler.py     # Celery integration
├── vice/                ❌ TODO Phase 3
│   ├── discovery.py     # ViceDiscovery
│   ├── categories.py    # 8 categories logic
│   └── intensity.py     # Intensity tracking
└── conflicts/           ❌ TODO Phase 3
    ├── detector.py      # Conflict type detection
    └── resolution.py    # Resolution scoring
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

### Chapter System (constants.py - updated Dec 2025)
```python
CHAPTER_NAMES = {
    1: "Curiosity",      # Days 1-14,   Boss: 55%, Decay: -0.8%/hr, Grace: 8h
    2: "Intrigue",       # Days 15-35,  Boss: 60%, Decay: -0.6%/hr, Grace: 16h
    3: "Investment",     # Days 36-70,  Boss: 65%, Decay: -0.4%/hr, Grace: 24h
    4: "Intimacy",       # Days 71-120, Boss: 70%, Decay: -0.3%/hr, Grace: 48h
    5: "Established",    # Days 121+,   Boss: 75%, Decay: -0.2%/hr, Grace: 72h
}
# Note: Decay is now HOURLY (compressed game), grace periods compressed too
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

## Target Implementation (Phase 3)

### ScoreCalculator
```python
class ScoreCalculator:
    async def analyze_response(
        self,
        user_message: str,
        nikita_response: str,
        context: ConversationContext,
    ) -> ResponseAnalysis:
        """Use LLM to analyze interaction, return metric deltas"""

    async def apply_deltas(
        self,
        user_id: UUID,
        analysis: ResponseAnalysis,
    ) -> Decimal:
        """Apply deltas to user_metrics, recalculate composite"""
```

### ChapterStateMachine
```python
class ChapterStateMachine:
    async def check_advancement(self, user_id: UUID) -> bool:
        """Check if boss threshold met"""

    async def trigger_boss(self, user_id: UUID) -> BossEncounter:
        """Initialize boss fight, set game_status"""

    async def handle_boss_result(
        self,
        user_id: UUID,
        passed: bool,
    ) -> BossResult:
        """Advance chapter on pass, increment attempts on fail"""
```

### DecayCalculator
```python
class DecayCalculator:
    async def apply_decay(self, user_id: UUID):
        """Apply decay if past grace period"""
        user = await get_user(user_id)
        grace = GRACE_PERIODS[user.chapter]
        time_since = now() - user.last_interaction_at

        if time_since > grace:
            decay = DECAY_RATES[user.chapter]
            new_score = max(0, user.relationship_score - decay)
            await update_score(user_id, new_score, 'decay')
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
