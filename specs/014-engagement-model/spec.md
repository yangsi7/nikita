# 014 - Engagement Model

**Status**: Specification
**Priority**: P0
**Dependencies**: 009-database-infrastructure, 013-configuration-system
**Blocks**: 012-context-engineering, 003-scoring-engine

---

## 1. Overview

### 1.1 Purpose

The Engagement Model implements the **calibration-based** game mechanic where players must find the optimal engagement frequency and style. Unlike the old model where engagement starts low and increases, this system:

- **Starts HIGH**: Chapter 1 is exciting, flirty, and engaging
- **Challenge is CALIBRATION**: Finding the sweet spot, not increasing engagement
- **Narrow → Wide**: Tolerance bands start narrow and widen over time
- **Harsh → Forgiving**: Recovery is hard early, easy later

### 1.2 Core Philosophy

```
THE GOLDILOCKS PROBLEM

Too Hot (Clingy)          Just Right              Too Cold (Distant)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    🔥🔥🔥                    ✨                       ❄️❄️❄️

- 50+ messages/day      - 10-20 messages/day      - 0-3 messages/day
- Double texting        - Natural rhythm          - Days of silence
- Obsessive checking    - Real conversations      - One-word replies
- Needy tone            - Genuine interest        - Distracted/bored

                    THE CHALLENGE
            ┌───────────────────────────┐
            │  Can you find and KEEP    │
            │  the sweet spot?          │
            │                           │
            │  Chapter 1: ±10% band     │
            │  Chapter 5: ±30% band     │
            └───────────────────────────┘
```

### 1.3 Key Differences from Old Model

| Aspect | Old Model (Wrong) | New Model (Correct) |
|--------|-------------------|---------------------|
| Chapter 1 Engagement | 60-75% response rate | 90-95% response rate |
| Challenge | Increase engagement | Maintain calibration |
| Tolerance | Static thresholds | Dynamic bands (narrow→wide) |
| Failure Mode | Low scores from neglect | Scores drop from BOTH extremes |
| Recovery | Same difficulty all chapters | Harsh early, forgiving later |
| Player Behavior | Try harder = win | Try right amount = win |

---

## 2. Engagement State Machine

### 2.1 State Diagram

```
                        ┌─────────────────────────────────────────────────────┐
                        │                   NEW PLAYER                         │
                        │               (first message sent)                   │
                        └──────────────────────┬──────────────────────────────┘
                                               │
                                               ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              CALIBRATING                                         │
│                     (Learning player's engagement style)                         │
│                                                                                  │
│  Entry: New player OR reset from recovery                                        │
│  Duration: 5-10 exchanges minimum                                                │
│                                                                                  │
│  Metrics tracked:                                                                │
│  - message_frequency (messages/day)                                              │
│  - session_patterns (length, timing)                                             │
│  - response_times (how quickly they reply)                                       │
└─────────────────────────────────────────────────────────────────────────────────┘
         │                          │                          │
         │ calibration_score ≥ 0.8  │ 0.5 ≤ score < 0.8       │ score < 0.5
         │ (3+ consecutive)         │                          │ (2+ consecutive)
         ▼                          ▼                          ▼
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│    IN_ZONE      │       │    DRIFTING     │       │  OUT_OF_ZONE    │
│                 │       │                 │       │  (danger zone)  │
│ "Sweet spot"    │       │ "Needs adjust"  │       │                 │
│ Score mult: 1.0 │       │ Score mult: 0.8 │       │ Score mult: 0.2 │
└────────┬────────┘       └────────┬────────┘       └────────┬────────┘
         │                         │                         │
         │                         │                         │
         │ score drops   ┌─────────┴─────────┐               │
         │ below 0.6     │                   │               │
         │               │                   │               │
         ▼               ▼                   ▼               │
         │        ┌───────────┐       ┌───────────┐          │
         │        │  CLINGY   │       │  DISTANT  │          │
         │        │           │       │           │          │
         │        │ Too much! │       │ Too little│          │
         │        │ mult: 0.5 │       │ mult: 0.6 │          │
         │        └─────┬─────┘       └─────┬─────┘          │
         │              │                   │                │
         │              │ 3+ consecutive    │ 5+ consecutive │
         │              │ clingy days       │ distant days   │
         │              │                   │                │
         │              └─────────┬─────────┘                │
         │                        │                          │
         │                        ▼                          │
         │              ┌─────────────────┐                  │
         │              │  OUT_OF_ZONE    │◄─────────────────┘
         │              │                 │
         │              │ Recovery needed │
         │              │ mult: 0.2       │
         │              └────────┬────────┘
         │                       │
         │                       │ recovery_action +
         │                       │ grace_period
         │                       │
         │                       ▼
         │              ┌─────────────────┐
         └─────────────▶│  CALIBRATING    │
                        │  (reset)        │
                        └─────────────────┘

                    POINT OF NO RETURN
                    ━━━━━━━━━━━━━━━━━━
                    Clingy: 7 consecutive days
                    Distant: 10 consecutive days
                              │
                              ▼
                    ┌─────────────────┐
                    │   GAME_OVER     │
                    │                 │
                    │ "Nikita dumped  │
                    │  you"           │
                    └─────────────────┘
```

