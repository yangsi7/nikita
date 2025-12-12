"""
Vice System Pydantic Models (T005-T007)

Data models for vice detection, analysis, and profile management.
"""

from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from nikita.config.enums import ViceCategory


class ViceSignal(BaseModel):
    """T005: Single vice detection signal.

    Represents a detected vice signal from a conversation exchange,
    including confidence level and evidence.
    """

    # AC-T005.1: category field from VICE_CATEGORIES enum
    category: ViceCategory

    # AC-T005.2: confidence field (Decimal 0.0-1.0)
    confidence: Annotated[
        Decimal,
        Field(ge=Decimal("0.0"), le=Decimal("1.0")),
    ]

    # AC-T005.3: evidence field for detection reasoning
    evidence: str = Field(min_length=1)

    # AC-T005.4: is_positive field (True=engagement, False=rejection)
    is_positive: bool

    @field_validator("confidence", mode="before")
    @classmethod
    def validate_confidence(cls, v):
        """Ensure confidence is a Decimal."""
        if isinstance(v, float):
            return Decimal(str(v))
        if isinstance(v, str):
            return Decimal(v)
        return v

    model_config = {"frozen": True}


class ViceAnalysisResult(BaseModel):
    """T006: Result of analyzing a conversation for vice signals.

    Contains all detected signals from a single conversation exchange.
    """

    # AC-T006.1: signals list of ViceSignal
    signals: list[ViceSignal] = Field(default_factory=list)

    # AC-T006.2: conversation_id for traceability
    conversation_id: UUID

    # AC-T006.3: analyzed_at timestamp
    analyzed_at: datetime

    @property
    def detected_count(self) -> int:
        """Number of positive signals detected."""
        return sum(1 for s in self.signals if s.is_positive)

    @property
    def rejection_count(self) -> int:
        """Number of rejection signals detected."""
        return sum(1 for s in self.signals if not s.is_positive)

    @property
    def has_signals(self) -> bool:
        """Whether any signals were detected."""
        return len(self.signals) > 0


class ViceProfile(BaseModel):
    """T007: User's vice profile with intensities.

    Aggregates all vice preference data for a user, enabling
    personalized prompt injection.
    """

    # AC-T007.1: user_id UUID field
    user_id: UUID

    # AC-T007.2: intensities dict[str, Decimal] for all 8 categories
    intensities: dict[str, Decimal] = Field(default_factory=dict)

    # AC-T007.3: top_vices ordered list
    top_vices: list[str] = Field(default_factory=list)

    # AC-T007.4: updated_at timestamp
    updated_at: datetime

    def get_intensity(self, category: str) -> Decimal:
        """Get intensity for a category, defaulting to 0.0.

        Args:
            category: Vice category name (e.g., 'dark_humor')

        Returns:
            Intensity value or Decimal('0.0') if not found
        """
        return self.intensities.get(category, Decimal("0.0"))

    def has_active_vices(self, threshold: Decimal = Decimal("0.30")) -> bool:
        """Check if user has any vices above threshold.

        Args:
            threshold: Minimum intensity to consider active

        Returns:
            True if any vice intensity >= threshold
        """
        return any(v >= threshold for v in self.intensities.values())

    def get_top_n(self, n: int = 3) -> list[tuple[str, Decimal]]:
        """Get top N vices by intensity.

        Args:
            n: Number of top vices to return

        Returns:
            List of (category, intensity) tuples, sorted descending
        """
        sorted_vices = sorted(
            self.intensities.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        return sorted_vices[:n]


# Injection context for prompt generation
class ViceInjectionContext(BaseModel):
    """Context for injecting vice preferences into prompts."""

    # Top vices to emphasize (max 3)
    active_vices: list[tuple[str, Decimal]] = Field(default_factory=list)

    # Chapter-appropriate expression level
    expression_level: str = Field(default="subtle")  # subtle, moderate, explicit

    # Discovery mode (probe for unknown vices)
    discovery_mode: bool = Field(default=False)

    # Categories to probe if in discovery mode
    probe_categories: list[str] = Field(default_factory=list)

    def has_vices(self) -> bool:
        """Check if there are active vices to inject."""
        return len(self.active_vices) > 0

    @property
    def primary_vice(self) -> str | None:
        """Get the primary (highest) vice category."""
        if self.active_vices:
            return self.active_vices[0][0]
        return None
