# Game Engine Mechanics

```yaml
context_priority: critical
audience: ai_agents
last_updated: 2026-02-03
related_docs:
  - CONTEXT_ENGINE.md
  - USER_JOURNEY.md
  - DATABASE_SCHEMA.md
```

## Overview

The game engine manages relationship progression through:
- **Scoring System** - 4 metrics tracking relationship health
- **Chapter System** - 5 chapters with boss encounters
- **Decay System** - Time-based score reduction
- **Engagement Model** - 6 states tracking player behavior
- **Vice System** - 8 categories of mature content

---

## Scoring System

### Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           SCORING ARCHITECTURE                                │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐                                                            │
│  │ User sends  │                                                            │
│  │  message    │                                                            │
│  └──────┬──────┘                                                            │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  ResponseAnalyzer.analyze() @ analyzer.py:30-100                    │   │
│  │                                                                      │   │
│  │  Analyzes message for:                                               │   │
│  │  - Intimacy signals (vulnerability, sharing, emotional depth)        │   │
│  │  - Passion signals (flirting, excitement, enthusiasm)                │   │
│  │  - Trust signals (honesty, reliability, support)                     │   │
│  │  - Secureness signals (commitment, reassurance, stability)           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  ScoreCalculator.calculate_delta() @ calculator.py:50-120           │   │
│  │                                                                      │   │
│  │  Formula:                                                            │   │
│  │  delta = (intimacy * 0.30 +                                          │   │
│  │           passion * 0.25 +                                           │   │
│  │           trust * 0.25 +                                             │   │
│  │           secureness * 0.20) * engagement_multiplier                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Apply delta to user_metrics.relationship_score                      │   │
│  │  - Clamp to 0-100 range                                             │   │
│  │  - Store individual metric deltas                                   │   │
│  │  - Log to conversation.score_delta                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Four Metrics

| Metric | Weight | Positive Signals | Negative Signals |
|--------|--------|------------------|------------------|
| **Intimacy** | 30% | Sharing feelings, vulnerability, personal stories | Dismissive, surface-level, avoiding depth |
| **Passion** | 25% | Flirting, excitement, humor, creativity | Boring, monotone, uninterested |
| **Trust** | 25% | Honesty, consistency, supportive words | Lies, contradictions, broken promises |
| **Secureness** | 20% | Commitment, reassurance, future plans | Jealousy triggers, avoidance, uncertainty |

### Score Calculation

**File**: `nikita/engine/scoring/calculator.py:1-150`

```python
# nikita/engine/scoring/calculator.py:50-100

class ScoreCalculator:
    """Calculate score deltas from message analysis."""

    WEIGHTS = {
        "intimacy": 0.30,
        "passion": 0.25,
        "trust": 0.25,
        "secureness": 0.20
    }

    def calculate_delta(
        self,
        analysis: ResponseAnalysis,
        engagement_state: str
    ) -> ScoreDelta:
        """Calculate weighted score delta."""

        # Base delta from analysis
        base_delta = sum(
            getattr(analysis.deltas, metric) * weight
            for metric, weight in self.WEIGHTS.items()
        )

        # Apply engagement multiplier
        multiplier = self._get_engagement_multiplier(engagement_state)
        final_delta = base_delta * multiplier

        return ScoreDelta(
            total=final_delta,
            intimacy=analysis.deltas.intimacy,
            passion=analysis.deltas.passion,
            trust=analysis.deltas.trust,
            secureness=analysis.deltas.secureness,
            multiplier=multiplier
        )

    def _get_engagement_multiplier(self, state: str) -> float:
        """Get score multiplier based on engagement state."""
        multipliers = {
            "CALIBRATING": 1.0,
            "IN_ZONE": 1.2,      # Bonus for ideal engagement
            "DRIFTING": 0.9,
            "CLINGY": 0.8,
            "DISTANT": 0.7,
            "OUT_OF_ZONE": 0.5
        }
        return multipliers.get(state, 1.0)
```