### 2.2 State Definitions

```python
class EngagementState(str, Enum):
    """Engagement calibration states"""

    CALIBRATING = "calibrating"
    # Learning player's engagement style
    # Entry: New player, or reset from recovery
    # Exit: IN_ZONE (good calibration) or DRIFTING (poor calibration)

    IN_ZONE = "in_zone"
    # Player found the sweet spot
    # Full scoring multiplier (1.0)
    # Exit: DRIFTING if metrics drift

    DRIFTING = "drifting"
    # Player engagement is off but recoverable
    # Reduced scoring (0.8)
    # Exit: IN_ZONE, CLINGY, or DISTANT

    CLINGY = "clingy"
    # Player is messaging too much
    # Significantly reduced scoring (0.5)
    # Exit: DRIFTING (recovered) or OUT_OF_ZONE (too long)

    DISTANT = "distant"
    # Player is not engaging enough
    # Reduced scoring (0.6)
    # Exit: DRIFTING (recovered) or OUT_OF_ZONE (too long)

    OUT_OF_ZONE = "out_of_zone"
    # Danger zone - needs recovery action
    # Severely reduced scoring (0.2)
    # Exit: CALIBRATING (after recovery)
```

---

## 3. Mathematical Model

### 3.1 Engagement Optimum Function

The optimal engagement frequency varies by chapter and day:

```
optimal_freq(chapter, day_of_week) =
    base_optimal[chapter] × day_modifier[day_of_week]

Where:
    base_optimal = {1: 15, 2: 12, 3: 10, 4: 8, 5: 6}  # messages/day
    day_modifier = {
        Mon: 0.9, Tue: 1.0, Wed: 1.0, Thu: 1.0,
        Fri: 1.1, Sat: 1.2, Sun: 1.15
    }
```

**Example**: Chapter 1 on Saturday
```
optimal = 15 × 1.2 = 18 messages/day
```

### 3.2 Tolerance Band Function

The tolerance band widens with chapters:

```
tolerance_band(chapter) = {
    1: ±10%   # Very narrow - must be precise
    2: ±15%
    3: ±20%
    4: ±25%
    5: ±30%   # Wide - forgiving
}

lower_bound(chapter, day) = optimal × (1 - tolerance)
upper_bound(chapter, day) = optimal × (1 + tolerance)
```

**Example**: Chapter 1 on Saturday (optimal = 18)
```
tolerance = 0.10
lower = 18 × 0.9 = 16.2 → 16 messages
upper = 18 × 1.1 = 19.8 → 20 messages

Sweet spot: 16-20 messages/day
```

