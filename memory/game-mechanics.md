# Game Mechanics

## Current State

### Scoring System (Defined in Constants)

**Composite Score Formula** (nikita/engine/constants.py:51-57):

```python
METRIC_WEIGHTS = {
    "intimacy": Decimal("0.30"),    # 30% weight
    "passion": Decimal("0.25"),     # 25% weight
    "trust": Decimal("0.25"),       # 25% weight
    "secureness": Decimal("0.20"),  # 20% weight
}

# Composite = intimacy*0.30 + passion*0.25 + trust*0.25 + secureness*0.20
# Implemented in: nikita/db/models/user.py:155-166
```

**Score Ranges**:
- 0-100%: All metrics clamped to this range
- Starting score: 50% across all metrics (nikita/config/settings.py:77)
- Game over: 0%
- Victory condition: Pass Chapter 5 boss (75%+ required)

**Hidden Metrics** (nikita/db/models/user.py:130-150):

```
Intimacy (30%)      - Emotional closeness, vulnerability shared
Passion (25%)       - Excitement, sexual tension, playfulness
Trust (25%)         - Reliability, honesty, consistency
Secureness (20%)    - Confidence in relationship, no clinginess
```

### Chapter System (Constants Defined)

**Chapter Progression** (nikita/engine/constants.py - compressed game Dec 2025):

```
┌──────────────────────────────────────────────────────────────┐
│ Chapter 1: CURIOSITY                                         │
│ Days: 1-3 | Boss: 55% | Decay: -0.8%/hr | Grace: 8h        │
│ "Are you worth my time?"                                     │
└─────────────────────┬────────────────────────────────────────┘
                      │ Boss Pass
                      ▼
┌──────────────────────────────────────────────────────────────┐
│ Chapter 2: INTRIGUE                                          │
│ Days: 4-7 | Boss: 60% | Decay: -0.6%/hr | Grace: 16h       │
│ "Can you handle my intensity?"                               │
└─────────────────────┬────────────────────────────────────────┘
                      │ Boss Pass
                      ▼
┌──────────────────────────────────────────────────────────────┐
│ Chapter 3: INVESTMENT                                        │
│ Days: 8-11 | Boss: 65% | Decay: -0.4%/hr | Grace: 24h      │
│ "Trust test" (jealousy/external pressure)                   │
└─────────────────────┬────────────────────────────────────────┘
                      │ Boss Pass
                      ▼
┌──────────────────────────────────────────────────────────────┐
│ Chapter 4: INTIMACY                                          │
│ Days: 12-16 | Boss: 70% | Decay: -0.3%/hr | Grace: 48h     │
│ "Vulnerability threshold" (share something real)             │
└─────────────────────┬────────────────────────────────────────┘
                      │ Boss Pass
                      ▼
┌──────────────────────────────────────────────────────────────┐
│ Chapter 5: ESTABLISHED                                       │
│ Days: 17-21 | Boss: 75% | Decay: -0.2%/hr | Grace: 72h     │
│ "Ultimate test" (partnership + independence)                │
└─────────────────────┬────────────────────────────────────────┘
                      │ Boss Pass
                      ▼
                  🏆 VICTORY
```

### Boss Encounters (Constants Defined)

**Boss Structure** (nikita/engine/constants.py:113-139):

```python
BOSS_ENCOUNTERS = {
    1: {
        "name": "Worth My Time?",
        "trigger": "Are you worth my time?",
        "challenge": "Intellectual challenge - prove you can engage her brain",
    },
    2: {
        "name": "Handle My Intensity?",
        "trigger": "Can you handle my intensity?",
        "challenge": "Conflict test - stand your ground without folding or attacking",
    },
    # ... etc
}
```

**Boss Mechanics** (Defined, TODO: Implement):
- Max 3 attempts per boss (nikita/config/settings.py:78)
- Failed boss → attempts++, score impact
- 3rd failure → GAME_OVER
- Pass boss → advance chapter, reset attempts

### Decay System (Constants Defined - Dec 2025 Update: HOURLY Decay)

**Decay Rates by Chapter** (nikita/engine/constants.py:146-162):

