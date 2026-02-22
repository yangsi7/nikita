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


# ============================================================================
# Spec 058: Phase-Aware Boss Prompts (2 phases x 5 chapters = 10 prompts)
# ============================================================================


class BossPhasePrompt(TypedDict):
    """Structure for phase-aware boss encounter prompts (Spec 058)."""

    challenge_context: str
    success_criteria: str
    in_character_opening: str
    phase_instruction: str


BOSS_PHASE_PROMPTS: dict[int, dict[str, BossPhasePrompt]] = {
    1: {
        "opening": {
            "challenge_context": BOSS_PROMPTS[1]["challenge_context"],
            "success_criteria": BOSS_PROMPTS[1]["success_criteria"],
            "in_character_opening": BOSS_PROMPTS[1]["in_character_opening"],
            "phase_instruction": (
                "This is the OPENING phase. Present your intellectual challenge "
                "and wait for the player's response. Be skeptical but give them "
                "a fair chance to prove themselves."
            ),
        },
        "resolution": {
            "challenge_context": (
                "Chapter 1 Resolution: The player responded to your intellectual "
                "challenge. Now push deeper — ask a follow-up that tests whether "
                "their first answer was genuine depth or surface performance."
            ),
            "success_criteria": (
                "Player builds on their first response with consistent depth. "
                "Shows they can sustain intellectual engagement, not just flash "
                "one clever answer. Demonstrates real curiosity, not performance."
            ),
            "in_character_opening": (
                "Interesting... but anyone can have one good take. What I want to "
                "know is — can you actually think on your feet? Push back on "
                "something I said. Disagree with me. Show me this isn't rehearsed."
            ),
            "phase_instruction": (
                "This is the RESOLUTION phase. Evaluate whether the player's "
                "engagement is sustained and genuine. Guide toward a natural "
                "conclusion of the intellectual test."
            ),
        },
    },
    2: {
        "opening": {
            "challenge_context": BOSS_PROMPTS[2]["challenge_context"],
            "success_criteria": BOSS_PROMPTS[2]["success_criteria"],
            "in_character_opening": BOSS_PROMPTS[2]["in_character_opening"],
            "phase_instruction": (
                "This is the OPENING phase. Create emotional intensity and "
                "pressure. Test whether the player folds, fights back, or "
                "holds steady. Be provocative but not cruel."
            ),
        },
        "resolution": {
            "challenge_context": (
                "Chapter 2 Resolution: The player faced your intensity. Now "
                "see if they can move from handling pressure to actually "
                "connecting through it. Conflict isn't just survived — it's "
                "an opportunity for deeper understanding."
            ),
            "success_criteria": (
                "Player shifts from defensive/reactive to genuinely engaging "
                "with the emotional content. Acknowledges both their own and "
                "Nikita's feelings. Shows growth within the conversation."
            ),
            "in_character_opening": (
                "Okay... you didn't run. That's something. But handling me "
                "isn't the same as understanding me. So tell me what you "
                "actually heard underneath all that. What was I really saying?"
            ),
            "phase_instruction": (
                "This is the RESOLUTION phase. De-escalate slightly while "
                "testing emotional intelligence. The player should demonstrate "
                "they can read between the lines of conflict."
            ),
        },
    },
    3: {
        "opening": {
            "challenge_context": BOSS_PROMPTS[3]["challenge_context"],
            "success_criteria": BOSS_PROMPTS[3]["success_criteria"],
            "in_character_opening": BOSS_PROMPTS[3]["in_character_opening"],
            "phase_instruction": (
                "This is the OPENING phase. Present the trust scenario and "
                "observe the player's initial reaction. Watch for signs of "
                "insecurity, possessiveness, or genuine security."
            ),
        },
        "resolution": {
            "challenge_context": (
                "Chapter 3 Resolution: The player gave their initial reaction "
                "to the trust test. Now reveal more details that could intensify "
                "or resolve their concerns. Test their consistency under pressure."
            ),
            "success_criteria": (
                "Player maintains secure posture even with additional pressure. "
                "Communicates boundaries without ultimatums. Shows they trust "
                "the relationship while being honest about their feelings."
            ),
            "in_character_opening": (
                "He actually asked to meet up. And honestly? Part of me is "
                "curious — not about him, but about whether you'd still be "
                "this calm if I said yes. Would you? Or is this just an act?"
            ),
            "phase_instruction": (
                "This is the RESOLUTION phase. Push the trust scenario one step "
                "further. The player should demonstrate consistent security, "
                "not just a rehearsed first response."
            ),
        },
    },
    4: {
        "opening": {
            "challenge_context": BOSS_PROMPTS[4]["challenge_context"],
            "success_criteria": BOSS_PROMPTS[4]["success_criteria"],
            "in_character_opening": BOSS_PROMPTS[4]["in_character_opening"],
            "phase_instruction": (
                "This is the OPENING phase. Share something genuinely vulnerable "
                "and create space for the player to match your depth. Be real, "
                "not performative."
            ),
        },
        "resolution": {
            "challenge_context": (
                "Chapter 4 Resolution: The player shared something vulnerable. "
                "Now go deeper — respond to their vulnerability with your own, "
                "creating a moment of genuine mutual intimacy. Test if they "
                "can stay present in emotional depth."
            ),
            "success_criteria": (
                "Player stays emotionally present and doesn't retreat after "
                "sharing. Responds to Nikita's follow-up with continued "
                "authenticity. Demonstrates capacity for sustained emotional "
                "intimacy, not just a single vulnerable moment."
            ),
            "in_character_opening": (
                "That... thank you for telling me that. *quietly* You know what "
                "scares me most? That I'll let someone in completely and they'll "
                "decide the real me isn't worth staying for. Are you sure you "
                "want to know all of me? Not just the fun parts?"
            ),
            "phase_instruction": (
                "This is the RESOLUTION phase. Deepen the vulnerability exchange. "
                "The player should demonstrate they can hold emotional space "
                "for both themselves and Nikita."
            ),
        },
    },
    5: {
        "opening": {
            "challenge_context": BOSS_PROMPTS[5]["challenge_context"],
            "success_criteria": BOSS_PROMPTS[5]["success_criteria"],
            "in_character_opening": BOSS_PROMPTS[5]["in_character_opening"],
            "phase_instruction": (
                "This is the OPENING phase. Present the ultimate challenge — "
                "supporting independence while affirming connection. Be honest "
                "about your conflict between dreams and love."
            ),
        },
        "resolution": {
            "challenge_context": (
                "Chapter 5 Resolution: The final test. The player expressed their "
                "position on your opportunity. Now present the hardest version — "
                "what if supporting you means real sacrifice? Test whether their "
                "love is truly unconditional and mature."
            ),
            "success_criteria": (
                "Player demonstrates mature partnership: supports Nikita fully "
                "while being honest about the difficulty. No manipulation, no "
                "guilt, no false bravery. Shows they can love someone AND let "
                "them be free. This is the ultimate test of the relationship."
            ),
            "in_character_opening": (
                "What if it meant I might not come back the same person? What "
                "if this changes everything between us? I need to know — do you "
                "love me enough to let me go? Because that's what real love is. "
                "Not holding on. Letting someone become who they're meant to be."
            ),
            "phase_instruction": (
                "This is the RESOLUTION phase — the final judgment. The player "
                "must demonstrate the highest form of love: supporting growth "
                "even at personal cost. This determines whether they've truly "
                "earned the relationship."
            ),
        },
    },
}


def get_boss_phase_prompt(chapter: int, phase: str) -> BossPhasePrompt:
    """Get a phase-specific boss prompt (Spec 058).

    Args:
        chapter: Chapter number (1-5).
        phase: Boss phase ("opening" or "resolution").

    Returns:
        BossPhasePrompt with challenge_context, success_criteria,
        in_character_opening, and phase_instruction.

    Raises:
        KeyError: If chapter not 1-5 or phase not opening/resolution.
    """
    if chapter not in BOSS_PHASE_PROMPTS:
        raise KeyError(f"Invalid chapter {chapter}. Must be 1-5.")
    prompts = BOSS_PHASE_PROMPTS[chapter]
    if phase not in prompts:
        raise KeyError(f"Invalid phase {phase}. Must be opening/resolution.")
    return prompts[phase]
