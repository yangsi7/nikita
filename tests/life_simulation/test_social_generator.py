"""Tests for Social Circle Generator (Spec 035).

TDD tests for the social circle generation system.

Covers:
- T2.1: Core character generation
- T2.1: Location-based adaptation
- T2.1: Job-based adaptation
- T2.1: Hobby-based adaptation
- T2.1: Meeting context adaptation
"""

from uuid import uuid4

import pytest

from nikita.life_simulation.social_generator import (
    FriendCharacter,
    SocialCircle,
    SocialCircleGenerator,
    generate_social_circle_for_user,
    get_social_generator,
)


class TestFriendCharacter:
    """Tests for FriendCharacter dataclass."""

    def test_friend_character_creation(self):
        """Test creating a friend character with required fields."""
        friend = FriendCharacter(
            name="Test",
            role="test_role",
            age=25,
            occupation="Tester",
            personality="Friendly",
            relationship_to_nikita="Test friend",
        )

        assert friend.name == "Test"
        assert friend.role == "test_role"
        assert friend.age == 25
        assert friend.storyline_potential == []
        assert friend.trigger_conditions == []
        assert friend.adapted_traits == {}

    def test_friend_character_to_dict(self):
        """Test converting friend character to dictionary."""
        friend = FriendCharacter(
            name="Test",
            role="best_friend",
            age=28,
            occupation="Designer",
            personality="Creative",
            relationship_to_nikita="Best friend",
            storyline_potential=["Drama arc"],
            trigger_conditions=["Weekend"],
        )

        result = friend.to_dict()

        assert result["name"] == "Test"
        assert result["role"] == "best_friend"
        assert result["storyline_potential"] == ["Drama arc"]
        assert isinstance(result, dict)

    def test_friend_character_with_adapted_traits(self):
        """Test friend character with adaptation traits."""
        friend = FriendCharacter(
            name="Marco",
            role="industry_friend",
            age=30,
            occupation="Startup founder",
            personality="Ambitious",
            relationship_to_nikita="Industry connection",
            adapted_traits={"location": "berlin", "type": "tech_hub"},
        )

        assert friend.adapted_traits["location"] == "berlin"
        assert friend.adapted_traits["type"] == "tech_hub"


class TestSocialCircle:
    """Tests for SocialCircle dataclass."""

    def test_social_circle_creation(self):
        """Test creating an empty social circle."""
        user_id = uuid4()
        circle = SocialCircle(user_id=user_id)

        assert circle.user_id == user_id
        assert circle.characters == []
        assert circle.adaptation_notes == {}

    def test_get_character_by_role(self):
        """Test retrieving character by role."""
        user_id = uuid4()
        lena = FriendCharacter(
            name="Lena",
            role="best_friend",
            age=28,
            occupation="UX Designer",
            personality="Honest",
            relationship_to_nikita="Best friend",
        )
        circle = SocialCircle(user_id=user_id, characters=[lena])

        result = circle.get_character_by_role("best_friend")

        assert result is not None
        assert result.name == "Lena"

    def test_get_character_by_role_not_found(self):
        """Test retrieving non-existent role."""
        user_id = uuid4()
        circle = SocialCircle(user_id=user_id, characters=[])

        result = circle.get_character_by_role("nonexistent")

        assert result is None

    def test_get_character_by_name(self):
        """Test retrieving character by name (case-insensitive)."""
        user_id = uuid4()
        viktor = FriendCharacter(
            name="Viktor",
            role="complicated_friend",
            age=31,
            occupation="Hacker",
            personality="Charismatic",
            relationship_to_nikita="Old friend",
        )
        circle = SocialCircle(user_id=user_id, characters=[viktor])

        result = circle.get_character_by_name("VIKTOR")

        assert result is not None
        assert result.name == "Viktor"

    def test_get_active_friends_context_empty(self):
        """Test context string for empty circle."""
        user_id = uuid4()
        circle = SocialCircle(user_id=user_id)

        result = circle.get_active_friends_context()

        assert result == "No specific friends relevant"

    def test_get_active_friends_context_with_friends(self):
        """Test context string with friends."""
        user_id = uuid4()
        friends = [
            FriendCharacter(
                name="Lena",
                role="best_friend",
                age=28,
                occupation="Designer",
                personality="Brutally honest and protective",
                relationship_to_nikita="Best friend",
            ),
            FriendCharacter(
                name="Viktor",
                role="complicated_friend",
                age=31,
                occupation="Hacker",
                personality="Brilliant but unstable",
                relationship_to_nikita="Old friend",
            ),
        ]
        circle = SocialCircle(user_id=user_id, characters=friends)

        result = circle.get_active_friends_context()

        assert "Lena (best_friend)" in result
        assert "Viktor (complicated_friend)" in result

    def test_social_circle_to_dict(self):
        """Test converting social circle to dictionary."""
        user_id = uuid4()
        circle = SocialCircle(
            user_id=user_id,
            adaptation_notes={"location": "Berlin adaptation"},
        )

        result = circle.to_dict()

        assert result["user_id"] == str(user_id)
        assert result["characters"] == []
        assert result["adaptation_notes"]["location"] == "Berlin adaptation"