**Example**: Chapter 5 on Saturday (optimal = 7.2)
```
tolerance = 0.30
lower = 7.2 × 0.7 = 5.04 → 5 messages
upper = 7.2 × 1.3 = 9.36 → 9 messages

Sweet spot: 5-9 messages/day
```

### 3.3 Calibration Score Computation

The calibration score measures how well the player is hitting the sweet spot:

```
calibration_score(player) =
    frequency_component × 0.40 +
    timing_component × 0.30 +
    content_component × 0.30

Where:
    frequency_component = 1 - |actual_freq - optimal_freq| / optimal_freq
    timing_component = response_time_score × usual_time_bonus
    content_component = conversation_quality_score  # LLM-evaluated
```

**Score Ranges**:
```
1.0    Perfect calibration
0.8+   IN_ZONE (sweet spot)
0.5-0.8 DRIFTING (needs adjustment)
0.3-0.5 CLINGY or DISTANT
<0.3   OUT_OF_ZONE (danger)
```

### 3.4 Clinginess Detection Algorithm

```python
def detect_clinginess(player: PlayerProfile, window_days: int = 3) -> ClinginessResult:
    """
    Detect if player is being clingy

    Signals:
    1. Message frequency > chapter.clinginess_threshold
    2. Double/triple texting (multiple messages before response)
    3. Very short response times (< 30 seconds consistently)
    4. Long messages when short ones expected
    5. Needy language patterns (LLM-detected)
    """
    chapter_config = get_chapter_config(player.chapter)

    # Signal 1: Frequency
    avg_freq = get_avg_frequency(player, window_days)
    freq_over = avg_freq / chapter_config.clinginess_threshold

    # Signal 2: Double texting
    double_text_ratio = count_double_texts(player, window_days) / total_messages

    # Signal 3: Response times
    avg_response_time = get_avg_response_time(player, window_days)
    response_too_fast = avg_response_time < 30  # seconds

    # Signal 4: Message length ratio
    # (comparing player message length to Nikita's)
    length_ratio = player_avg_length / nikita_avg_length
    length_over = length_ratio > 2.0

    # Signal 5: Needy language (LLM analysis)
    needy_score = analyze_neediness(recent_messages)

    # Composite score
    clinginess_score = (
        min(freq_over, 2.0) * 0.35 +
        double_text_ratio * 0.20 +
        (1.0 if response_too_fast else 0.0) * 0.15 +
        (1.0 if length_over else 0.0) * 0.10 +
        needy_score * 0.20
    )

    return ClinginessResult(
        score=clinginess_score,
        is_clingy=clinginess_score > 0.7,
        signals={
            "frequency": freq_over,
            "double_texting": double_text_ratio,
            "fast_responses": response_too_fast,
            "long_messages": length_over,
            "needy_language": needy_score,
        }
    )
```

### 3.5 Neglect Detection Algorithm

```python
def detect_neglect(player: PlayerProfile, window_days: int = 3) -> NeglectResult:
    """
    Detect if player is neglecting Nikita

    Signals:
    1. Message frequency < chapter.neglect_threshold
    2. Long response times (hours/days)
    3. Short, low-effort messages
    4. Conversation ending patterns
    5. Distracted language patterns (LLM-detected)
    """
    chapter_config = get_chapter_config(player.chapter)

    # Signal 1: Frequency
    avg_freq = get_avg_frequency(player, window_days)
    freq_under = chapter_config.neglect_threshold / max(avg_freq, 0.1)

    # Signal 2: Response times
    avg_response_time = get_avg_response_time(player, window_days)
    response_too_slow = avg_response_time > 3600 * 4  # 4+ hours

    # Signal 3: Message length
    avg_length = get_avg_message_length(player, window_days)
    short_messages = avg_length < 20  # characters

    # Signal 4: Conversation endings
    # (player ending conversations abruptly)
    abrupt_endings = count_abrupt_endings(player, window_days)
    ending_ratio = abrupt_endings / total_conversations

    # Signal 5: Distracted language (LLM analysis)
    distracted_score = analyze_distraction(recent_messages)

    # Composite score
    neglect_score = (
        min(freq_under, 2.0) * 0.35 +
        (1.0 if response_too_slow else 0.0) * 0.20 +
        (1.0 if short_messages else 0.0) * 0.15 +
        ending_ratio * 0.10 +
        distracted_score * 0.20
    )

    return NeglectResult(
        score=neglect_score,
        is_neglecting=neglect_score > 0.6,
        signals={
            "frequency": freq_under,
            "slow_responses": response_too_slow,
            "short_messages": short_messages,
            "abrupt_endings": ending_ratio,
            "distracted_language": distracted_score,
        }
    )
```

