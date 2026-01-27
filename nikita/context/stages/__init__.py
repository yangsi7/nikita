"""Pipeline stages module for post-processing.

This module provides the unified stage infrastructure for the conversation
post-processing pipeline. Each stage extends PipelineStage and implements
consistent timeout, retry, logging, and tracing behavior.

Stages:
    - IngestionStage: Load conversation from DB
    - ExtractionStage: LLM entity extraction
    - PsychologyStage: Update psychological profile
    - NarrativeArcsStage: Generate/update narrative arcs
    - ThreadsStage: Thread resolution
    - ThoughtsStage: Thought simulation
    - GraphUpdatesStage: Neo4j knowledge graph updates
    - SummaryRollupsStage: Daily/weekly summaries
    - ViceProcessingStage: Vice signal detection
    - VoiceCacheStage: Voice cache refresh
    - FinalizationStage: Mark conversation processed
"""

from nikita.context.stages.base import PipelineStage, StageResult, StageError
from nikita.context.stages.circuit_breaker import CircuitBreaker, CircuitState, CircuitOpenError
from nikita.context.stages.extraction import ExtractionStage, ExtractionResult
from nikita.context.stages.graph_updates import GraphUpdatesStage
from nikita.context.stages.ingestion import IngestionStage
from nikita.context.stages.narrative_arcs import NarrativeArcsStage, NarrativeArcsInput, NarrativeArcsResult
from nikita.context.stages.psychology import PsychologyStage, PsychologyInput, PsychologyResult
from nikita.context.stages.summary_rollups import SummaryRollupsStage, SummaryRollupsInput
from nikita.context.stages.threads import ThreadsStage, ThreadsInput
from nikita.context.stages.thoughts import ThoughtsStage, ThoughtsInput
from nikita.context.stages.vice_processing import ViceProcessingStage
from nikita.context.stages.voice_cache import VoiceCacheStage
from nikita.context.stages.finalization import (
    FinalizationInput,
    FinalizationResult,
    FinalizationStage,
)

__all__ = [
    # Base classes
    "PipelineStage",
    "StageResult",
    "StageError",
    # Circuit breaker
    "CircuitBreaker",
    "CircuitState",
    "CircuitOpenError",
    # Stages
    "IngestionStage",
    "ExtractionStage",
    "ExtractionResult",
    "GraphUpdatesStage",
    "NarrativeArcsStage",
    "NarrativeArcsInput",
    "NarrativeArcsResult",
    "PsychologyStage",
    "PsychologyInput",
    "PsychologyResult",
    "SummaryRollupsStage",
    "SummaryRollupsInput",
    "ThreadsStage",
    "ThreadsInput",
    "ThoughtsStage",
    "ThoughtsInput",
    "ViceProcessingStage",
    "VoiceCacheStage",
    "FinalizationStage",
    "FinalizationInput",
    "FinalizationResult",
]
