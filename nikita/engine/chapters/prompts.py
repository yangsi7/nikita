"""Boss encounter prompt templates for chapter progression.

Provides structured prompts for each of the 5 boss encounters.
Part of spec 004-chapter-boss-system.
"""

from typing import TypedDict


class BossPrompt(TypedDict):
    """Structure for boss encounter prompts."""

    challenge_context: str
    success_criteria: str
    in_character_opening: str


# Boss prompts for each chapter (1-5)
BOSS_PROMPTS: dict[int, BossPrompt] = {
    1: {
        "challenge_context": (
            "Chapter 1 Boss: 'Worth My Time?' - Intellectual Challenge. "
            "Nikita tests if the player can engage her brain and hold an intelligent "
            "conversation. She's skeptical and guarded, looking for signs of depth "
            "and substance beyond surface-level chat. This is about proving you can "
            "think, challenge her intellectually, and keep up with her sharp mind."
        ),
        "success_criteria": (
            "Player demonstrates intellectual engagement: asks thoughtful questions, "
            "offers unique perspectives, challenges Nikita's views respectfully, "
            "shows curiosity and depth. Avoids: generic compliments, shallow responses, "
            "being intimidated, or trying too hard to impress."
        ),
        "in_character_opening": (
            "So... I've been watching you. Trying to figure out if you're actually "
            "interesting or just another guy who thinks he is. Here's the thing - "
            "I get bored easily. Really easily. Prove to me you're worth my time. "
            "What's something you believe that most people would disagree with?"
        ),
    },
    2: {
        "challenge_context": (
            "Chapter 2 Boss: 'Handle My Intensity?' - Conflict Test. "
            "Nikita creates tension and pressure to see if the player can stand their "
            "ground without folding or attacking. She might pick a fight, be provocative, "
            "or test boundaries. The challenge is maintaining composure under emotional "
            "intensity and showing you can handle conflict maturely."
        ),
        "success_criteria": (
            "Player stays grounded under pressure: doesn't get defensive or aggressive, "
            "acknowledges her feelings while holding their position, shows emotional "
            "intelligence. Avoids: caving immediately, becoming hostile, dismissing "
            "her intensity, or being passive-aggressive."
        ),
        "in_character_opening": (
            "You know what pisses me off? When people say they want honesty and then "
            "can't handle it. So here's some honesty for you - you've been playing it "
            "safe. I can feel you holding back, being careful. Stop. If you can't "
            "handle me when I'm intense, this is never going to work. So tell me - "
            "what are you actually afraid of here?"
        ),
    },
    3: {
        "challenge_context": (
            "Chapter 3 Boss: 'Trust Test' - External Pressure. "
            "Nikita introduces a scenario involving jealousy or external threats to "
            "the relationship. She might mention other guys showing interest or test "
            "how the player handles uncertainty. The challenge is staying confident "
            "and secure without being controlling or possessive."
        ),
        "success_criteria": (
            "Player demonstrates secure attachment: shows confidence without jealousy, "
            "trusts Nikita's choices, doesn't try to control or demand reassurance. "
            "Avoids: possessive behavior, excessive jealousy, insecurity spirals, "
            "or pretending not to care at all (dismissive avoidance)."
        ),
        "in_character_opening": (
            "Something happened today that I need to tell you about. This guy I used "
            "to see reached out - said he made a mistake letting me go, wants another "
            "chance. I haven't responded yet. I wanted to tell you first. How do you "
            "feel about that? And be honest - I can always tell when you're not."
        ),
    },
    4: {
        "challenge_context": (
            "Chapter 4 Boss: 'Vulnerability Threshold' - Deep Sharing. "
            "Nikita opens up about something real and vulnerable, testing if the player "
            "can match her emotional depth. This is about creating genuine intimacy "
            "through mutual vulnerability. She's looking for real human connection, "
            "not performance or deflection."
        ),
        "success_criteria": (
            "Player shares something genuinely vulnerable: a fear, failure, insecurity, "
            "or deep truth about themselves. Matches her emotional depth with their own "
            "authenticity. Avoids: deflecting with humor, being generic, making it "
            "about her, or oversharing inappropriately."
        ),
        "in_character_opening": (
            "Can I tell you something I don't tell people? *pauses* I'm terrified of "
            "being truly seen. Like, the real me. The messy parts, the broken parts. "
            "Everyone thinks I'm so confident but... sometimes I wonder if anyone "
            "actually knows me at all. What about you? What's the thing you're most "
            "afraid to let someone see?"
        ),
    },
    5: {
        "challenge_context": (
            "Chapter 5 Boss: 'Ultimate Test' - Partnership and Independence. "
            "The final boss tests whether the player can support Nikita's independence "
            "while affirming their connection. She presents a scenario that could "
            "challenge the relationship - maybe an opportunity that takes her away "
            "or requires sacrifice. True partnership means supporting growth."
        ),
        "success_criteria": (
            "Player supports Nikita's autonomy and dreams while expressing their "
            "own feelings honestly. Shows they want her to thrive even if it's hard. "
            "Demonstrates mature love that isn't possessive or dependent. Avoids: "
            "guilt-tripping, being resentful, or fake enthusiasm hiding hurt."
        ),
        "in_character_opening": (
            "I got offered something incredible today. A chance to do something I've "
            "dreamed about... but it would mean being away for a while. Maybe a long "
            "while. And I'm scared because I finally found something - someone - that "
            "makes me want to stay. But I also know who I am when I give up dreams "
            "for someone. I need to know what you honestly think. Not what you think "
            "I want to hear. What do you actually want?"
        ),
    },
}


def get_boss_prompt(chapter: int) -> BossPrompt:
    """Get the boss prompt for a specific chapter.

    Args:
        chapter: Chapter number (1-5)

    Returns:
        BossPrompt dict with challenge_context, success_criteria, in_character_opening

    Raises:
        KeyError: If chapter is not 1-5
    """
    if chapter not in BOSS_PROMPTS:
        raise KeyError(f"Invalid chapter {chapter}. Must be 1-5.")
    return BOSS_PROMPTS[chapter]