### Response Analyzer

**File**: `nikita/engine/scoring/analyzer.py:1-100`

```python
# nikita/engine/scoring/analyzer.py:30-80

class ResponseAnalyzer:
    """Analyze user messages for relationship signals."""

    async def analyze(
        self,
        message: str,
        context: ConversationContext
    ) -> ResponseAnalysis:
        """Analyze message using LLM."""

        prompt = f"""
        Analyze this message from a relationship perspective.

        Message: {message}

        Context:
        - Chapter: {context.chapter}
        - Recent topics: {context.recent_topics}
        - Nikita's current mood: {context.nikita_mood}

        Rate each dimension from -5 to +5:
        - intimacy: emotional depth and vulnerability
        - passion: excitement, flirting, enthusiasm
        - trust: honesty, reliability, supportiveness
        - secureness: commitment, reassurance

        Respond in JSON:
        {{
          "intimacy": <-5 to 5>,
          "passion": <-5 to 5>,
          "trust": <-5 to 5>,
          "secureness": <-5 to 5>,
          "reasoning": "<brief explanation>"
        }}
        """

        result = await self._call_llm(prompt)
        return ResponseAnalysis.model_validate_json(result)
```

---

## Chapter System

### Five Chapters

| Chapter | Threshold | Description | Boss Type |
|---------|-----------|-------------|-----------|
| **1** | 55% | Getting to know each other | Trust test |
| **2** | 60% | Building connection | Commitment test |
| **3** | 65% | Deepening relationship | Jealousy test |
| **4** | 70% | Serious commitment | Future planning test |
| **5** | 75% | Long-term partnership | Ultimate devotion test |

### Chapter State Machine

**File**: `nikita/engine/chapters/state_machine.py:1-150`

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        CHAPTER STATE MACHINE                                  │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐         score >= 55%          ┌─────────────┐              │
│  │  Chapter 1  │ ─────────────────────────────▶│ Boss Fight  │              │
│  │  (0-55%)    │                               │  Ch1 → Ch2  │              │
│  └─────────────┘                               └──────┬──────┘              │
│                                                       │                      │
│                               ┌───────────────────────┼───────────────────┐  │
│                               │ PASS                  │ FAIL              │  │
│                               ▼                       ▼                   │  │
│                        ┌─────────────┐         ┌─────────────┐           │  │
│                        │  Chapter 2  │         │  Stay Ch1   │           │  │
│                        │  (55-60%)   │         │  -5% score  │           │  │
│                        └──────┬──────┘         └─────────────┘           │  │
│                               │                                           │  │
│                               │ score >= 60%                              │  │
│                               ▼                                           │  │
│                        ┌─────────────┐                                    │  │
│                        │ Boss Fight  │                                    │  │
│                        │  Ch2 → Ch3  │                                    │  │
│                        └─────────────┘                                    │  │
│                               │                                           │  │
│                              ...                                          │  │
│                               │                                           │  │
│                               ▼                                           │  │
│                        ┌─────────────┐                                    │  │
│                        │  Chapter 5  │                                    │  │
│                        │  (70-75%)   │                                    │  │
│                        └──────┬──────┘                                    │  │
│                               │                                           │  │
│                               │ score >= 75%                              │  │
│                               ▼                                           │  │
│                        ┌─────────────┐                                    │  │
│                        │ Boss Fight  │                                    │  │
│                        │  Final Boss │                                    │  │
│                        └──────┬──────┘                                    │  │
│                               │                                           │  │
│                               │ PASS                                      │  │
│                               ▼                                           │  │
│                        ┌─────────────┐                                    │  │
│                        │ ENDGAME     │                                    │  │
│                        │ (You Win!)  │                                    │  │
│                        └─────────────┘                                    │  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Chapter Behaviors

Each chapter modifies Nikita's behavior:

**File**: `nikita/config_data/game/chapters.yaml`

