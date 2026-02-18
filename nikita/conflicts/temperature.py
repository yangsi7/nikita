"""Temperature engine for conflict system (Spec 057).

Pure computation class for temperature gauge operations.
No database access — all state passed in and returned.

Temperature Zones:
- CALM (0-25): No conflicts generated
- WARM (25-50): 10-25% injection, severity capped at 0.4
- HOT (50-75): 25-60% injection, severity capped at 0.7
- CRITICAL (75-100): 60-90% injection, full severity
"""

from datetime import UTC, datetime

from nikita.conflicts.models import (
    ConflictDetails,
    ConflictTemperature,
    HorsemanType,
    TemperatureZone,
    TriggerType,
)


class TemperatureEngine:
    """Pure computation engine for temperature gauge (Spec 057).

    All methods are stateless — state is passed in and returned.
    No database access.
    """

    # Zone boundaries (upper bound exclusive)
    ZONE_BOUNDARIES: dict[TemperatureZone, tuple[float, float]] = {
        TemperatureZone.CALM: (0.0, 25.0),
        TemperatureZone.WARM: (25.0, 50.0),
        TemperatureZone.HOT: (50.0, 75.0),
        TemperatureZone.CRITICAL: (75.0, 100.0),
    }

    # Injection probability range per zone (min, max)
    INJECTION_PROBABILITIES: dict[TemperatureZone, tuple[float, float]] = {
        TemperatureZone.CALM: (0.0, 0.0),
        TemperatureZone.WARM: (0.10, 0.25),
        TemperatureZone.HOT: (0.25, 0.60),
        TemperatureZone.CRITICAL: (0.60, 0.90),
    }

    # Max severity per zone
    MAX_SEVERITY: dict[TemperatureZone, float] = {
        TemperatureZone.CALM: 0.0,
        TemperatureZone.WARM: 0.4,
        TemperatureZone.HOT: 0.7,
        TemperatureZone.CRITICAL: 1.0,
    }

    # Horseman type to temperature delta
    HORSEMAN_DELTAS: dict[HorsemanType, float] = {
        HorsemanType.CRITICISM: 4.0,
        HorsemanType.CONTEMPT: 8.0,
        HorsemanType.DEFENSIVENESS: 3.0,
        HorsemanType.STONEWALLING: 5.0,
    }

    # Trigger type to temperature delta
    TRIGGER_DELTAS: dict[TriggerType, float] = {
        TriggerType.DISMISSIVE: 3.0,
        TriggerType.NEGLECT: 5.0,
        TriggerType.JEALOUSY: 4.0,
        TriggerType.BOUNDARY: 8.0,
        TriggerType.TRUST: 6.0,
    }

    # Passive decay rate (per hour)
    TIME_DECAY_RATE: float = 0.5

    # Score drop threshold for bonus temperature increase
    SCORE_DROP_THRESHOLD: float = 3.0
    SCORE_DROP_TEMP_DELTA: float = 5.0

    @classmethod
    def increase(cls, current: float, delta: float) -> float:
        """Increase temperature, clamped to 0-100.

        Args:
            current: Current temperature.
            delta: Amount to increase (positive).

        Returns:
            New temperature value.
        """
        return max(0.0, min(100.0, current + abs(delta)))

    @classmethod
    def decrease(cls, current: float, delta: float) -> float:
        """Decrease temperature, clamped to 0-100.

        Args:
            current: Current temperature.
            delta: Amount to decrease (positive).

        Returns:
            New temperature value.
        """
        return max(0.0, min(100.0, current - abs(delta)))

    @classmethod
    def apply_time_decay(
        cls,
        current: float,
        hours_elapsed: float,
        rate: float | None = None,
    ) -> float:
        """Apply passive time-based decay.

        Args:
            current: Current temperature.
            hours_elapsed: Hours since last update.
            rate: Decay rate per hour (default 0.5).

        Returns:
            New temperature after decay.
        """
        decay_rate = max(0.0, rate if rate is not None else cls.TIME_DECAY_RATE)
        decay_amount = max(0.0, hours_elapsed) * decay_rate
        return max(0.0, current - decay_amount)

    @classmethod
    def get_zone(cls, temperature: float) -> TemperatureZone:
        """Get the temperature zone for a value.

        Args:
            temperature: Temperature value (0-100).

        Returns:
            TemperatureZone enum value.
        """
        if temperature < 25.0:
            return TemperatureZone.CALM
        elif temperature < 50.0:
            return TemperatureZone.WARM
        elif temperature < 75.0:
            return TemperatureZone.HOT
        else:
            return TemperatureZone.CRITICAL

    @classmethod
    def get_injection_probability(cls, zone: TemperatureZone) -> tuple[float, float]:
        """Get injection probability range for a zone.

        Args:
            zone: Temperature zone.

        Returns:
            Tuple of (min_probability, max_probability).
        """
        return cls.INJECTION_PROBABILITIES.get(zone, (0.0, 0.0))

    @classmethod
    def get_max_severity(cls, zone: TemperatureZone) -> float:
        """Get maximum conflict severity for a zone.

        Args:
            zone: Temperature zone.

        Returns:
            Maximum severity (0.0-1.0).
        """
        return cls.MAX_SEVERITY.get(zone, 0.0)

    @classmethod
    def calculate_delta_from_score(cls, score_delta: float) -> float:
        """Calculate temperature delta from a scoring change.

        Negative score changes increase temperature.
        Positive score changes decrease temperature (at slower rate).

        Args:
            score_delta: Score change (can be negative or positive).

        Returns:
            Temperature delta (positive = increase, negative = decrease).
        """
        if score_delta < 0:
            # Negative interaction: proportional increase
            temp_delta = abs(score_delta) * 1.5
            # Bonus for large drops
            if abs(score_delta) > cls.SCORE_DROP_THRESHOLD:
                temp_delta += cls.SCORE_DROP_TEMP_DELTA
            return temp_delta
        elif score_delta > 0:
            # Positive interaction: slower decrease
            return -(abs(score_delta) * 0.5)
        return 0.0

    @classmethod
    def calculate_delta_from_horseman(cls, horseman: HorsemanType) -> float:
        """Calculate temperature delta from a detected horseman.

        Args:
            horseman: Detected horseman type.

        Returns:
            Temperature increase.
        """
        return cls.HORSEMAN_DELTAS.get(horseman, 4.0)

    @classmethod
    def calculate_delta_from_trigger(cls, trigger_type: TriggerType) -> float:
        """Calculate temperature delta from a trigger type.

        Args:
            trigger_type: Type of trigger detected.

        Returns:
            Temperature increase.
        """
        return cls.TRIGGER_DELTAS.get(trigger_type, 3.0)

    @classmethod
    def interpolate_probability(cls, temperature: float) -> float:
        """Get interpolated injection probability for exact temperature.

        Linear interpolation within zone bounds.

        Args:
            temperature: Temperature value (0-100).

        Returns:
            Injection probability (0.0-1.0).
        """
        zone = cls.get_zone(temperature)
        prob_min, prob_max = cls.INJECTION_PROBABILITIES[zone]
        zone_min, zone_max = cls.ZONE_BOUNDARIES[zone]

        if prob_min == prob_max:
            return prob_min

        # Linear interpolation within zone, clamped to [0, 1]
        zone_progress = max(0.0, min(1.0, (temperature - zone_min) / (zone_max - zone_min)))
        return prob_min + (prob_max - prob_min) * zone_progress

    @classmethod
    def update_conflict_details(
        cls,
        details: ConflictDetails,
        temp_delta: float,
        now: datetime | None = None,
    ) -> ConflictDetails:
        """Apply a temperature delta to conflict details.

        Args:
            details: Current conflict details.
            temp_delta: Temperature change (positive = increase).
            now: Current timestamp.

        Returns:
            Updated ConflictDetails.
        """
        now = now or datetime.now(UTC)
        new_temp = max(0.0, min(100.0, details.temperature + temp_delta))
        new_zone = cls.get_zone(new_temp)

        return ConflictDetails(
            temperature=new_temp,
            zone=new_zone.value,
            positive_count=details.positive_count,
            negative_count=details.negative_count,
            gottman_ratio=details.gottman_ratio,
            gottman_target=details.gottman_target,
            horsemen_detected=details.horsemen_detected,
            repair_attempts=details.repair_attempts,
            last_temp_update=now.isoformat(),
            session_positive=details.session_positive,
            session_negative=details.session_negative,
        )
