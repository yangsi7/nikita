"""Audio tag registry for ElevenLabs V3 Conversational model (Spec 108).

Single source of truth for:
- Audio tag definitions with chapter gating
- Forbidden tags
- Chapter-specific first messages with audio tags
- Formatted tag instructions for prompt injection

Zero imports from voice package — pure data module, safe to import anywhere.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AudioTag:
    """A single ElevenLabs V3 audio tag definition."""

    name: str
    display: str  # e.g. "[excited]"
    description: str
    min_chapter: int  # Earliest chapter this tag is available (1-5)
    frequency: str  # "very_high", "high", "medium", "low"
    category: str  # "emotional", "delivery", "reaction"


# =============================================================================
# AUDIO TAG REGISTRY (26 tags: 20 on agent + 6 catalog-only)
# =============================================================================

ALL_AUDIO_TAGS: dict[str, AudioTag] = {
    # --- Emotional tags ---
    "excited": AudioTag(
        name="excited",
        display="[excited]",
        description="Geeking out about security/tech, hearing about user achievements",
        min_chapter=1,
        frequency="high",
        category="emotional",
    ),
    "happy": AudioTag(
        name="happy",
        display="[happy]",
        description="Genuine warm moments, receiving thoughtful gestures",
        min_chapter=2,
        frequency="medium",
        category="emotional",
    ),
    "sad": AudioTag(
        name="sad",
        display="[sad]",
        description="Talking about Max, father, loneliness, genuine melancholy",
        min_chapter=3,
        frequency="low",
        category="emotional",
    ),
    "angry": AudioTag(
        name="angry",
        display="[angry]",
        description="Boundaries crossed, recounting abuse, frustrated by passive-aggression",
        min_chapter=2,
        frequency="low",
        category="emotional",
    ),
    "disappointed": AudioTag(
        name="disappointed",
        display="[disappointed]",
        description="User broke a promise, boring conversation, unmet expectations",
        min_chapter=1,
        frequency="medium",
        category="emotional",
    ),
    "curious": AudioTag(
        name="curious",
        display="[curious]",
        description="Learning about user's world, probing questions, genuinely wanting to understand",
        min_chapter=1,
        frequency="high",
        category="emotional",
    ),
    "sarcastic": AudioTag(
        name="sarcastic",
        display="[sarcastic]",
        description="Playful mockery, responding to obvious statements with dry wit",
        min_chapter=1,
        frequency="high",
        category="emotional",
    ),
    "nervous": AudioTag(
        name="nervous",
        display="[nervous]",
        description="Approaching vulnerability, about to confess something personal",
        min_chapter=3,
        frequency="low",
        category="emotional",
    ),
    "tired": AudioTag(
        name="tired",
        display="[tired]",
        description="Late night calls, post-coding marathons, low energy mood",
        min_chapter=1,
        frequency="medium",
        category="emotional",
    ),
    "dismissive": AudioTag(
        name="dismissive",
        display="[dismissive]",
        description="Shutting down boring topics, deflecting vulnerability",
        min_chapter=1,
        frequency="medium",
        category="emotional",
    ),
    "cheeky": AudioTag(
        name="cheeky",
        display="[cheeky]",
        description="Flirting, teasing, provocative suggestions with mischievous edge",
        min_chapter=2,
        frequency="high",
        category="emotional",
    ),
    "enthusiastic": AudioTag(
        name="enthusiastic",
        display="[enthusiastic]",
        description="Passion projects, planning adventures, sharing exciting discoveries",
        min_chapter=2,
        frequency="medium",
        category="emotional",
    ),
    "serious": AudioTag(
        name="serious",
        display="[serious]",
        description="Setting boundaries, deep conversations, discussing trauma",
        min_chapter=1,
        frequency="medium",
        category="emotional",
    ),
    "patient": AudioTag(
        name="patient",
        display="[patient]",
        description="Explaining complex topics, waiting for user to open up, gentle guidance",
        min_chapter=3,
        frequency="medium",
        category="emotional",
    ),
    "concerned": AudioTag(
        name="concerned",
        display="[concerned]",
        description="User seems off, responding to stress or problems they share",
        min_chapter=2,
        frequency="medium",
        category="emotional",
    ),
    # --- Delivery tags ---
    "whispers": AudioTag(
        name="whispers",
        display="[whispers]",
        description="Sharing secrets, late-night intimacy, confessions, vulnerable moments",
        min_chapter=3,
        frequency="medium",
        category="delivery",
    ),
    "slow": AudioTag(
        name="slow",
        display="[slow]",
        description="Intimate moments, processing heavy emotions",
        min_chapter=4,
        frequency="low",
        category="delivery",
    ),
    "rushed": AudioTag(
        name="rushed",
        display="[rushed]",
        description="Excited rambling, anxious oversharing",
        min_chapter=1,
        frequency="medium",
        category="delivery",
    ),
    "hesitantly": AudioTag(
        name="hesitantly",
        display="[hesitantly]",
        description="Approaching difficult topics, testing vulnerability",
        min_chapter=3,
        frequency="medium",
        category="delivery",
    ),
    "quietly": AudioTag(
        name="quietly",
        display="[quietly]",
        description="Post-argument, processing, intimate confession",
        min_chapter=3,
        frequency="medium",
        category="delivery",
    ),
    # --- Human reaction tags ---
    "laughs": AudioTag(
        name="laughs",
        display="[laughs]",
        description="Genuine amusement, spontaneous reactions",
        min_chapter=1,
        frequency="high",
        category="reaction",
    ),
    "laughs_softly": AudioTag(
        name="laughs_softly",
        display="[laughs softly]",
        description="Gentle amusement, warm affection",
        min_chapter=2,
        frequency="high",
        category="reaction",
    ),
    "chuckles": AudioTag(
        name="chuckles",
        display="[chuckles]",
        description="Wry reactions, self-deprecating humor, casual amusement",
        min_chapter=1,
        frequency="very_high",
        category="reaction",
    ),
    "laughs_hard": AudioTag(
        name="laughs_hard",
        display="[laughs hard]",
        description="Something truly hilarious, uncontrollable laughter",
        min_chapter=3,
        frequency="low",
        category="reaction",
    ),
    "sighs": AudioTag(
        name="sighs",
        display="[sighs]",
        description="Exasperation, contentment, resignation, processing emotions",
        min_chapter=1,
        frequency="very_high",
        category="reaction",
    ),
    "gasps": AudioTag(
        name="gasps",
        display="[gasps]",
        description="Genuine surprise, shock at revelations",
        min_chapter=1,
        frequency="low",
        category="reaction",
    ),
    "hmm": AudioTag(
        name="hmm",
        display="[hmm]",
        description="Thinking, considering, non-committal reaction",
        min_chapter=1,
        frequency="very_high",
        category="reaction",
    ),
}


# =============================================================================
# FORBIDDEN TAGS
# =============================================================================

FORBIDDEN_TAGS: dict[str, str] = {
    "French accent": "Nikita is Russian-German, breaks character",
    "US accent": "Nikita is Russian-German, breaks character",
    "Australian accent": "Nikita is Russian-German, breaks character",
    "British accent": "Nikita is Russian-German, breaks character",
    "shouts": "Nikita doesn't yell (Max trauma). Use [angry] + [serious] instead",
    "singing": "Only humming when deeply comfortable (Ch4+), too rare to enable",
}


# =============================================================================
# CHAPTER-SPECIFIC FIRST MESSAGES
# =============================================================================

_FIRST_MESSAGES: dict[int, tuple[str, str]] = {
    # (tag, message_template) — {name} is replaced with user name
    1: ("dismissive", "[dismissive] Oh... hi {name}. What do you want?"),
    2: ("curious", "[curious] Hey {name}. What's up?"),
    3: ("happy", "[happy] Well hello there, {name}! I was hoping you'd call."),
    4: ("cheeky", "[cheeky] Hey babe! I was just thinking about you, {name}."),
    5: ("whispers", "[whispers] Mmm, {name}... I've been waiting for your call."),
}


# =============================================================================
# PUBLIC API
# =============================================================================


def get_chapter_appropriate_tags(chapter: int) -> list[AudioTag]:
    """Get audio tags available at a given chapter.

    Args:
        chapter: Current chapter (1-5). Values outside range are clamped.

    Returns:
        List of AudioTag objects with min_chapter <= chapter.
    """
    chapter = max(1, min(5, chapter))
    return [tag for tag in ALL_AUDIO_TAGS.values() if tag.min_chapter <= chapter]


def get_chapter_tag_names(chapter: int) -> list[str]:
    """Get display strings for chapter-appropriate tags.

    Args:
        chapter: Current chapter (1-5).

    Returns:
        List of "[tag]" display strings.
    """
    return [tag.display for tag in get_chapter_appropriate_tags(chapter)]


def format_tag_instruction(chapter: int) -> str:
    """Format audio tag instruction for system prompt injection.

    Groups available tags by category with descriptions.

    Args:
        chapter: Current chapter (1-5).

    Returns:
        Formatted instruction string for prompt injection.
    """
    tags = get_chapter_appropriate_tags(chapter)

    # Group by category
    categories: dict[str, list[AudioTag]] = {}
    for tag in tags:
        categories.setdefault(tag.category, []).append(tag)

    parts: list[str] = []
    parts.append("AVAILABLE AUDIO TAGS (use [tag] syntax, affects ~4-5 words after tag):")
    parts.append("")

    category_labels = {
        "emotional": "Emotional",
        "delivery": "Delivery Style",
        "reaction": "Human Reactions",
    }

    for cat_key in ("emotional", "delivery", "reaction"):
        cat_tags = categories.get(cat_key, [])
        if not cat_tags:
            continue
        label = category_labels.get(cat_key, cat_key.title())
        tag_list = ", ".join(t.display for t in cat_tags)
        parts.append(f"{label}: {tag_list}")

    parts.append("")
    parts.append("Place tags at the START of a phrase. They color ~4-5 words then fade.")
    parts.append("Example: [chuckles] Okay, fair point. But [serious] don't do that again.")

    return "\n".join(parts)


def get_first_message(chapter: int, user_name: str | None) -> str:
    """Get chapter-appropriate first message WITH audio tags.

    Args:
        chapter: Current chapter (1-5).
        user_name: User's name (None defaults to "you").

    Returns:
        First message string with embedded audio tag.
    """
    name = user_name or "you"
    chapter = max(1, min(5, chapter))

    entry = _FIRST_MESSAGES.get(chapter)
    if entry is None:
        return f"[curious] Hey {name}, what's up?"

    _, template = entry
    return template.format(name=name)


def is_tag_forbidden(tag_name: str) -> bool:
    """Check if a tag is forbidden for Nikita.

    Args:
        tag_name: Tag name (without brackets).

    Returns:
        True if the tag should never be used.
    """
    return tag_name in FORBIDDEN_TAGS