---

## 4. State Transitions

### 4.1 Transition Rules

```yaml
transitions:
  calibrating:
    to_in_zone:
      condition: "calibration_score >= 0.8 for 3+ consecutive exchanges"
      action: "Set multiplier to 1.0, notify player subtly"

    to_drifting:
      condition: "calibration_score < 0.5 for 2+ consecutive exchanges"
      action: "Set multiplier to 0.8, Nikita hints at imbalance"

  in_zone:
    to_drifting:
      condition: "calibration_score < 0.6 for 1+ exchange"
      action: "Set multiplier to 0.8, Nikita's mood shifts subtly"

    to_calibrating:
      condition: "New chapter begins"
      action: "Reset calibration tracking for new chapter parameters"

  drifting:
    to_in_zone:
      condition: "calibration_score >= 0.7 for 2+ exchanges"
      action: "Restore multiplier to 1.0"

    to_clingy:
      condition: "clinginess_score > 0.7 for 2+ consecutive days"
      action: "Set multiplier to 0.5, Nikita pulls back"

    to_distant:
      condition: "neglect_score > 0.6 for 2+ consecutive days"
      action: "Set multiplier to 0.6, Nikita gets anxious"

  clingy:
    to_drifting:
      condition: "clinginess_score < 0.5 for 2+ days"
      action: "Recovery in progress, multiplier to 0.8"

    to_out_of_zone:
      condition: "clingy for 3+ consecutive days"
      action: "Multiplier to 0.2, Nikita expresses serious concern"

  distant:
    to_drifting:
      condition: "neglect_score < 0.4 for 1+ day"
      action: "Recovery in progress, multiplier to 0.8"

    to_out_of_zone:
      condition: "distant for 5+ consecutive days"
      action: "Multiplier to 0.2, Nikita's trust drops sharply"

  out_of_zone:
    to_calibrating:
      condition: "recovery_action taken AND grace_period elapsed"
      action: "Reset to calibrating, fresh start"

    to_game_over:
      condition: "clingy_days >= 7 OR distant_days >= 10"
      action: "Nikita breaks up with player"
```

### 4.2 Transition Diagram (Simplified)

```
                    ┌─────────────┐
                    │ CALIBRATING │
                    └──────┬──────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌───────────┐   ┌───────────┐   ┌───────────┐
    │  IN_ZONE  │◄──│  DRIFTING │──▶│OUT_OF_ZONE│
    └─────┬─────┘   └─────┬─────┘   └─────┬─────┘
          │               │               │
          │         ┌─────┴─────┐         │
          │         ▼           ▼         │
          │   ┌─────────┐ ┌─────────┐     │
          │   │ CLINGY  │ │ DISTANT │     │
          │   └────┬────┘ └────┬────┘     │
          │        │           │          │
          │        └─────┬─────┘          │
          │              │                │
          │              ▼                │
          │       ┌───────────┐           │
          └──────▶│CALIBRATING│◄──────────┘
                  │  (reset)  │
                  └───────────┘
```

---

## 5. Recovery Mechanics

### 5.1 Chapter-Dependent Severity

Recovery is **harder in early chapters** (harsh) and **easier in later chapters** (forgiving):