class TestSocialCircleGenerator:
    """Tests for SocialCircleGenerator class."""

    def test_generator_singleton(self):
        """Test that generator singleton works."""
        gen1 = get_social_generator()
        gen2 = get_social_generator()

        assert gen1 is gen2

    def test_generate_social_circle_basic(self):
        """Test generating basic social circle without adaptations."""
        generator = SocialCircleGenerator()
        user_id = uuid4()

        circle = generator.generate_social_circle(user_id)

        # Should have at least core characters
        assert len(circle.characters) >= 6
        assert circle.user_id == user_id

    def test_generate_includes_core_characters(self):
        """Test that core characters are included."""
        generator = SocialCircleGenerator()
        user_id = uuid4()

        circle = generator.generate_social_circle(user_id)

        # Check for core character roles
        roles = [c.role for c in circle.characters]
        assert "best_friend" in roles  # Lena
        assert "complicated_friend" in roles  # Viktor
        assert "party_friend" in roles  # Yuki
        assert "therapist" in roles  # Dr. Miriam
        assert "father" in roles  # Alexei
        assert "mother" in roles  # Katya

    def test_generate_with_tech_hub_location(self):
        """Test adaptation for tech hub cities."""
        generator = SocialCircleGenerator()
        user_id = uuid4()

        circle = generator.generate_social_circle(
            user_id, location="Berlin, Germany"
        )

        # Should add tech hub adaptation
        assert "location" in circle.adaptation_notes
        assert "Tech hub" in circle.adaptation_notes["location"]

        # Should add industry friend (Marco)
        roles = [c.role for c in circle.characters]
        assert "industry_friend" in roles

    def test_generate_with_creative_city_location(self):
        """Test adaptation for creative cities."""
        generator = SocialCircleGenerator()
        user_id = uuid4()

        circle = generator.generate_social_circle(
            user_id, location="Los Angeles, CA"
        )

        # Should add creative city adaptation
        assert "location" in circle.adaptation_notes
        assert "Creative" in circle.adaptation_notes["location"]

        # Should add creative friend (Ava)
        roles = [c.role for c in circle.characters]
        assert "creative_friend" in roles

    def test_generate_with_job_tech(self):
        """Test adaptation for tech job field."""
        generator = SocialCircleGenerator()
        user_id = uuid4()

        circle = generator.generate_social_circle(
            user_id, job_field="Software Engineer"
        )

        # Should add job adaptation
        assert "job" in circle.adaptation_notes
        assert "tech" in circle.adaptation_notes["job"]

    def test_generate_with_job_finance(self):
        """Test adaptation for finance job field."""
        generator = SocialCircleGenerator()
        user_id = uuid4()

        circle = generator.generate_social_circle(
            user_id, job_field="Investment Banking"
        )

        assert "job" in circle.adaptation_notes
        assert "finance" in circle.adaptation_notes["job"]

    def test_generate_with_hobbies(self):
        """Test adaptation for hobbies."""
        generator = SocialCircleGenerator()
        user_id = uuid4()

        circle = generator.generate_social_circle(
            user_id, hobbies=["music", "gaming"]
        )

        # Should add hobby adaptations (max 2)
        hobby_keys = [k for k in circle.adaptation_notes.keys() if k.startswith("hobby_")]
        assert len(hobby_keys) <= 2

    def test_generate_with_meeting_context_party(self):
        """Test adaptation for party meeting context."""
        generator = SocialCircleGenerator()
        user_id = uuid4()

        circle = generator.generate_social_circle(
            user_id, meeting_context="Met at a club party"
        )

        assert "meeting" in circle.adaptation_notes
        assert "Met through" in circle.adaptation_notes["meeting"]

        # Yuki should have adaptation
        yuki = circle.get_character_by_name("Yuki")
        assert yuki is not None
        assert yuki.adapted_traits.get("was_at_meeting") is True

    def test_generate_with_meeting_context_tech_conference(self):
        """Test adaptation for tech conference meeting context."""
        generator = SocialCircleGenerator()
        user_id = uuid4()

        circle = generator.generate_social_circle(
            user_id, meeting_context="Met at a tech conference"
        )

        # Viktor should have adaptation
        viktor = circle.get_character_by_name("Viktor")
        assert viktor is not None
        assert "Heard about you" in str(viktor.storyline_potential)

    def test_generate_with_multiple_adaptations(self):
        """Test generating with all adaptation types."""
        generator = SocialCircleGenerator()
        user_id = uuid4()

        circle = generator.generate_social_circle(
            user_id,
            location="San Francisco",
            job_field="Tech startup founder",
            hobbies=["fitness", "music"],
            meeting_context="Met at a tech party",
        )

        # Should have multiple adaptation notes
        assert len(circle.adaptation_notes) >= 3
        assert "location" in circle.adaptation_notes
        assert "job" in circle.adaptation_notes
        assert "meeting" in circle.adaptation_notes


