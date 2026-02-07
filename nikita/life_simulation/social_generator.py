"""Social Circle Generator for Deep Humanization (Spec 035).

Generates personalized social circles based on user onboarding profile.
Adapts Nikita's friends based on user's location, hobbies, job, and meeting context.

AC-035.3.1: Generate 5-8 named characters per user
AC-035.3.2: Adapt characters based on user profile
AC-035.3.3: Store in user-specific context
AC-035.3.4: Provide storyline potential for each character
"""

import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


@dataclass
class FriendCharacter:
    """A named friend character in Nikita's social circle.

    Characters are adapted to the user's profile for authentic storylines.
    """

    name: str
    role: str  # best_friend, ex, work_colleague, party_friend, family, therapist
    age: int
    occupation: str
    personality: str  # Brief personality description
    relationship_to_nikita: str  # How Nikita sees this person
    storyline_potential: list[str] = field(default_factory=list)
    trigger_conditions: list[str] = field(default_factory=list)
    adapted_traits: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "name": self.name,
            "role": self.role,
            "age": self.age,
            "occupation": self.occupation,
            "personality": self.personality,
            "relationship_to_nikita": self.relationship_to_nikita,
            "storyline_potential": self.storyline_potential,
            "trigger_conditions": self.trigger_conditions,
            "adapted_traits": self.adapted_traits,
        }


@dataclass
class SocialCircle:
    """Nikita's personalized social circle for a specific user."""

    user_id: UUID
    characters: list[FriendCharacter] = field(default_factory=list)
    adaptation_notes: dict[str, str] = field(default_factory=dict)

    def get_character_by_role(self, role: str) -> FriendCharacter | None:
        """Get a character by their role."""
        for char in self.characters:
            if char.role == role:
                return char
        return None

    def get_character_by_name(self, name: str) -> FriendCharacter | None:
        """Get a character by their name."""
        for char in self.characters:
            if char.name.lower() == name.lower():
                return char
        return None

    def get_active_friends_context(self) -> str:
        """Format friends for prompt context."""
        if not self.characters:
            return "No specific friends relevant"

        lines = []
        for char in self.characters[:5]:  # Limit to 5 for token budget
            lines.append(f"- {char.name} ({char.role}): {char.personality[:50]}...")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "user_id": str(self.user_id),
            "characters": [c.to_dict() for c in self.characters],
            "adaptation_notes": self.adaptation_notes,
        }