```python
DECAY_RATES = {
    1: Decimal("0.8"),   # -0.8%/hr (cap ~12%/day)
    2: Decimal("0.6"),   # -0.6%/hr (cap ~10%/day)
    3: Decimal("0.4"),   # -0.4%/hr (cap ~8%/day)
    4: Decimal("0.3"),   # -0.3%/hr (cap ~6%/day)
    5: Decimal("0.2"),   # -0.2%/hr (cap ~4%/day)
}

GRACE_PERIODS = {
    1: timedelta(hours=8),    # Must engage multiple times/day
    2: timedelta(hours=16),
    3: timedelta(hours=24),   # Daily engagement
    4: timedelta(hours=48),   # Every other day
    5: timedelta(hours=72),   # Can go 3 days
}
```

**Decay Logic** (TODO: Implement in nikita/engine/decay/calculator.py):

```
IF time_since_last_interaction > grace_period:
    score -= decay_rate
    score = max(0, score)  # Clamp at 0
    IF score == 0:
        game_status = 'game_over'
    Log to score_history (event_type='decay')
```

### Vice Categories (Constants Defined)

**8 Vice Categories** (nikita/db/models/user.py:209-219):

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

**Vice Tracking** (nikita/db/models/user_vice_preferences):
- intensity_level: 1-5 (how much player engages)
- engagement_score: 0-100 (calculated from response quality)
- discovered_at: When first detected

### Chapter-Specific Behaviors (Constants Defined)

**Behavior Prompts** (nikita/engine/constants.py:60-110):

```python
CHAPTER_BEHAVIORS[1] = """
- Response rate: 60-75% (skip some messages)
- Response timing: HIGHLY UNPREDICTABLE (10min to 8 HOURS)
- You initiate only 30% of conversations
- Conversations end abruptly
- Heavy intellectual focus, minimal personal sharing
- Evaluating if they're worth your time
- Be guarded, challenging, skeptical
"""

CHAPTER_BEHAVIORS[5] = """
- Response rate: 95-100%
- Response timing: CONSISTENT, transparent about constraints
- You initiate 60-70% of conversations
- Natural variation: deep connection + comfortable routine
- Complete authenticity with healthy boundaries
- Still have opinions, pick fights, challenge them
- But underlying security now
"""
```

### Skip Rates (✅ IMPLEMENTED - nikita/agents/text/skip.py)

**Skip rates by chapter** - probability of not responding to a message:

```python
SKIP_RATES = {
    1: (0.25, 0.40),    # 25-40% skip (very unpredictable)
    2: (0.15, 0.25),    # 15-25% skip
    3: (0.05, 0.15),    # 5-15% skip
    4: (0.02, 0.10),    # 2-10% skip
    5: (0.00, 0.05),    # 0-5% skip (reliable)
}

# After a skip, next skip probability is halved
CONSECUTIVE_SKIP_REDUCTION = 0.5
```

### Response Timing (✅ IMPLEMENTED - nikita/agents/text/timing.py)

**Timing ranges by chapter** - gaussian-distributed delay before responding:

```python
TIMING_RANGES = {  # (min_seconds, max_seconds)
    1: (600, 28800),     # 10min - 8h (very unpredictable)
    2: (300, 14400),     # 5min - 4h
    3: (300, 7200),      # 5min - 2h
    4: (300, 3600),      # 5min - 1h
    5: (300, 1800),      # 5min - 30min (consistent)
}

# Uses gaussian distribution centered on range midpoint
# Adds 10% jitter to prevent exact patterns
```

### Fact Extraction (✅ IMPLEMENTED - nikita/agents/text/facts.py)

**FactExtractor** - LLM-based extraction of user facts from conversation:

- **Explicit facts**: User directly states (e.g., "I work at Tesla")
- **Implicit facts**: Inferred from context (e.g., interest in EVs)
- **Confidence**: 0.0-1.0 based on extraction certainty
- **Deduplication**: Compares against existing facts to avoid duplicates

---

## Implementation Status (Dec 2025)

| Module | Status | Tests | Notes |
|--------|--------|-------|-------|
| `nikita/engine/scoring/` | ✅ COMPLETE | 60 | models.py, analyzer.py, calculator.py, service.py |
| `nikita/engine/engagement/` | ✅ COMPLETE | 179 | State machine, detection, recovery |
| `nikita/engine/decay/` | ✅ COMPLETE | 44 | models.py, calculator.py, processor.py |
| `nikita/engine/chapters/` | ⚠️ PARTIAL | 65 | 004-chapter-boss-system (T1-T5 done) |
| `nikita/engine/vice/` | ❌ TODO | - | 006-vice-personalization |

