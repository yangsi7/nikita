"""Event type constants for pipeline observability (Spec 110).

All event types emitted from the orchestrator by snapshotting PipelineContext
before/after each stage. Zero stage code changes.
"""

# Pipeline stage completion events (12 types)
EXTRACTION_COMPLETE = "extraction.complete"
MEMORY_UPDATE_COMPLETE = "memory_update.complete"
PERSISTENCE_COMPLETE = "persistence.complete"
LIFE_SIMULATION_COMPLETE = "life_simulation.complete"
EMOTIONAL_STATE_COMPLETE = "emotional_state.complete"
VICE_COMPLETE = "vice.complete"  # Spec 114 GE-006
GAME_STATE_COMPLETE = "game_state.complete"
CONFLICT_COMPLETE = "conflict.complete"
TOUCHPOINT_COMPLETE = "touchpoint.complete"
SUMMARY_COMPLETE = "summary.complete"
PROMPT_BUILDER_COMPLETE = "prompt_builder.complete"
PIPELINE_COMPLETE = "pipeline.complete"

# Stage name → event type mapping
STAGE_EVENT_TYPES: dict[str, str] = {
    "extraction": EXTRACTION_COMPLETE,
    "memory_update": MEMORY_UPDATE_COMPLETE,
    "persistence": PERSISTENCE_COMPLETE,
    "life_sim": LIFE_SIMULATION_COMPLETE,
    "emotional": EMOTIONAL_STATE_COMPLETE,
    "vice": VICE_COMPLETE,
    "game_state": GAME_STATE_COMPLETE,
    "conflict": CONFLICT_COMPLETE,
    "touchpoint": TOUCHPOINT_COMPLETE,
    "summary": SUMMARY_COMPLETE,
    "prompt_builder": PROMPT_BUILDER_COMPLETE,
}

ALL_EVENT_TYPES: set[str] = {
    EXTRACTION_COMPLETE,
    MEMORY_UPDATE_COMPLETE,
    PERSISTENCE_COMPLETE,
    LIFE_SIMULATION_COMPLETE,
    EMOTIONAL_STATE_COMPLETE,
    VICE_COMPLETE,
    GAME_STATE_COMPLETE,
    CONFLICT_COMPLETE,
    TOUCHPOINT_COMPLETE,
    SUMMARY_COMPLETE,
    PROMPT_BUILDER_COMPLETE,
    PIPELINE_COMPLETE,
}