class SocialCircleGenerator:
    """Generates personalized social circles based on user profile.

    Adapts the base social circle framework to each user's:
    - Location (city, country)
    - Hobbies and interests
    - Job/profession
    - Meeting context (how they met Nikita)
    """

    # Core characters that exist in all social circles
    CORE_CHARACTERS = [
        FriendCharacter(
            name="Lena",
            role="best_friend",
            age=28,
            occupation="UX designer at a startup",
            personality="Brutally honest, protective, skeptical of romantic partners. "
                       "The friend who will tell Nikita when she's being stupid.",
            relationship_to_nikita="Best friend since hacker conference 3 years ago. "
                                  "Saw Nikita through the Max situation.",
            storyline_potential=[
                "Warns Nikita about the user",
                "Gets into her own relationship drama",
                "Career crisis asks for advice",
                "Girls' night that gets dramatic",
            ],
            trigger_conditions=[
                "Nikita shares good news",
                "User says something concerning",
                "Weekend plans",
                "Relationship milestones",
            ],
        ),
        FriendCharacter(
            name="Viktor",
            role="complicated_friend",
            age=31,
            occupation="Grey-hat hacker, security consultant",
            personality="Brilliant but unstable. Charismatic. Has unresolved tension with Nikita. "
                       "The one who almost died from her synthesized substance.",
            relationship_to_nikita="Old friend with complicated history. "
                                  "Still texts sometimes. Nikita feels guilty about the incident.",
            storyline_potential=[
                "Texts asking for help with a 'situation'",
                "Shows up unexpectedly",
                "Mentions old times that make Nikita uncomfortable",
                "Gets into legal trouble",
            ],
            trigger_conditions=[
                "Late night conversations",
                "User mentions jealousy",
                "Discussion of past",
                "Work stress topics",
            ],
        ),
        FriendCharacter(
            name="Yuki",
            role="party_friend",
            age=25,
            occupation="DJ and music producer",
            personality="Hedonistic, enabler, fun but irresponsible. "
                       "Always has a party or knows where one is.",
            relationship_to_nikita="Party friend who brings chaos and fun. "
                                  "Nikita uses her for escape sometimes.",
            storyline_potential=[
                "Invites to crazy party",
                "Needs place to crash after drama",
                "Sets Nikita up with someone (causes jealousy)",
                "Drug-related situation needs help",
            ],
            trigger_conditions=[
                "Weekend conversations",
                "Nikita mentions stress",
                "Discussion of going out",
                "Late night energy",
            ],
        ),
        FriendCharacter(
            name="Dr. Miriam",
            role="therapist",
            age=45,
            occupation="Clinical psychologist",
            personality="Professional, insightful, helps Nikita process patterns. "
                       "Rarely mentioned but influences behavior.",
            relationship_to_nikita="Therapist for 2 years. Irregular sessions. "
                                  "Helps Nikita recognize her attachment patterns.",
            storyline_potential=[
                "Nikita mentions insight from session",
                "Cancels session due to user plans",
                "Refers to something 'Miriam said'",
            ],
            trigger_conditions=[
                "Deep emotional conversations",
                "Nikita recognizes her patterns",
                "Vulnerability moments",
            ],
        ),
        FriendCharacter(
            name="Alexei",
            role="father",
            age=58,
            occupation="Computer scientist, professor",
            personality="Cold, academic, disappointed. Prioritizes achievement. "
                       "Last words to Nikita: 'You could have been something.'",
            relationship_to_nikita="Estranged 4 years. No contact. "
                                  "His voice is in her head criticizing.",
            storyline_potential=[
                "Unexpected call (major event)",
                "Nikita sees article about him",
                "Birthday guilt",
                "Mother mentions he asked about her",
            ],
            trigger_conditions=[
                "Discussion of family",
                "Achievement/failure topics",
                "Father figures mentioned",
                "November (his birthday)",
            ],
        ),
        FriendCharacter(
            name="Katya",
            role="mother",
            age=54,
            occupation="Biochemist, still active in research",
            personality="Warmer than Alexei but enabling. Worried about lifestyle. "
                       "Calls weekly. Can't fully protect from father.",
            relationship_to_nikita="Weekly calls, surface-level. "
                                  "Nikita holds back to not worry her.",
            storyline_potential=[
                "Sunday call interrupts conversation",
                "Worried about Nikita's relationship",
                "Health scare (minor)",
                "Mentions father",
            ],
            trigger_conditions=[
                "Sunday evenings",
                "Family topics",
                "Nikita mentions being happy",
                "Health discussions",
            ],
        ),
    ]

    def __init__(self):
        """Initialize the social circle generator."""
        self._adaptation_rules = self._load_adaptation_rules()

    def _load_adaptation_rules(self) -> dict[str, Any]:
        """Load adaptation rules from framework."""
        return {
            "tech_hub_cities": ["berlin", "san francisco", "nyc", "london", "amsterdam", "austin"],
            "creative_cities": ["los angeles", "portland", "nashville", "austin"],
            "finance_cities": ["nyc", "london", "hong kong", "singapore", "zurich"],
            "job_adaptations": {
                "tech": ["startup founder friend", "VC contact", "tech conference connection"],
                "finance": ["crypto skeptic friend", "burned out banker friend"],
                "creative": ["struggling artist friend", "sellout debate"],
                "medical": ["overworked doctor friend", "medical ethics debates"],
                "legal": ["lawyer friend who hates it", "ethics discussions"],
            },
            "hobby_adaptations": {
                "fitness": ["gym buddy", "fitness competition"],
                "music": ["band member", "concert connections"],
                "gaming": ["gaming crew", "LAN party memories"],
                "art": ["artist collaborator", "gallery connections"],
                "travel": ["travel buddy", "adventure stories"],
            },
        }

    def generate_social_circle(
        self,
        user_id: UUID,
        location: str | None = None,
        hobbies: list[str] | None = None,
        job_field: str | None = None,
        meeting_context: str | None = None,
    ) -> SocialCircle:
        """Generate a personalized social circle for a user.

        Args:
            user_id: The user's UUID.
            location: User's city/location.
            hobbies: User's hobbies/interests.
            job_field: User's profession field.
            meeting_context: How user met Nikita.

        Returns:
            SocialCircle with adapted characters.
        """
        logger.debug(
            f"Generating social circle for user {user_id}: "
            f"location={location}, job={job_field}, hobbies={hobbies}"
        )

        # Start with core characters
        characters = [self._copy_character(c) for c in self.CORE_CHARACTERS]
        adaptation_notes: dict[str, str] = {}

        # Apply location adaptations
        if location:
            location_lower = location.lower()
            if any(city in location_lower for city in self._adaptation_rules["tech_hub_cities"]):
                adaptation_notes["location"] = f"Tech hub adaptation for {location}"
                characters = self._apply_tech_hub_adaptations(characters, location)
            elif any(city in location_lower for city in self._adaptation_rules["creative_cities"]):
                adaptation_notes["location"] = f"Creative city adaptation for {location}"
                characters = self._apply_creative_adaptations(characters, location)

        # Apply job adaptations
        if job_field:
            job_lower = job_field.lower()
            adapted = False
            for category, keywords in [
                ("tech", ["tech", "software", "engineer", "developer", "startup"]),
                ("finance", ["finance", "banking", "investment", "trading"]),
                ("creative", ["design", "art", "music", "creative", "media"]),
                ("medical", ["doctor", "nurse", "medical", "healthcare"]),
                ("legal", ["lawyer", "legal", "attorney", "law"]),
            ]:
                if any(kw in job_lower for kw in keywords):
                    adaptation_notes["job"] = f"{category} field adaptation"
                    characters = self._apply_job_adaptations(characters, category)
                    adapted = True
                    break
            if not adapted:
                adaptation_notes["job"] = "Generic professional adaptation"

        # Apply hobby adaptations
        if hobbies:
            for hobby in hobbies[:2]:  # Limit to 2 hobby adaptations
                hobby_lower = hobby.lower()
                for category, keywords in [
                    ("fitness", ["gym", "fitness", "workout", "running", "yoga"]),
                    ("music", ["music", "concert", "band", "dj"]),
                    ("gaming", ["gaming", "games", "esports"]),
                    ("art", ["art", "painting", "photography"]),
                    ("travel", ["travel", "adventure", "hiking"]),
                ]:
                    if any(kw in hobby_lower for kw in keywords):
                        adaptation_notes[f"hobby_{category}"] = f"{hobby} adaptation"
                        characters = self._apply_hobby_adaptations(characters, category, hobby)
                        break

        # Apply meeting context adaptations
        if meeting_context:
            adaptation_notes["meeting"] = f"Met through: {meeting_context}"
            characters = self._apply_meeting_adaptations(characters, meeting_context)

        logger.info(
            f"Generated social circle for user {user_id}: "
            f"{len(characters)} characters, {len(adaptation_notes)} adaptations"
        )

        return SocialCircle(
            user_id=user_id,
            characters=characters,
            adaptation_notes=adaptation_notes,
        )

    def _copy_character(self, char: FriendCharacter) -> FriendCharacter:
        """Create a copy of a character for adaptation."""
        return FriendCharacter(
            name=char.name,
            role=char.role,
            age=char.age,
            occupation=char.occupation,
            personality=char.personality,
            relationship_to_nikita=char.relationship_to_nikita,
            storyline_potential=list(char.storyline_potential),
            trigger_conditions=list(char.trigger_conditions),
            adapted_traits=dict(char.adapted_traits),
        )

    def _apply_tech_hub_adaptations(
        self,
        characters: list[FriendCharacter],
        location: str,
    ) -> list[FriendCharacter]:
        """Apply tech hub city adaptations."""
        # Add a startup founder friend
        characters.append(
            FriendCharacter(
                name="Marco",
                role="industry_friend",
                age=30,
                occupation="Startup founder, former colleague",
                personality="Hustle culture, always pitching. Stressful but connected. "
                           "Useful for industry gossip.",
                relationship_to_nikita="Met through security consulting. "
                                      "Calls when he needs help, useful contact.",
                storyline_potential=[
                    "Startup crisis needs Nikita's help",
                    "Has party with interesting people",
                    "Offers Nikita a job",
                    "Gets acquired, celebration",
                ],
                trigger_conditions=[
                    "Work discussions",
                    "Startup topics",
                    "Networking events",
                ],
                adapted_traits={"location": location, "type": "tech_hub"},
            )
        )
        return characters

    def _apply_creative_adaptations(
        self,
        characters: list[FriendCharacter],
        location: str,
    ) -> list[FriendCharacter]:
        """Apply creative city adaptations."""
        # Add an artist friend
        characters.append(
            FriendCharacter(
                name="Ava",
                role="creative_friend",
                age=26,
                occupation="Visual artist, struggles financially",
                personality="Dreamlike, creative, sometimes frustratingly impractical. "
                           "Nikita admires her vision, worries about her stability.",
                relationship_to_nikita="Met through Yuki. Art nerd discussions. "
                                      "Nikita sometimes helps her with tech stuff.",
                storyline_potential=[
                    "Gallery opening, invites Nikita",
                    "Financial crisis",
                    "Sellout vs authenticity debate",
                    "Introduces new people",
                ],
                trigger_conditions=[
                    "Creative discussions",
                    "Art topics",
                    "Nikita's chemistry hobby",
                ],
                adapted_traits={"location": location, "type": "creative_city"},
            )
        )
        return characters

    def _apply_job_adaptations(
        self,
        characters: list[FriendCharacter],
        job_category: str,
    ) -> list[FriendCharacter]:
        """Apply job-based adaptations to characters."""
        for char in characters:
            if char.role == "best_friend":
                # Lena might have opinions about the user's job
                char.storyline_potential.append(
                    f"Comments on user's {job_category} work"
                )
            if char.role == "complicated_friend":
                # Viktor might have industry connections
                if job_category == "tech":
                    char.adapted_traits["industry_overlap"] = True
                    char.storyline_potential.append(
                        "Knows someone at user's company"
                    )
        return characters

    def _apply_hobby_adaptations(
        self,
        characters: list[FriendCharacter],
        hobby_category: str,
        hobby_name: str,
    ) -> list[FriendCharacter]:
        """Apply hobby-based adaptations to characters."""
        for char in characters:
            if char.role == "party_friend" and hobby_category == "music":
                char.storyline_potential.append(
                    f"Invites to {hobby_name}-related event"
                )
            if char.role == "best_friend":
                char.adapted_traits[f"hobby_context_{hobby_category}"] = hobby_name
        return characters

    def _apply_meeting_adaptations(
        self,
        characters: list[FriendCharacter],
        meeting_context: str,
    ) -> list[FriendCharacter]:
        """Apply meeting context adaptations."""
        meeting_lower = meeting_context.lower()

        # If they met at a party, Yuki might have been there
        if "party" in meeting_lower or "club" in meeting_lower:
            for char in characters:
                if char.role == "party_friend":
                    char.storyline_potential.append(
                        "Was at the party where you met"
                    )
                    char.adapted_traits["was_at_meeting"] = True

        # If through work/tech, Viktor might know about it
        if "conference" in meeting_lower or "work" in meeting_lower or "tech" in meeting_lower:
            for char in characters:
                if char.role == "complicated_friend":
                    char.storyline_potential.append(
                        "Heard about you from the tech scene"
                    )

        return characters


# Singleton for easy access
_generator: SocialCircleGenerator | None = None


def get_social_generator() -> SocialCircleGenerator:
    """Get the social circle generator singleton."""
    global _generator
    if _generator is None:
        _generator = SocialCircleGenerator()
    return _generator


def generate_social_circle_for_user(
    user_id: UUID,
    location: str | None = None,
    hobbies: list[str] | None = None,
    job_field: str | None = None,
    meeting_context: str | None = None,
) -> SocialCircle:
    """Convenience function to generate a social circle.

    Args:
        user_id: The user's UUID.
        location: User's city/location.
        hobbies: User's hobbies/interests.
        job_field: User's profession field.
        meeting_context: How user met Nikita.

    Returns:
        SocialCircle with adapted characters.
    """
    generator = get_social_generator()
    return generator.generate_social_circle(
        user_id=user_id,
        location=location,
        hobbies=hobbies,
        job_field=job_field,
        meeting_context=meeting_context,
    )
