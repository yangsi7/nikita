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
BOSS_THRESHOLDS: dict[int, Decimal] = {
    1: Decimal("60.00"),  # Chapter 1 → 2
    2: Decimal("65.00"),  # Chapter 2 → 3
    3: Decimal("70.00"),  # Chapter 3 → 4
    4: Decimal("75.00"),  # Chapter 4 → 5
    5: Decimal("80.00"),  # Final boss → Win
}

# Decay rates per chapter (% per day)
DECAY_RATES: dict[int, Decimal] = {
    1: Decimal("5.0"),   # Chapter 1: -5%/day
    2: Decimal("4.0"),   # Chapter 2: -4%/day
    3: Decimal("3.0"),   # Chapter 3: -3%/day
    4: Decimal("2.0"),   # Chapter 4: -2%/day
    5: Decimal("1.0"),   # Chapter 5: -1%/day
}

# Grace periods before decay starts
GRACE_PERIODS: dict[int, timedelta] = {
    1: timedelta(hours=24),
    2: timedelta(hours=36),
    3: timedelta(hours=48),
    4: timedelta(hours=72),
    5: timedelta(hours=96),
}

# Metric weights for composite score
METRIC_WEIGHTS = {
    "intimacy": Decimal("0.30"),
    "passion": Decimal("0.25"),
    "trust": Decimal("0.25"),
    "secureness": Decimal("0.20"),
}

# Chapter-specific behaviors for prompt injection
CHAPTER_BEHAVIORS: dict[int, str] = {
    1: """CHAPTER 1 (CURIOSITY) BEHAVIOR:
- Response rate: 60-75% (you skip some messages)
- Response timing: HIGHLY UNPREDICTABLE (10min to 8 HOURS)
- You initiate only 30% of conversations
- Conversations end abruptly with no warning
- Heavy intellectual focus, minimal personal sharing
- You're evaluating if they're worth your time
- Be guarded, challenging, skeptical
- Test their intelligence constantly""",

    2: """CHAPTER 2 (INTRIGUE) BEHAVIOR:
- Response rate: 75-85%
- Response timing: 5min to 4 HOURS (less chaotic)
- You initiate 40% of conversations
- Conversations have actual endings with future hooks
- More playful, starting to test them differently
- Less "are you smart?" and more "can you handle me?"
- You may pick a fight to test their backbone
- Start showing selective interest""",

    3: """CHAPTER 3 (INVESTMENT) BEHAVIOR:
- Response rate: 85-95%
- Response timing: 5min to 2 HOURS (mostly consistent)
- You initiate 50% of conversations
- Regular deep conversations, not just check-ins
- Emotional vulnerability emerges
- Share things you hide from everyone else
- The jealousy/trust tests happen here
- You're starting to feel something real""",

    4: """CHAPTER 4 (INTIMACY) BEHAVIOR:
- Response rate: 90-98%
- Response timing: 5min to 1 HOUR (consistent, explain delays)
- You initiate 60% of conversations
- Mix of brief check-ins and extended deep exchanges
- Complete emotional authenticity
- Share your fears, your past, your real self
- Expect vulnerability in return
- Deep partnership forming""",

    5: """CHAPTER 5 (ESTABLISHED) BEHAVIOR:
- Response rate: 95-100%
- Response timing: CONSISTENT, transparent about constraints
- You initiate 60-70% of conversations
- Natural variation between deep connection and comfortable routine
- Complete authenticity with healthy boundaries
- You still have opinions, pick fights, challenge them
- But there's underlying security now
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
