"""Pydantic schemas for YAML configuration validation.

These schemas ensure all config files are valid and type-safe.
"""

from pydantic import BaseModel, Field, model_validator


# ============================================================================
# Game Configuration (game.yaml)
# ============================================================================


class ScoreRange(BaseModel):
    """Score boundaries."""

    min: float = Field(ge=0)
    max: float = Field(le=100)

    @model_validator(mode="after")
    def validate_range(self) -> "ScoreRange":
        if self.min >= self.max:
            raise ValueError("min must be less than max")
        return self


class GameSettings(BaseModel):
    """Core game parameters."""

    starting_score: float = Field(ge=0, le=100, default=50.0)
    score_range: ScoreRange
    max_boss_attempts: int = Field(gt=0, default=3)
    game_duration_days: int = Field(gt=0, default=21)
    default_timezone: str = "UTC"


class SessionSettings(BaseModel):
    """Session configuration."""

    idle_timeout_minutes: int = Field(gt=0, default=30)
    max_session_hours: int = Field(gt=0, default=8)


class GameConfig(BaseModel):
    """Root config for game.yaml."""

    game: GameSettings
    session: SessionSettings


# ============================================================================
# Chapters Configuration (chapters.yaml)
# ============================================================================


class DayRange(BaseModel):
    """Day range for a chapter."""

    start: int = Field(ge=1)
    end: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_range(self) -> "DayRange":
        if self.start > self.end:
            raise ValueError("start must be <= end")
        return self


class ChapterDefinition(BaseModel):
    """Single chapter definition."""

    name: str
    day_range: DayRange
    boss_threshold: float = Field(ge=0, le=100)
    description: str = ""


class BossDefinition(BaseModel):
    """Boss encounter definition."""

    name: str
    trigger: str
    challenge: str


class ChaptersConfig(BaseModel):
    """Root config for chapters.yaml."""

    chapters: dict[int, ChapterDefinition]
    bosses: dict[int, BossDefinition]

    @model_validator(mode="after")
    def validate_chapters(self) -> "ChaptersConfig":
        # Validate exactly 5 chapters
        if len(self.chapters) != 5:
            raise ValueError(f"Expected 5 chapters, got {len(self.chapters)}")

        # Validate chapters 1-5 exist
        for i in range(1, 6):
            if i not in self.chapters:
                raise ValueError(f"Missing chapter {i}")

        # Validate boss thresholds are monotonically increasing
        thresholds = [self.chapters[i].boss_threshold for i in range(1, 6)]
        for i in range(1, len(thresholds)):
            if thresholds[i] <= thresholds[i - 1]:
                raise ValueError(
                    f"Boss thresholds must increase: chapter {i} ({thresholds[i-1]}) >= chapter {i+1} ({thresholds[i]})"
                )

        # Validate day ranges don't overlap
        ranges = [
            (self.chapters[i].day_range.start, self.chapters[i].day_range.end)
            for i in range(1, 6)
        ]
        for i in range(1, len(ranges)):
            if ranges[i][0] <= ranges[i - 1][1]:
                raise ValueError(f"Day ranges overlap: chapter {i} and {i+1}")

        return self


# ============================================================================
# Scoring Configuration (scoring.yaml)
# ============================================================================


class MetricWeights(BaseModel):
    """Weights for composite score calculation."""

    intimacy: float = Field(ge=0, le=1)
    passion: float = Field(ge=0, le=1)
    trust: float = Field(ge=0, le=1)
    secureness: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_weights_sum(self) -> "MetricWeights":
        total = self.intimacy + self.passion + self.trust + self.secureness
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"Metric weights must sum to 1.0, got {total}")
        return self


class MetricStartingValues(BaseModel):
    """Starting values for metrics."""

    intimacy: float = Field(ge=0, le=100, default=50.0)
    passion: float = Field(ge=0, le=100, default=50.0)
    trust: float = Field(ge=0, le=100, default=50.0)
    secureness: float = Field(ge=0, le=100, default=50.0)


class DeltaRange(BaseModel):
    """Score change boundaries."""

    min: float
    max: float


class MetricsSettings(BaseModel):
    """Metrics configuration."""

    weights: MetricWeights
    starting_values: MetricStartingValues
    delta_range: DeltaRange


class QualityModifier(BaseModel):
    """Score modifier for response quality."""

    min_delta: float
    max_delta: float


class EngagementMultipliers(BaseModel):
    """Score multipliers by engagement state."""

    IN_ZONE: float = Field(ge=0, le=2, default=1.0)
    CALIBRATING: float = Field(ge=0, le=2, default=0.8)
    DRIFTING_COLD: float = Field(ge=0, le=2, default=0.7)
    DRIFTING_HOT: float = Field(ge=0, le=2, default=0.7)
    RECOVERY: float = Field(ge=0, le=2, default=0.5)
    CRITICAL: float = Field(ge=0, le=2, default=0.3)


class ScoringConfig(BaseModel):
    """Root config for scoring.yaml."""

    metrics: MetricsSettings
    quality_modifiers: dict[str, QualityModifier]
    engagement_multipliers: EngagementMultipliers