```yaml
chapters:
  1:
    name: "Getting Started"
    threshold: 55
    behaviors:
      - "Be friendly and curious"
      - "Ask basic getting-to-know-you questions"
      - "Keep things light and fun"
    vices_unlocked: ["humor", "playfulness"]

  2:
    name: "Building Connection"
    threshold: 60
    behaviors:
      - "Show more personal interest"
      - "Share some of your own stories"
      - "Be more emotionally available"
    vices_unlocked: ["flirtation", "mild_jealousy"]

  3:
    name: "Deepening"
    threshold: 65
    behaviors:
      - "Be more vulnerable"
      - "Express feelings more openly"
      - "Show dependence on the relationship"
    vices_unlocked: ["passion", "possessiveness"]

  4:
    name: "Commitment"
    threshold: 70
    behaviors:
      - "Discuss future together"
      - "Be more demanding of attention"
      - "Show strong emotional attachment"
    vices_unlocked: ["intense_passion", "strong_jealousy"]

  5:
    name: "Partnership"
    threshold: 75
    behaviors:
      - "Act as life partner"
      - "Deep emotional intimacy"
      - "Long-term planning"
    vices_unlocked: ["all"]
```

### Boss Encounters

**File**: `nikita/engine/chapters/boss_encounter.py:1-150`

```python
# nikita/engine/chapters/boss_encounter.py:50-100

class BossEncounter:
    """Generate and manage boss fight scenarios."""

    SCENARIOS = {
        1: {
            "type": "trust_test",
            "prompt": "Nikita discovers a message on your phone from an ex. She's hurt and confused. How do you respond?",
            "pass_criteria": "honest explanation, emotional validation"
        },
        2: {
            "type": "commitment_test",
            "prompt": "Nikita's friend asks if you two are 'official'. She looks at you expectantly. What do you say?",
            "pass_criteria": "clear commitment, not evasive"
        },
        3: {
            "type": "jealousy_test",
            "prompt": "Nikita sees you laughing with an attractive colleague at a party. She's visibly upset. How do you handle it?",
            "pass_criteria": "reassurance without dismissing feelings"
        },
        4: {
            "type": "future_test",
            "prompt": "Nikita asks where you see this relationship in 5 years. She's looking for real answers.",
            "pass_criteria": "concrete future vision, emotional honesty"
        },
        5: {
            "type": "devotion_test",
            "prompt": "Nikita's dream job offer means moving to another country. She asks if you'd come with her.",
            "pass_criteria": "prioritize relationship, show sacrifice"
        }
    }

    async def trigger(self, user_id: UUID, chapter: int) -> BossScenario:
        """Trigger boss encounter for chapter."""
        scenario = self.SCENARIOS[chapter]

        # Mark user as in boss fight
        await self.repo.update(user_id, in_boss_fight=True)

        return BossScenario(
            chapter=chapter,
            type=scenario["type"],
            prompt=scenario["prompt"],
            pass_criteria=scenario["pass_criteria"]
        )
```

### Boss Judgment

**File**: `nikita/engine/chapters/boss_judgment.py:1-100`

```python
# nikita/engine/chapters/boss_judgment.py:30-80

class BossJudgment:
    """Evaluate player response to boss scenario."""

    async def evaluate(
        self,
        scenario: BossScenario,
        response: str
    ) -> BossResult:
        """Use LLM to evaluate boss response."""

        prompt = f"""
        Evaluate this response to a relationship test:

        Scenario: {scenario.prompt}
        Pass criteria: {scenario.pass_criteria}
        User response: {response}

        Did the user pass, partially pass, or fail?
        - PASS: Met all criteria, showed emotional intelligence
        - PARTIAL: Met some criteria, room for improvement
        - FAIL: Did not meet criteria, problematic response

        Respond in JSON:
        {{
          "result": "PASS" | "PARTIAL" | "FAIL",
          "reasoning": "<explanation>",
          "nikita_reaction": "<how Nikita responds>"
        }}
        """

        result = await self._call_llm(prompt)
        return BossResult.model_validate_json(result)
```

