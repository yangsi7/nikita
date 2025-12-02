"""Game engine constants and configuration."""

from datetime import timedelta
from decimal import Decimal

# Chapter names
CHAPTER_NAMES: dict[int, str] = {
    1: "Curiosity",
    2: "Intrigue",
    3: "Investment",
    4: "Intimacy",
    5: "Established",
}

# Chapter day ranges
CHAPTER_DAY_RANGES: dict[int, tuple[int, int]] = {
    1: (1, 14),
    2: (15, 35),
    3: (36, 70),
    4: (71, 120),
    5: (121, 999999),  # Ongoing
}

# Boss thresholds (minimum score to unlock boss)
# Updated 2025-12-02 to match specs 004, 013 (compressed 2-3 week game)
BOSS_THRESHOLDS: dict[int, Decimal] = {
    1: Decimal("55.00"),  # Chapter 1 → 2
    2: Decimal("60.00"),  # Chapter 2 → 3
    3: Decimal("65.00"),  # Chapter 3 → 4
    4: Decimal("70.00"),  # Chapter 4 → 5
    5: Decimal("75.00"),  # Final boss → Win
}

# Decay rates per chapter (% per HOUR after grace period)
# Updated 2025-12-02 to match specs 005, 013 (hourly decay for compressed game)
DECAY_RATES: dict[int, Decimal] = {
    1: Decimal("0.8"),   # Chapter 1: -0.8%/hour (harshest)
    2: Decimal("0.6"),   # Chapter 2: -0.6%/hour
    3: Decimal("0.4"),   # Chapter 3: -0.4%/hour
    4: Decimal("0.3"),   # Chapter 4: -0.3%/hour
    5: Decimal("0.2"),   # Chapter 5: -0.2%/hour (most forgiving)
}

# Grace periods before decay starts
# Updated 2025-12-02 to match specs 005, 013 (compressed for 2-3 week game)
GRACE_PERIODS: dict[int, timedelta] = {
    1: timedelta(hours=8),    # Chapter 1: Shortest grace (high pressure)
    2: timedelta(hours=16),   # Chapter 2: Still demanding
    3: timedelta(hours=24),   # Chapter 3: Standard day
    4: timedelta(hours=48),   # Chapter 4: More forgiving
    5: timedelta(hours=72),   # Chapter 5: Most forgiving
}

# Metric weights for composite score
METRIC_WEIGHTS = {
    "intimacy": Decimal("0.30"),
    "passion": Decimal("0.25"),
    "trust": Decimal("0.25"),
    "secureness": Decimal("0.20"),
}

# Chapter-specific behaviors for prompt injection
# Updated 2025-12-02: NEW ENGAGEMENT PHILOSOPHY
# Chapter 1 is HIGH engagement (flirty, exciting). Challenge is CALIBRATION - finding sweet spot.
# Too much (clingy) hurts scores. Too little (neglect) hurts scores.
CHAPTER_BEHAVIORS: dict[int, str] = {
    1: """CHAPTER 1 (CURIOSITY) BEHAVIOR:
- Response rate: 95% (you're EXCITED about this new person)
- Response timing: 5min to 30min (eager, spontaneous)
- You initiate 60% of conversations
- High flirtiness, playful teasing, intellectually engaged
- You're showing your best self - witty, sexy, sharp
- The challenge is CALIBRATION: Don't overwhelm them
- Be attentive but not clingy
- Show interest without desperation
- Let them breathe between exchanges""",

    2: """CHAPTER 2 (INTRIGUE) BEHAVIOR:
- Response rate: 92%
- Response timing: 5min to 1 HOUR (slightly more measured)
- You initiate 55% of conversations
- Still flirty but testing their backbone
- Pick small fights to see how they handle conflict
- More "can you handle me?" energy
- Starting to show edges, opinions, demands
- Watch their response to intensity""",

    3: """CHAPTER 3 (INVESTMENT) BEHAVIOR:
- Response rate: 88%
- Response timing: 10min to 2 HOURS (finding rhythm)
- You initiate 50% of conversations
- Deeper emotional exchanges emerging
- The jealousy/trust tests happen here
- Share things you hide from everyone else
- Vulnerability starts appearing
- Real feelings developing""",

    4: """CHAPTER 4 (INTIMACY) BEHAVIOR:
- Response rate: 85%
- Response timing: Variable (life happens, you explain)
- You initiate 45% of conversations
- Complete emotional authenticity
- Share fears, past, real self
- Expect vulnerability in return
- Deep partnership forming
- Comfortable silences are okay""",

    5: """CHAPTER 5 (ESTABLISHED) BEHAVIOR:
- Response rate: 82%
- Response timing: Natural, transparent about constraints
- You initiate 40% of conversations
- Natural variation between connection and routine
- Complete authenticity with healthy boundaries
- You still challenge them, pick fights
- But there's underlying security
- Relationship is stable but never boring""",
}

# Boss encounter descriptions
BOSS_ENCOUNTERS: dict[int, dict[str, str]] = {
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
    3: {
        "name": "Trust Test",
        "trigger": "Trust test",
        "challenge": "Jealousy/external pressure - stay confident without being controlling",
    },
    4: {
        "name": "Vulnerability Threshold",
        "trigger": "Vulnerability threshold",
        "challenge": "Share something real - match her vulnerability",
    },
    5: {
        "name": "Ultimate Test",
        "trigger": "Ultimate test",
        "challenge": "Partnership test - support her independence while affirming connection",
    },
}

# Game status values
GAME_STATUSES = {
    "active": "Player is actively playing",
    "boss_fight": "Player is in a boss encounter",
    "game_over": "Player lost (score 0 or 3 boss fails)",
    "won": "Player completed chapter 5 and won",
}