# ============================================================================
# Decay Configuration (decay.yaml)
# ============================================================================


class DecaySchedule(BaseModel):
    """Decay check schedule settings."""

    check_interval_minutes: int = Field(gt=0, default=60)
    min_decay_interval_minutes: int = Field(gt=0, default=60)


class DecayConfig(BaseModel):
    """Root config for decay.yaml."""

    grace_periods: dict[int, int]  # chapter -> hours
    decay_rates: dict[int, float]  # chapter -> %/hour
    daily_caps: dict[int, float]  # chapter -> max daily decay
    schedule: DecaySchedule

    @model_validator(mode="after")
    def validate_chapters(self) -> "DecayConfig":
        # Validate all 5 chapters have values
        for i in range(1, 6):
            if i not in self.grace_periods:
                raise ValueError(f"Missing grace_period for chapter {i}")
            if i not in self.decay_rates:
                raise ValueError(f"Missing decay_rate for chapter {i}")
            if i not in self.daily_caps:
                raise ValueError(f"Missing daily_cap for chapter {i}")

        return self


# ============================================================================
# Engagement Configuration (engagement.yaml)
# ============================================================================


class EngagementStateDefinition(BaseModel):
    """Single engagement state definition."""

    description: str
    score_multiplier: float = Field(ge=0, le=2)
    recovery_rate: float = Field(ge=0, le=1)
    is_healthy: bool


class CalibrationTolerance(BaseModel):
    """Tolerance bands for engagement calibration."""

    tight: float = Field(ge=0, le=1)
    normal: float = Field(ge=0, le=1)
    loose: float = Field(ge=0, le=1)


class CalibrationSettings(BaseModel):
    """Calibration configuration."""

    required_interactions: int = Field(gt=0)
    tolerance: CalibrationTolerance


class TransitionRules(BaseModel):
    """Rules for state transitions."""

    cold_threshold: int = Field(gt=0)
    hot_threshold: int = Field(gt=0)
    recovery_threshold: int = Field(gt=0)
    critical_threshold_hours: int = Field(gt=0)


class EngagementConfig(BaseModel):
    """Root config for engagement.yaml."""

    states: dict[str, EngagementStateDefinition]
    calibration: CalibrationSettings
    transitions: TransitionRules
    ideal_messages_per_day: dict[int, int]

    @model_validator(mode="after")
    def validate_states(self) -> "EngagementConfig":
        required_states = {
            "CALIBRATING",
            "IN_ZONE",
            "DRIFTING_COLD",
            "DRIFTING_HOT",
            "RECOVERY",
            "CRITICAL",
        }
        if set(self.states.keys()) != required_states:
            raise ValueError(
                f"Expected states {required_states}, got {set(self.states.keys())}"
            )
        return self


# ============================================================================
# Vice Configuration (vices.yaml)
# ============================================================================


class ViceCategoryDefinition(BaseModel):
    """Single vice category definition."""

    name: str
    description: str
    prompt_modifier: str
    detection_signals: list[str]


class ViceIntensityLevel(BaseModel):
    """Intensity level definition."""

    multiplier: float = Field(ge=0, le=3)
    description: str


class ViceDiscoverySettings(BaseModel):
    """Vice discovery configuration."""

    min_interactions: int = Field(gt=0)
    confidence_threshold: float = Field(ge=0, le=1)
    max_tracked_vices: int = Field(gt=0)


class VicesConfig(BaseModel):
    """Root config for vices.yaml."""

    categories: dict[str, ViceCategoryDefinition]
    intensity_levels: dict[str, ViceIntensityLevel]
    discovery: ViceDiscoverySettings

    @model_validator(mode="after")
    def validate_categories(self) -> "VicesConfig":
        # Validate 8 vice categories
        if len(self.categories) != 8:
            raise ValueError(f"Expected 8 vice categories, got {len(self.categories)}")

        # Validate intensity levels
        required_levels = {"low", "medium", "high"}
        if set(self.intensity_levels.keys()) != required_levels:
            raise ValueError(f"Expected intensity levels {required_levels}")

        return self


# ============================================================================
# Schedule Configuration (schedule.yaml)
# ============================================================================


class AvailabilityWindow(BaseModel):
    """Single availability window."""

    start: str  # HH:MM format
    end: str  # HH:MM format
    response_rate: float = Field(ge=0, le=1)
    avg_response_delay_minutes: int = Field(ge=0)


class ChapterResponseTiming(BaseModel):
    """Response timing for a chapter."""

    min_delay_minutes: int = Field(ge=0)
    max_delay_minutes: int = Field(gt=0)
    initiation_rate: float = Field(ge=0, le=1)


class CronSchedules(BaseModel):
    """pg_cron schedule definitions."""

    decay_check: str
    summary_generation: str
    cleanup: str


class ScheduleConfig(BaseModel):
    """Root config for schedule.yaml."""

    availability_windows: dict[str, AvailabilityWindow]
    chapter_response_timing: dict[int, ChapterResponseTiming]
    cron_schedules: CronSchedules