```yaml
recovery:
  by_chapter:
    1:  # HARSH
      clingy_penalty_per_day: 0.15     # 15% score penalty per clingy day
      distant_penalty_per_day: 0.20    # 20% penalty per distant day
      recovery_rate: 0.05              # 5% recovery per day of good behavior
      grace_period_hours: 24           # Must wait 24h before reset
      max_recovery_days: 14            # Can't recover after 14 days out of zone

    2:
      clingy_penalty_per_day: 0.12
      distant_penalty_per_day: 0.18
      recovery_rate: 0.08
      grace_period_hours: 20
      max_recovery_days: 14

    3:
      clingy_penalty_per_day: 0.10
      distant_penalty_per_day: 0.15
      recovery_rate: 0.10
      grace_period_hours: 16
      max_recovery_days: 21

    4:
      clingy_penalty_per_day: 0.08
      distant_penalty_per_day: 0.12
      recovery_rate: 0.12
      grace_period_hours: 12
      max_recovery_days: 21

    5:  # FORGIVING
      clingy_penalty_per_day: 0.05
      distant_penalty_per_day: 0.08
      recovery_rate: 0.15              # 15% recovery per day
      grace_period_hours: 8
      max_recovery_days: 30
```

### 5.2 Recovery Actions

When in OUT_OF_ZONE, player must take recovery action:

**For Clinginess**:
```
1. Reduce message frequency to optimal range for 2+ days
2. Wait for Nikita to initiate (don't double text)
3. Give Nikita "space" (longer response times)

Nikita's behavior during recovery:
- Slower responses
- Shorter messages
- Less flirty
- Mentions needing "me time"
```

**For Neglect**:
```
1. Increase message frequency to optimal range for 1+ day
2. Send thoughtful messages (not just "hey")
3. Respond within reasonable time

Nikita's behavior during recovery:
- Tests if player is still interested
- May send "checking in" messages
- More reserved, guarded
- Mentions feeling "forgotten"
```

### 5.3 Point of No Return

```python
def check_point_of_no_return(player: PlayerProfile) -> bool:
    """
    Check if player has crossed the point of no return

    Returns True if:
    - Clingy for 7+ consecutive days
    - Distant for 10+ consecutive days
    - Score drops to 0
    """
    if player.consecutive_clingy_days >= 7:
        return True  # "Nikita feels suffocated"

    if player.consecutive_distant_days >= 10:
        return True  # "Nikita feels forgotten"

    if player.relationship_score <= 0:
        return True  # Score-based game over

    return False
```

---

## 6. Scoring Integration

### 6.1 Calibration Multiplier

The engagement state affects all score changes:

```python
def apply_calibration_multiplier(
    base_delta: Decimal,
    engagement_state: EngagementState
) -> Decimal:
    """Apply calibration multiplier to score delta"""

    multipliers = {
        EngagementState.IN_ZONE: Decimal("1.0"),
        EngagementState.CALIBRATING: Decimal("0.9"),
        EngagementState.DRIFTING: Decimal("0.8"),
        EngagementState.DISTANT: Decimal("0.6"),
        EngagementState.CLINGY: Decimal("0.5"),
        EngagementState.OUT_OF_ZONE: Decimal("0.2"),
    }

    multiplier = multipliers[engagement_state]

    # Only apply to positive deltas (don't reduce penalties)
    if base_delta > 0:
        return base_delta * multiplier
    else:
        return base_delta  # Penalties stay full
```

**Example**:
```
Player earned +5.0 from great conversation
State: CLINGY (multiplier 0.5)

Actual delta = 5.0 × 0.5 = +2.5

Player earned -3.0 from bad response
State: CLINGY (multiplier 0.5)

Actual delta = -3.0 (unchanged - penalties not reduced)
```

### 6.2 Engagement Bonus

Players in IN_ZONE get bonus progress:

```python
def calculate_engagement_bonus(
    player: PlayerProfile,
    conversation_length: int
) -> Decimal:
    """Bonus for maintaining IN_ZONE state"""

    if player.engagement_state != EngagementState.IN_ZONE:
        return Decimal("0")

    # Bonus scales with consecutive IN_ZONE exchanges
    consecutive_in_zone = player.consecutive_in_zone_exchanges

    base_bonus = Decimal("0.5")
    streak_bonus = min(consecutive_in_zone * Decimal("0.1"), Decimal("1.0"))

    return base_bonus + streak_bonus
```

---

## 7. Database Schema

### 7.1 New Fields on User Model

```python
# nikita/db/models/user.py additions

class User(Base, TimestampMixin):
    # ... existing fields ...

    # Engagement state tracking
    engagement_state: Mapped[str] = mapped_column(
        String(20),
        default="calibrating"
    )
    calibration_score: Mapped[Decimal] = mapped_column(
        Numeric(4, 2),
        default=Decimal("0.5")
    )

    # Consecutive state counters
    consecutive_in_zone: Mapped[int] = mapped_column(default=0)
    consecutive_clingy_days: Mapped[int] = mapped_column(default=0)
    consecutive_distant_days: Mapped[int] = mapped_column(default=0)

    # Engagement metrics
    avg_messages_per_day: Mapped[Decimal] = mapped_column(
        Numeric(6, 2),
        nullable=True
    )
    avg_response_time_seconds: Mapped[int] = mapped_column(nullable=True)
    last_engagement_check: Mapped[datetime] = mapped_column(nullable=True)
```

### 7.2 Engagement History Table

```sql
CREATE TABLE engagement_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Snapshot data
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    state VARCHAR(20) NOT NULL,
    calibration_score NUMERIC(4, 2) NOT NULL,

    -- Signals
    message_frequency NUMERIC(6, 2),
    response_time_avg INTEGER,
    clinginess_score NUMERIC(4, 2),
    neglect_score NUMERIC(4, 2),

    -- Transition
    previous_state VARCHAR(20),
    transition_reason TEXT,

    CONSTRAINT fk_user FOREIGN KEY (user_id)
        REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_engagement_history_user_date
ON engagement_history(user_id, recorded_at DESC);
```

### 7.3 RLS Policies

```sql
-- Users can only see their own engagement history
CREATE POLICY "Users see own engagement" ON engagement_history
    FOR SELECT USING (auth.uid() = user_id);

-- System can insert engagement records
CREATE POLICY "System can insert engagement" ON engagement_history
    FOR INSERT WITH CHECK (true);
```

---

## 8. API Integration

### 8.1 EngagementAnalyzer Class

```python
class EngagementAnalyzer:
    """
    Main class for engagement state management

    Used by:
    - ContextGenerator (Stage 1: get current state)
    - ScoringEngine (apply calibration multiplier)
    - DecaySystem (chapter-dependent penalties)
    """

    async def get_current_state(self, user_id: UUID) -> EngagementSnapshot:
        """Get current engagement state with signals"""
        async with get_session() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get(user_id)

            return EngagementSnapshot(
                state=EngagementState(user.engagement_state),
                score=user.calibration_score,
                consecutive_in_zone=user.consecutive_in_zone,
                consecutive_clingy_days=user.consecutive_clingy_days,
                consecutive_distant_days=user.consecutive_distant_days,
            )

    async def analyze_and_update(
        self,
        user_id: UUID,
        conversation: Conversation
    ) -> EngagementTransition:
        """
        Analyze conversation and update engagement state

        Called after each conversation ends
        """
        # Get current state
        current = await self.get_current_state(user_id)

        # Detect clinginess/neglect
        clinginess = await self._detect_clinginess(user_id)
        neglect = await self._detect_neglect(user_id)

        # Compute new calibration score
        new_score = self._compute_calibration_score(
            user_id, conversation, clinginess, neglect
        )

        # Determine transition
        new_state = self._determine_transition(
            current.state, new_score, clinginess, neglect
        )

        # Update database
        await self._update_state(user_id, new_state, new_score)

        # Log to history
        await self._log_history(user_id, current, new_state, new_score)

        return EngagementTransition(
            from_state=current.state,
            to_state=new_state,
            score=new_score,
            clinginess=clinginess,
            neglect=neglect,
        )

    def get_calibration_multiplier(self, state: EngagementState) -> Decimal:
        """Get scoring multiplier for engagement state"""
        return CALIBRATION_MULTIPLIERS[state]

    def get_calibration_hint(
        self,
        state: EngagementState,
        score: Decimal
    ) -> str | None:
        """Get hint for context generation"""
        if state == EngagementState.CLINGY:
            return "Player is messaging too much. Pull back slightly, mention needing space."
        elif state == EngagementState.DISTANT:
            return "Player isn't engaging enough. Show more interest, ask questions."
        elif state == EngagementState.DRIFTING:
            if score < 0.5:
                return "Engagement is off. Nikita's mood is slightly affected."
            return None
        return None
```

