"""Profile and onboarding models for enhanced user personalization.

This module contains models for the 017-enhanced-onboarding feature:
- UserProfile: User's profile preferences (location, interests, drug tolerance)
- UserBackstory: How Nikita and user "met" (selected or custom backstory)
- VenueCache: Cached venue research results from Firecrawl
- OnboardingState: Transient state for onboarding flow (like PendingRegistration)

Models follow existing patterns from user.py and pending_registration.py.
"""

from datetime import datetime
from datetime import timedelta
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey
from sqlalchemy import Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nikita.db.models.base import Base, TimestampMixin, utc_now

if TYPE_CHECKING:
    from nikita.db.models.user import User


class OnboardingStep(str, Enum):
    """Onboarding flow steps (state machine).

    Profile collection steps (in order):
    1. LOCATION - City/country
    2. LIFE_STAGE - Career phase (student, professional, artist, etc.)
    3. SCENE - Social scene preference (techno, art, dining, etc.)
    4. INTEREST - Primary interest/hobby
    5. DRUG_TOLERANCE - 1-5 scale for content intensity

    Post-profile steps:
    6. VENUE_RESEARCH - System researches venues
    7. SCENARIO_SELECTION - User picks from 3 scenarios or writes custom
    8. COMPLETE - Onboarding finished
    """

    LOCATION = "location"
    LIFE_STAGE = "life_stage"
    SCENE = "scene"
    INTEREST = "interest"
    DRUG_TOLERANCE = "drug_tolerance"
    VENUE_RESEARCH = "venue_research"
    SCENARIO_SELECTION = "scenario_selection"
    COMPLETE = "complete"


class UserProfile(Base, TimestampMixin):
    """User profile for personalization.

    Stores user preferences collected during onboarding to personalize
    Nikita's persona and generate relevant backstory scenarios.

    Table: user_profiles
    Primary Key: id (UUID matching users.id for 1:1 relationship)

    T1.1: Create UserProfile Model
    - AC-T1.1-001: 6 required fields
    - AC-T1.1-002: Inherits from Base, UUID PK referencing users.id
    """

    __tablename__ = "user_profiles"

    # Primary key (same as users.id for 1:1 relationship)
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Location
    location_city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    location_country: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Life stage (tech, artist, finance, student, etc.)
    life_stage: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Social scene (techno, art galleries, fine dining, etc.)
    social_scene: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Primary interest/hobby
    primary_interest: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Drug tolerance 1-5 (affects Nikita's "edge level")
    drug_tolerance: Mapped[int] = mapped_column(
        Integer,
        default=3,  # Middle of scale
        nullable=False,
    )

    # Relationship to User
    user: Mapped["User"] = relationship(
        "User",
        back_populates="profile",
        uselist=False,
    )

    __table_args__ = (
        CheckConstraint(
            "drug_tolerance BETWEEN 1 AND 5",
            name="check_drug_tolerance_range",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"UserProfile(id={self.id}, "
            f"city={self.location_city}, "
            f"drug_tolerance={self.drug_tolerance})"
        )


class UserBackstory(Base, TimestampMixin):
    """User's backstory with Nikita (how they "met").

    Stores the selected or custom backstory that defines Nikita and user's
    shared history. Used in MetaPromptContext to inject backstory into
    Nikita's system prompt.

    Table: user_backstories
    Primary Key: id (auto-generated UUID)
    Unique: user_id (one backstory per user)

    T1.2: Create UserBackstory Model
    - AC-T1.2-001: 7 required fields including JSONB
    - AC-T1.2-002: UNIQUE constraint on user_id (1:1)
    """

    __tablename__ = "user_backstories"

    # Auto-generated UUID
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # Foreign key to users (UNIQUE for 1:1)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,  # AC-T1.2-002: One backstory per user
        nullable=False,
    )

    # Venue where they met
    venue_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    venue_city: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Scenario type (romantic, intellectual, chaotic, custom)
    scenario_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Narrative elements
    how_we_met: Mapped[str | None] = mapped_column(Text, nullable=True)
    the_moment: Mapped[str | None] = mapped_column(Text, nullable=True)
    unresolved_hook: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Persona overrides (JSONB) - adaptive traits based on profile
    # e.g., {"occupation": "hacker", "hobby": "DJ", "vice_intensity": 4}
    nikita_persona_overrides: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
    )

    # Relationship to User
    user: Mapped["User"] = relationship(
        "User",
        back_populates="backstory",
        uselist=False,
    )

    def __repr__(self) -> str:
        return (
            f"UserBackstory(id={self.id}, "
            f"user_id={self.user_id}, "
            f"scenario_type={self.scenario_type})"
        )


class VenueCache(Base):
    """Cached venue research results from Firecrawl.

    Caches venue search results by (city, scene) to reduce Firecrawl
    API calls. Results expire after 30 days.

    Table: venue_cache
    Primary Key: id (auto-generated UUID)
    Unique: (city, scene) composite

    T1.3: Create VenueCache Model
    - AC-T1.3-001: 5 required fields including JSONB
    - AC-T1.3-002: Composite unique on (city, scene)
    """

    __tablename__ = "venue_cache"

    # Auto-generated UUID
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # Cache key: normalized city + scene
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    scene: Mapped[str] = mapped_column(String(50), nullable=False)

    # Cached venues (JSONB array of venue objects)
    # e.g., [{"name": "Berghain", "description": "...", "vibe": "dark techno"}]
    venues: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    # Timestamps for cache management
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now() + timedelta(days=30),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("city", "scene", name="uq_venue_cache_city_scene"),
    )

    def is_expired(self) -> bool:
        """Check if cache entry has expired.

        Returns:
            True if current time is past expires_at.
        """
        return utc_now() > self.expires_at

    def __repr__(self) -> str:
        return (
            f"VenueCache(city={self.city}, "
            f"scene={self.scene}, "
            f"venues_count={len(self.venues)})"
        )


class OnboardingState(Base):
    """Transient onboarding state for profile collection flow.

    Tracks user's progress through the onboarding steps. Similar to
    PendingRegistration - deleted upon completion.

    Table: onboarding_states
    Primary Key: telegram_id (one state per user)

    T1.4: Create OnboardingState Model
    - AC-T1.4-001: 5 required fields including JSONB
    - AC-T1.4-002: Steps enum with 8 values
    - AC-T1.4-003: Transient (delete on completion)
    """

    __tablename__ = "onboarding_states"

    # Telegram ID as primary key (like PendingRegistration)
    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        nullable=False,
    )

    # Current step in onboarding flow
    current_step: Mapped[str] = mapped_column(
        String(30),
        default=OnboardingStep.LOCATION.value,
        nullable=False,
    )

    # Collected answers so far (JSONB)
    # e.g., {"location_city": "Berlin", "life_stage": "tech"}
    collected_answers: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Timestamps
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def get_current_step(self) -> OnboardingStep:
        """Get current step as enum."""
        return OnboardingStep(self.current_step)

    def set_step(self, step: OnboardingStep) -> None:
        """Set current step from enum."""
        self.current_step = step.value

    def is_complete(self) -> bool:
        """Check if onboarding is complete."""
        return self.current_step == OnboardingStep.COMPLETE.value

    def __repr__(self) -> str:
        return (
            f"OnboardingState(telegram_id={self.telegram_id}, "
            f"step={self.current_step}, "
            f"answers={len(self.collected_answers)})"
        )