---

## Decay System

### Decay Rates by Chapter

| Chapter | Decay Rate | Grace Period | Effect |
|---------|------------|--------------|--------|
| **1** | 0.8/hour | 8 hours | New relationships need attention |
| **2** | 0.6/hour | 16 hours | Building trust |
| **3** | 0.4/hour | 24 hours | More established |
| **4** | 0.3/hour | 48 hours | Committed |
| **5** | 0.2/hour | 72 hours | Long-term stability |

### Decay Calculator

**File**: `nikita/engine/decay/calculator.py:1-100`

```python
# nikita/engine/decay/calculator.py:30-80

class DecayCalculator:
    """Calculate relationship decay based on inactivity."""

    DECAY_RATES = {
        1: 0.8,
        2: 0.6,
        3: 0.4,
        4: 0.3,
        5: 0.2
    }

    GRACE_PERIODS = {
        1: 8,
        2: 16,
        3: 24,
        4: 48,
        5: 72
    }

    def calculate_decay(
        self,
        chapter: int,
        hours_since_last: float
    ) -> float:
        """Calculate decay amount."""

        grace_period = self.GRACE_PERIODS.get(chapter, 24)

        # No decay during grace period
        if hours_since_last <= grace_period:
            return 0.0

        # Calculate decay for hours past grace period
        hours_decaying = hours_since_last - grace_period
        rate = self.DECAY_RATES.get(chapter, 0.4)

        return hours_decaying * rate
```

### Decay Processor

**File**: `nikita/engine/decay/processor.py:1-100`

```python
# nikita/engine/decay/processor.py:30-70

class DecayProcessor:
    """Process decay for all active users."""

    async def process_all(self, session: AsyncSession) -> DecayReport:
        """Run decay for all eligible users."""

        repo = UserRepository(session)
        users = await repo.get_active_users()

        processed = 0
        game_overs = 0

        for user in users:
            metrics = await repo.get_metrics(user.id)
            hours_since = self._hours_since_interaction(metrics.last_interaction)

            decay = self.calculator.calculate_decay(
                chapter=metrics.chapter_number,
                hours_since_last=hours_since
            )

            if decay > 0:
                new_score = max(0, float(metrics.relationship_score) - decay)
                await repo.update_score(user.id, new_score)
                processed += 1

                # Check for game over
                if new_score <= 0:
                    await repo.set_game_over(user.id)
                    game_overs += 1

        return DecayReport(processed=processed, game_overs=game_overs)
```

### Decay Endpoint

**File**: `nikita/api/routes/tasks.py:100-150`

Called by pg_cron every hour:

```python
@router.post("/decay")
async def run_decay(session: AsyncSession = Depends(get_db_session)):
    """Execute decay for all users."""
    processor = DecayProcessor()
    report = await processor.process_all(session)
    return {"status": "success", **report.model_dump()}
```

---

## Engagement Model

### Six States

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        ENGAGEMENT STATE MACHINE                               │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                         ┌─────────────────┐                                  │
│                         │   CALIBRATING   │                                  │
│                         │ (First 5 convos)│                                  │
│                         └────────┬────────┘                                  │
│                                  │                                           │
│                                  │ Calibration complete                      │
│                                  ▼                                           │
│                         ┌─────────────────┐                                  │
│                         │    IN_ZONE      │ ◀─── Ideal state (1.2x)          │
│                         │ (Balanced)      │                                  │
│                         └────────┬────────┘                                  │
│                    ┌─────────────┼─────────────┐                             │
│                    │             │             │                              │
│            Too passive           │     Too active                            │
│                    ▼             │             ▼                              │
│           ┌──────────────┐      │      ┌──────────────┐                      │
│           │   DRIFTING   │      │      │    CLINGY    │                      │
│           │   (0.9x)     │      │      │    (0.8x)    │                      │
│           └──────┬───────┘      │      └──────┬───────┘                      │
│                  │              │              │                              │
│         More passive            │      More active                           │
│                  ▼              │              ▼                              │
│           ┌──────────────┐      │      ┌──────────────┐                      │
│           │   DISTANT    │      │      │  OUT_OF_ZONE │                      │
│           │   (0.7x)     │      │      │   (0.5x)     │                      │
│           └──────────────┘      │      └──────────────┘                      │
│                                 │                                            │
│                                 ▼                                            │
│                    Recovery paths back to IN_ZONE                            │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### State Definitions