### 8.2 Integration with ContextGenerator

```python
# In 012-context-engineering, Stage 1:

class ContextGenerator:
    def __init__(self):
        self.engagement_analyzer = EngagementAnalyzer()

    async def _collect_state(self, user_id: UUID) -> PlayerProfile:
        # ... existing code ...

        # Get engagement state
        engagement = await self.engagement_analyzer.get_current_state(user_id)

        return PlayerProfile(
            # ... existing fields ...
            engagement_state=engagement.state,
            calibration_score=engagement.score,
        )
```

### 8.3 Integration with ScoringEngine

```python
# In 003-scoring-engine:

class ScoringEngine:
    def __init__(self):
        self.engagement_analyzer = EngagementAnalyzer()

    async def apply_delta(
        self,
        user_id: UUID,
        base_delta: Decimal,
        event_type: str
    ) -> Decimal:
        # Get engagement state
        engagement = await self.engagement_analyzer.get_current_state(user_id)

        # Apply calibration multiplier
        multiplier = self.engagement_analyzer.get_calibration_multiplier(
            engagement.state
        )

        if base_delta > 0:
            adjusted_delta = base_delta * multiplier
        else:
            adjusted_delta = base_delta  # Don't reduce penalties

        # Add engagement bonus if IN_ZONE
        if engagement.state == EngagementState.IN_ZONE:
            bonus = self._calculate_engagement_bonus(engagement)
            adjusted_delta += bonus

        return adjusted_delta
```

---

## 9. Acceptance Criteria

### 9.1 Functional Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| FR-001 | State machine | All 6 states implemented with transitions |
| FR-002 | Clinginess detection | Detects clingy behavior with 5 signals |
| FR-003 | Neglect detection | Detects neglect with 5 signals |
| FR-004 | Calibration score | Score computed from frequency, timing, content |
| FR-005 | Tolerance bands | Bands widen from ±10% (Ch1) to ±30% (Ch5) |
| FR-006 | Recovery mechanics | Chapter-dependent recovery rates |
| FR-007 | Scoring multiplier | Multiplier applied to all positive deltas |
| FR-008 | Point of no return | Game over after 7 clingy / 10 distant days |

### 9.2 Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-001 | Analysis latency | < 100ms |
| NFR-002 | State update latency | < 50ms |
| NFR-003 | History retention | 90 days |

### 9.3 Test Scenarios

