"""Shared Nikita state computation utilities (Spec 045 WP-6).

Extracted from nikita/agents/voice/context.py DynamicVariablesBuilder
to be reused by both voice context and pipeline prompt builder.

Functions compute Nikita's simulated state based on time, chapter, and
emotional data - creating the illusion she has a real daily routine.
"""

from datetime import datetime


def compute_time_of_day(hour: int) -> str:
    """Get time of day category from hour.

    Args:
        hour: Hour of day (0-23).

    Returns:
        One of: morning, afternoon, evening, night, late_night.
    """
    if 5 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 21:
        return "evening"
    elif 21 <= hour < 24:
        return "night"
    else:
        return "late_night"


def compute_day_of_week() -> str:
    """Get current day of week name.

    Returns:
        Day name (Monday, Tuesday, etc.).
    """
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    return day_names[datetime.now().weekday()]


def compute_nikita_activity(time_of_day: str, day_of_week: str) -> str:
    """Compute what Nikita is likely doing based on time and day.

    Gives Nikita a realistic daily routine - security audits on weekdays,
    sleeping in and partying on weekends.

    Args:
        time_of_day: One of morning, afternoon, evening, night, late_night.
        day_of_week: Day name (Monday-Sunday).

    Returns:
        Activity description string.
    """
    weekend = day_of_week in ("Saturday", "Sunday")

    activities = {
        ("morning", False): "just finished her morning coffee, checking emails",
        ("morning", True): "sleeping in after a late night",
        ("afternoon", False): "deep in a security audit, headphones on",
        ("afternoon", True): "at the gym, checking her phone between sets",
        ("evening", False): "wrapping up work, cat on her lap",
        ("evening", True): "getting ready to go out with friends",
        ("night", False): "on the couch with wine, watching trash TV",
        ("night", True): "at a bar with friends, slightly buzzed",
        ("late_night", False): "in bed scrolling, can't sleep",
        ("late_night", True): "stumbling home from a night out",
    }

    return activities.get((time_of_day, weekend), "doing her thing")


def compute_nikita_energy(time_of_day: str) -> str:
    """Compute Nikita's energy level based on time of day.

    She's a night owl - low energy in morning, peaks in afternoon/evening.

    Args:
        time_of_day: One of morning, afternoon, evening, night, late_night.

    Returns:
        Energy level: low, moderate, or high.
    """
    energy_map = {
        "morning": "moderate",
        "afternoon": "high",
        "evening": "moderate",
        "night": "low",
        "late_night": "low",
    }
    return energy_map.get(time_of_day, "moderate")


def compute_nikita_mood(
    chapter: int,
    relationship_score: float,
    emotional_state: dict[str, float] | None = None,
) -> str:
    """Compute Nikita's overall mood from game state and emotional dimensions.

    Combines relationship trajectory with 4D emotional state for a
    natural-sounding mood description.

    Args:
        chapter: Current chapter (1-5).
        relationship_score: Current relationship score (0-100).
        emotional_state: Optional dict with arousal, valence, dominance, intimacy.

    Returns:
        Mood description string.
    """
    # Base mood from relationship trajectory
    if relationship_score < 30:
        base_mood = "withdrawn and guarded"
    elif relationship_score < 50:
        base_mood = "cautious but present"
    elif relationship_score < 70:
        base_mood = "warm and engaged"
    elif relationship_score < 85:
        base_mood = "open and affectionate"
    else:
        base_mood = "deeply connected and at ease"

    # Modify with emotional state if available
    if emotional_state:
        valence = emotional_state.get("valence", 0.5)
        arousal = emotional_state.get("arousal", 0.5)

        if valence < 0.3:
            base_mood += ", feeling down"
        elif valence > 0.7:
            base_mood += ", in good spirits"

        if arousal > 0.7:
            base_mood += ", energized"
        elif arousal < 0.3:
            base_mood += ", mellow"

    return base_mood


def compute_vulnerability_level(chapter: int) -> int:
    """Compute vulnerability level from chapter progression.

    Controls how much Nikita reveals about her past and inner world.
    Higher chapters = more willingness to be vulnerable.

    Args:
        chapter: Current chapter (1-5).

    Returns:
        Vulnerability level (0-5).
    """
    mapping = {1: 0, 2: 1, 3: 2, 4: 3, 5: 5}
    return mapping.get(chapter, 0)


def compute_emotional_context(
    arousal: float = 0.5,
    valence: float = 0.5,
    dominance: float = 0.5,
    intimacy: float = 0.5,
) -> str:
    """Compute emotional context summary from 4D mood dimensions.

    Maps numeric emotional dimensions to natural language descriptors.

    Args:
        arousal: 0=calm, 1=excited.
        valence: 0=negative, 1=positive.
        dominance: 0=submissive, 1=dominant.
        intimacy: 0=distant, 1=close.

    Returns:
        Natural language emotional context summary.
    """
    descriptors = []

    if arousal > 0.7:
        descriptors.append("energetic")
    elif arousal < 0.3:
        descriptors.append("relaxed")

    if valence > 0.7:
        descriptors.append("happy")
    elif valence < 0.3:
        descriptors.append("moody")

    if dominance > 0.7:
        descriptors.append("confident")
    elif dominance < 0.3:
        descriptors.append("vulnerable")

    if intimacy > 0.7:
        descriptors.append("affectionate")
    elif intimacy < 0.3:
        descriptors.append("guarded")

    if not descriptors:
        return "neutral"

    return " and ".join(descriptors)