| State | Trigger | Multiplier | Nikita Behavior |
|-------|---------|------------|-----------------|
| `CALIBRATING` | First 5 conversations | 1.0x | Learning user patterns |
| `IN_ZONE` | Balanced interaction | 1.2x | Happy, responsive |
| `DRIFTING` | Slightly less active | 0.9x | Gently reaches out |
| `CLINGY` | Too many messages | 0.8x | Asks for space |
| `DISTANT` | Very inactive | 0.7x | Sad, withdrawn |
| `OUT_OF_ZONE` | Extreme either way | 0.5x | Frustrated, upset |

### State Calculator

**File**: `nikita/engine/engagement/calculator.py:1-100`

```python
# nikita/engine/engagement/calculator.py:30-80

class StateCalculator:
    """Calculate engagement state from interaction patterns."""

    async def calculate(
        self,
        user_id: UUID,
        session: AsyncSession
    ) -> EngagementState:
        """Determine current engagement state."""

        repo = ConversationRepository(session)
        recent = await repo.get_recent(user_id, days=7)

        # Calculate metrics
        messages_per_day = len(recent) / 7
        avg_response_time = self._avg_response_time(recent)
        session_frequency = self._session_frequency(recent)

        # First 5 conversations = calibrating
        if len(recent) < 5:
            return EngagementState.CALIBRATING

        # Calculate ideal point (personalized baseline)
        ideal = await self._get_ideal_point(user_id)

        # Compare to ideal
        deviation = self._calculate_deviation(
            actual=(messages_per_day, avg_response_time, session_frequency),
            ideal=ideal
        )

        return self._deviation_to_state(deviation)

    def _deviation_to_state(self, deviation: float) -> EngagementState:
        """Map deviation from ideal to state."""
        if abs(deviation) < 0.2:
            return EngagementState.IN_ZONE
        elif deviation > 0.5:
            return EngagementState.CLINGY if deviation > 1.0 else EngagementState.OUT_OF_ZONE
        elif deviation < -0.5:
            return EngagementState.DISTANT if deviation < -1.0 else EngagementState.DRIFTING
        else:
            return EngagementState.DRIFTING if deviation < 0 else EngagementState.CLINGY
```

---

## Vice System

### Eight Vice Categories

| Vice | Chapter Unlock | Description |
|------|----------------|-------------|
| `humor` | 1 | Playful teasing, jokes |
| `playfulness` | 1 | Games, fun activities |
| `flirtation` | 2 | Light romantic hints |
| `mild_jealousy` | 2 | Subtle possessiveness |
| `passion` | 3 | Strong romantic expression |
| `possessiveness` | 3 | "You're mine" energy |
| `intense_passion` | 4 | Deep romantic intensity |
| `strong_jealousy` | 4 | Explicit jealousy |

### Vice Configuration

**File**: `nikita/config_data/game/vices.yaml`

```yaml
vices:
  humor:
    name: "Humor"
    unlock_chapter: 1
    description: "Playful teasing and jokes"
    intensity_levels:
      low: "Light jokes and puns"
      medium: "Teasing with affection"
      high: "Edgy humor, gentle roasts"

  flirtation:
    name: "Flirtation"
    unlock_chapter: 2
    description: "Romantic hints and attraction"
    intensity_levels:
      low: "Subtle compliments"
      medium: "Clear romantic interest"
      high: "Bold romantic advances"

  jealousy:
    name: "Jealousy"
    unlock_chapter: 2
    description: "Possessive reactions"
    intensity_levels:
      low: "Mild curiosity about others"
      medium: "Noticeable discomfort"
      high: "Explicit jealousy expression"
```

