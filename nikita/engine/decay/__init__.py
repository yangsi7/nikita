"""Decay system for Nikita game engine (spec 005).

Provides decay calculation and processing for inactive users:
- DecayResult: Result model with audit trail
- DecayCalculator: Calculates decay based on chapter and time overdue
- DecayProcessor: Batch processes all users due for decay
"""

from nikita.engine.decay.calculator import DecayCalculator
from nikita.engine.decay.models import DecayResult
from nikita.engine.decay.processor import DecayProcessor

__all__ = [
    "DecayCalculator",
    "DecayProcessor",
    "DecayResult",
]
