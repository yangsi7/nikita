"""Post-Processing Pipeline for Hierarchical Prompt Composition (Spec 021).

This module handles async post-processing after conversations end:
1. Update knowledge graphs (user facts, relationship events)
2. Generate/update summaries (daily, weekly)
3. Pre-compose Layers 2-4 (chapter, emotional, situation)
4. Build and store ContextPackage for next conversation

Architecture:
- Runs async after conversation ends (15 min timeout or call end)
- Non-blocking, errors don't affect user experience
- Results stored in context_packages table for fast retrieval

Related:
- nikita/context/ - Context injection and prompt composition
- nikita/context/post_processor.py - Existing 9-stage pipeline (threads, thoughts)
- nikita/memory/ - Graphiti knowledge graph integration
"""

from nikita.post_processing.pipeline import (
    PostProcessingPipeline,
    ProcessingResult,
    ProcessingStep,
    StepStatus,
    get_post_processing_pipeline,
)
from nikita.post_processing.graph_updater import (
    GraphUpdater,
    get_graph_updater,
)
from nikita.post_processing.summary_generator import (
    SummaryGenerator,
    get_summary_generator,
)
from nikita.post_processing.layer_composer import (
    LayerComposer,
    get_layer_composer,
)
from nikita.post_processing.trigger import (
    add_pipeline_trigger_to_background_tasks,
    is_pipeline_enabled,
    trigger_pipeline,
    trigger_pipeline_background,
)
from nikita.post_processing.adapter import (
    process_conversations,
    AdapterResult,
)

__all__ = [
    # Pipeline
    "PostProcessingPipeline",
    "ProcessingResult",
    "ProcessingStep",
    "StepStatus",
    "get_post_processing_pipeline",
    # Graph Updater
    "GraphUpdater",
    "get_graph_updater",
    # Summary Generator
    "SummaryGenerator",
    "get_summary_generator",
    # Layer Composer
    "LayerComposer",
    "get_layer_composer",
    # Trigger
    "trigger_pipeline",
    "trigger_pipeline_background",
    "add_pipeline_trigger_to_background_tasks",
    "is_pipeline_enabled",
]