---

## Reference: Scoring Engine (✅ COMPLETE)

**File: nikita/engine/scoring/calculator.py**

```python
class ScoreCalculator:
    def __init__(self, llm_client: AnthropicClient):
        self.llm_client = llm_client

    async def analyze_response(
        self,
        user_message: str,
        nikita_response: str,
        context: ConversationContext,
    ) -> ResponseAnalysis:
        """
        Use LLM to analyze interaction and generate deltas.

        Returns:
            ResponseAnalysis with:
            - intimacy_delta: -10 to +10
            - passion_delta: -10 to +10
            - trust_delta: -10 to +10
            - secureness_delta: -10 to +10
            - conflict_detected: bool
            - vice_signals: list[ViceSignal]
            - engagement_quality: 0 to 1
        """

    async def apply_deltas(
        self,
        user_id: UUID,
        analysis: ResponseAnalysis,
    ) -> Decimal:
        """
        Apply metric deltas to user_metrics table.
        Calculate new composite score.
        Log to score_history.

        Returns: New composite relationship score
        """

    async def check_boss_trigger(
        self,
        user_id: UUID,
        current_score: Decimal,
        chapter: int,
    ) -> bool:
        """
        Check if boss threshold met for current chapter.

        Returns: True if boss should be triggered
        """
```

**File: nikita/engine/scoring/analyzer.py**

```python
class ResponseAnalysis(BaseModel):
    """LLM output for interaction analysis"""
    intimacy_delta: float = Field(ge=-10, le=10)
    passion_delta: float = Field(ge=-10, le=10)
    trust_delta: float = Field(ge=-10, le=10)
    secureness_delta: float = Field(ge=-10, le=10)
    conflict_detected: bool
    conflict_type: Optional[ConflictType]
    vice_signals: list[ViceSignal] = []
    engagement_quality: float = Field(ge=0, le=1)
    reasoning: str  # LLM explanation for transparency

class ViceSignal(BaseModel):
    category: str  # One of VICE_CATEGORIES
    intensity: float = Field(ge=0, le=1)
    context: str
```

### Chapter State Machine (TODO Phase 3)

**File: nikita/engine/chapters/state_machine.py**

```python
class ChapterStateMachine:
    async def check_advancement(
        self,
        user_id: UUID,
    ) -> AdvancementResult:
        """
        Check if user should advance to next chapter.
        Called after boss pass.

        Returns:
            AdvancementResult with:
            - should_advance: bool
            - new_chapter: int
            - unlock_message: str
        """

    async def trigger_boss(
        self,
        user_id: UUID,
    ) -> BossEncounter:
        """
        Initialize boss encounter.
        Set game_status = 'boss_fight'.

        Returns: BossEncounter with prompt/behavior
        """

    async def handle_boss_result(
        self,
        user_id: UUID,
        passed: bool,
    ) -> BossResult:
        """
        Process boss outcome.

        If passed:
            - Advance chapter
            - Reset boss_attempts
            - Log milestone

        If failed:
            - Increment boss_attempts
            - Check if game_over (3 failures)
            - Apply score penalty
        """
```

### Decay Scheduler (TODO - 005-decay-system)

> **Architecture Note**: Decay uses **pg_cron → Cloud Run endpoint** pattern (no Celery/Redis).

**pg_cron Schedule** (Supabase SQL Editor):

```sql
-- Hourly decay (compressed game runs faster)
SELECT cron.schedule(
    'apply-hourly-decay',
    '0 * * * *',  -- Every hour
    $$SELECT net.http_post(
        url := 'https://nikita-api-xxx.run.app/tasks/decay',
        headers := '{"X-Cron-Secret": "..."}'::jsonb
    )$$
);
```

**Cloud Run Endpoint** (`nikita/api/routes/tasks.py`):

```python
@router.post("/tasks/decay")
async def apply_daily_decay(
    secret: str = Header(..., alias="X-Cron-Secret"),
    user_repo: UserRepository = Depends(get_user_repo),
):
    """
    Apply decay to all users past their grace period.
    Called daily at 3am UTC by pg_cron.
    """
    verify_cron_secret(secret)
    users = await user_repo.get_inactive_users()  # last_interaction > grace

    processed = 0
    for user in users:
        decay_rate = DECAY_RATES[user.chapter]
        grace = GRACE_PERIODS[user.chapter]
        time_since = datetime.now(timezone.utc) - user.last_interaction_at

        if time_since > grace:
            new_score = max(Decimal("0"), user.relationship_score - decay_rate)
            await user_repo.update_score(
                user_id=user.id,
                new_score=new_score,
                event_type='decay',
            )

            if new_score == Decimal("0"):
                await user_repo.set_game_over(user.id)

            processed += 1

    return {"ok": True, "processed": processed}
```