class TestGenerateSocialCircleForUser:
    """Tests for convenience function."""

    def test_convenience_function_works(self):
        """Test that convenience function generates circle."""
        user_id = uuid4()

        circle = generate_social_circle_for_user(user_id)

        assert circle is not None
        assert circle.user_id == user_id
        assert len(circle.characters) >= 6

    def test_convenience_function_with_params(self):
        """Test convenience function with all parameters."""
        user_id = uuid4()

        circle = generate_social_circle_for_user(
            user_id=user_id,
            location="NYC",
            hobbies=["reading"],
            job_field="Writer",
            meeting_context="Online",
        )

        assert circle.user_id == user_id
        assert len(circle.adaptation_notes) > 0


class TestCharacterCopying:
    """Tests for character copying to ensure isolation."""

    def test_characters_are_copied_not_shared(self):
        """Test that generated characters are independent copies."""
        generator = SocialCircleGenerator()

        circle1 = generator.generate_social_circle(uuid4(), job_field="Tech")
        circle2 = generator.generate_social_circle(uuid4(), job_field="Finance")

        # Modify circle1's character
        lena1 = circle1.get_character_by_name("Lena")
        lena1.storyline_potential.append("Test modification")

        # circle2's Lena should not be affected
        lena2 = circle2.get_character_by_name("Lena")
        assert "Test modification" not in lena2.storyline_potential

    def test_adaptation_traits_are_independent(self):
        """Test that adapted traits are independent per circle."""
        generator = SocialCircleGenerator()

        circle1 = generator.generate_social_circle(uuid4(), location="Berlin")
        circle2 = generator.generate_social_circle(uuid4(), location="Los Angeles")

        # Both should have different characters added
        roles1 = [c.role for c in circle1.characters]
        roles2 = [c.role for c in circle2.characters]

        assert "industry_friend" in roles1  # Berlin tech hub
        assert "creative_friend" in roles2  # LA creative city