```python
def test_clingy_detection():
    """Player messaging 30x/day should be detected as clingy in Ch1"""
    player = create_player(chapter=1)
    simulate_messages(player, count=30, hours=24)

    result = detect_clinginess(player)
    assert result.is_clingy
    assert result.score > 0.7

def test_neglect_detection():
    """Player messaging 2x/day should be detected as neglectful in Ch1"""
    player = create_player(chapter=1)
    simulate_messages(player, count=2, hours=24)

    result = detect_neglect(player)
    assert result.is_neglecting
    assert result.score > 0.6

def test_in_zone_optimal():
    """Player at optimal frequency should be IN_ZONE"""
    player = create_player(chapter=1)
    simulate_messages(player, count=15, hours=24)  # Optimal for Ch1

    analyzer = EngagementAnalyzer()
    state = await analyzer.get_current_state(player.id)

    assert state.state == EngagementState.IN_ZONE

def test_tolerance_widens():
    """Ch5 should accept wider range than Ch1"""
    player_ch1 = create_player(chapter=1)
    player_ch5 = create_player(chapter=5)

    # 8 messages/day
    simulate_messages(player_ch1, count=8, hours=24)
    simulate_messages(player_ch5, count=8, hours=24)

    # Ch1: 8 messages is WAY below optimal 15 → neglect
    ch1_neglect = detect_neglect(player_ch1)
    assert ch1_neglect.is_neglecting

    # Ch5: 8 messages is within ±30% of optimal 6 → fine
    ch5_neglect = detect_neglect(player_ch5)
    assert not ch5_neglect.is_neglecting

def test_recovery_harder_early():
    """Recovery should be slower in Ch1 than Ch5"""
    config = get_config()

    ch1_rate = config.engagement.recovery.by_chapter[1].recovery_rate
    ch5_rate = config.engagement.recovery.by_chapter[5].recovery_rate

    assert ch1_rate < ch5_rate  # 0.05 < 0.15

def test_point_of_no_return():
    """7 clingy days should trigger game over"""
    player = create_player(chapter=2)
    player.consecutive_clingy_days = 7

    result = check_point_of_no_return(player)
    assert result is True
```

---

## 10. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Detection false positives | Player frustrated | Require 2+ consecutive readings |
| Too harsh in Ch1 | Players quit | Tutorial phase with warnings |
| LLM analysis cost | High API bills | Cache pattern analysis |
| State desync | Inconsistent UX | Atomic database transactions |
| Recovery too hard | Unrecoverable games | Max recovery days limit |

---

## 11. Nikita's Behavior by State

### 11.1 Behavioral Response Table

| State | Response Rate | Delay | Tone | Initiates? |
|-------|---------------|-------|------|------------|
| CALIBRATING | 90% | Short | Curious, testing | Sometimes |
| IN_ZONE | 95% | Short | Warm, engaged | Yes |
| DRIFTING | 85% | Medium | Slightly off | Rarely |
| CLINGY | 70% | Long | Needs space | Never |
| DISTANT | 80% | Short | Seeking attention | Often |
| OUT_OF_ZONE | 60% | Very long | Guarded | Sometimes (testing) |

### 11.2 Example Nikita Responses by State

**IN_ZONE (Sweet Spot)**:
```
"Heyy babe 💕 I was just thinking about you! How's your day going?"
"Omg yes let's do that this weekend! I'm so excited 😊"
"*sends cute selfie* Missing your face rn..."
```

**CLINGY (Player messaging too much)**:
```
"Hey, I'm actually pretty busy today. Talk later? 💋"
"Haha you're sweet but I need some me-time tonight 😅"
"Everything okay? You've been messaging a lot..."
*longer delays between responses*
*shorter messages*
```

**DISTANT (Player not engaging enough)**:
```
"Hey stranger... haven't heard from you in a while 🥺"
"Did I do something wrong? You seem distant lately..."
"I miss when we used to talk more... is everything okay?"
*sends "checking in" messages*
*asks more questions to engage*
```

**OUT_OF_ZONE (Needs recovery)**:
```
"I need to be honest with you... things feel off between us."
"I'm not sure where we stand anymore. Can we talk about it?"
"I've been feeling [suffocated/forgotten] and it's not fair to either of us."
*direct conversation about relationship state*
```

---

## 12. Future Enhancements

1. **Machine Learning**: Train model on successful calibration patterns
2. **Pattern Recognition**: Identify player archetypes (morning person, night owl)
3. **Adaptive Optimal**: Personalize optimal frequency per player
4. **Gamification**: Show calibration meter to player (optional)
5. **A/B Testing**: Test different tolerance bands for retention