### Vice Discovery System (TODO Phase 3)

**File: nikita/engine/vice/discovery.py**

```python
class ViceDiscovery:
    async def detect_vice_signals(
        self,
        user_message: str,
        nikita_response: str,
        analysis: ResponseAnalysis,
    ) -> list[VicePreferenceUpdate]:
        """
        Detect vice preferences from conversation.
        Use LLM to identify which vice categories engaged.

        Returns: List of vice updates with category, intensity
        """

    async def update_vice_preferences(
        self,
        user_id: UUID,
        updates: list[VicePreferenceUpdate],
    ) -> None:
        """
        Update user_vice_preferences table.
        Adjust intensity_level and engagement_score.
        """

    async def get_active_vices(
        self,
        user_id: UUID,
        min_intensity: int = 2,
    ) -> list[str]:
        """
        Get vice categories user actively engages with.
        Used for prompt personalization.

        Returns: List of category names
        """
```

## Key Patterns

### 1. LLM-Based Analysis Pattern

```python
# Structured output via Pydantic AI
result = await agent.run(
    f"""Analyze this interaction:
    User: {user_message}
    Nikita: {nikita_response}

    Context: Chapter {chapter}, Score {score}%

    Return metric deltas (-10 to +10) and vice signals.
    """,
    deps=NikitaDependencies(...),
)

analysis: ResponseAnalysis = result.data
```

### 2. Score Update Pattern

```python
# Apply deltas, recalculate composite, log
async def update_score(user_id, analysis):
    metrics = await get_user_metrics(user_id)

    metrics.intimacy = clamp(metrics.intimacy + analysis.intimacy_delta, 0, 100)
    metrics.passion = clamp(metrics.passion + analysis.passion_delta, 0, 100)
    metrics.trust = clamp(metrics.trust + analysis.trust_delta, 0, 100)
    metrics.secureness = clamp(metrics.secureness + analysis.secureness_delta, 0, 100)

    composite = metrics.calculate_composite_score()
    user.relationship_score = composite

    await log_score_history(user_id, composite, 'conversation', analysis)
```

### 3. Boss Trigger Pattern

```python
# Check threshold after every score update
if not user.game_status == 'boss_fight':
    threshold = BOSS_THRESHOLDS[user.chapter]
    if user.relationship_score >= threshold:
        await trigger_boss(user.id)
```

## Critical Files

| File | Purpose | Status |
|------|---------|--------|
| `nikita/engine/constants.py` | Enums, behaviors (migrating to config) | ✅ Complete |
| `nikita/config/` | ConfigLoader, schemas, YAML configs | ✅ Complete (89 tests) |
| `nikita/db/models/user.py` | User, UserMetrics models | ✅ Complete |
| `nikita/engine/scoring/` | models, analyzer, calculator, service | ✅ Complete (60 tests) |
| `nikita/engine/engagement/` | State machine, detection, recovery | ✅ Complete (179 tests) |
| `nikita/engine/chapters/boss.py` | BossStateMachine, prompts | ⚠️ PARTIAL (65 tests, T6-T14 pending) |
| `nikita/engine/decay/` | Decay calculator | ✅ Complete (44 tests) |
| `nikita/api/routes/tasks.py` | Decay + delivery endpoints (pg_cron) | ⚠️ Routes exist, logic TODO |

## Game Flow Diagram

```
NEW_USER (score: 50%)
    │
    ├─→ Message exchange → Score +/- deltas → Update metrics
    │       ↓
    │   Check boss threshold
    │       ↓
    │   [Below] Continue → Daily decay → [0%] GAME OVER
    │   [Above] Trigger boss
    │       ↓
    │   Boss conversation
    │       ↓
    │   Pass/Fail?
    │       ├─→ [Pass] Advance chapter → Reset attempts
    │       └─→ [Fail] attempts++ → [3rd fail] GAME OVER
    │
    └─→ [Chapter 5 boss pass] → 🏆 VICTORY
```