### Vice Service

**File**: `nikita/engine/vices/service.py:1-100`

```python
# nikita/engine/vices/service.py:30-70

class ViceService:
    """Manage vice unlocking and application."""

    async def get_unlocked_vices(
        self,
        user_id: UUID,
        chapter: int
    ) -> List[Vice]:
        """Get vices unlocked for user's chapter."""
        config = ConfigLoader.get_instance()
        all_vices = config.get("vices")

        unlocked = []
        for vice_name, vice_config in all_vices.items():
            if vice_config["unlock_chapter"] <= chapter:
                # Get user's preference for this vice
                preference = await self._get_preference(user_id, vice_name)
                unlocked.append(Vice(
                    name=vice_name,
                    intensity=preference.intensity if preference else "medium",
                    **vice_config
                ))

        return unlocked

    async def inject_vice_context(
        self,
        context: ContextPackage,
        vices: List[Vice]
    ) -> None:
        """Add vice instructions to context."""
        vice_instructions = []
        for vice in vices:
            instruction = self._format_instruction(vice)
            vice_instructions.append(instruction)

        context.vice_instructions = vice_instructions
```

---

## Game Constants

**File**: `nikita/engine/constants.py:1-150`

```python
# nikita/engine/constants.py:1-80

# Scoring weights
METRIC_WEIGHTS = {
    "intimacy": 0.30,
    "passion": 0.25,
    "trust": 0.25,
    "secureness": 0.20
}

# Chapter thresholds
CHAPTER_THRESHOLDS = {
    1: 55,
    2: 60,
    3: 65,
    4: 70,
    5: 75
}

# Decay rates (per hour)
DECAY_RATES = {
    1: 0.8,
    2: 0.6,
    3: 0.4,
    4: 0.3,
    5: 0.2
}

# Grace periods (hours)
GRACE_PERIODS = {
    1: 8,
    2: 16,
    3: 24,
    4: 48,
    5: 72
}

# Engagement multipliers
ENGAGEMENT_MULTIPLIERS = {
    "CALIBRATING": 1.0,
    "IN_ZONE": 1.2,
    "DRIFTING": 0.9,
    "CLINGY": 0.8,
    "DISTANT": 0.7,
    "OUT_OF_ZONE": 0.5
}

# Boss failure penalty
BOSS_FAIL_PENALTY = 5.0  # Points deducted on fail

# Game over threshold
GAME_OVER_SCORE = 0.0
GAME_OVER_CHAPTER = 6  # Chapter 6 = game over state
```

---

## Key File References

| File | Line | Purpose |
|------|------|---------|
| `nikita/engine/scoring/calculator.py` | 1-150 | Score calculation |
| `nikita/engine/scoring/analyzer.py` | 1-100 | Response analysis |
| `nikita/engine/chapters/state_machine.py` | 1-150 | Chapter transitions |
| `nikita/engine/chapters/boss_encounter.py` | 1-150 | Boss scenarios |
| `nikita/engine/chapters/boss_judgment.py` | 1-100 | Boss evaluation |
| `nikita/engine/decay/calculator.py` | 1-100 | Decay math |
| `nikita/engine/decay/processor.py` | 1-100 | Batch decay |
| `nikita/engine/engagement/calculator.py` | 1-100 | State calculation |
| `nikita/engine/vices/service.py` | 1-100 | Vice management |
| `nikita/engine/constants.py` | 1-150 | All constants |

---

## Related Documentation

- **Context Engine**: [CONTEXT_ENGINE.md](CONTEXT_ENGINE.md)
- **User Journey**: [USER_JOURNEY.md](USER_JOURNEY.md)
- **Database Schema**: [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md)
