"""Post-Processing Pipeline (Spec 021, T020 + Spec 022-027 Humanization).

Orchestrates all post-processing steps after conversation ends:
1. Graph updates (user facts, relationship events)
2. Summary generation (daily, weekly)
3. Life simulation (tomorrow's events) - Spec 022
4. Emotional state update - Spec 023
5. Conflict check - Spec 027
6. Touchpoint scheduling - Spec 025
7. Layer pre-composition (Layers 2-4)
8. Context package storage

Spec 029: Wire all humanization modules into production pipeline.

AC-T020.1: PostProcessingPipeline class orchestrates all steps
AC-T020.2: process() method runs all steps in sequence
AC-T020.3: Returns ProcessingResult with step status
AC-T020.4: Error handling with partial completion support
AC-T020.5: Unit tests for pipeline
AC-T014.1: PostProcessingPipeline calls LifeSimulator
AC-T014.2: Events generated after each conversation
AC-T014.3: Errors logged but don't fail pipeline
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID

from nikita.context.package import ContextPackage
from nikita.context.store import PackageStore, get_package_store

logger = logging.getLogger(__name__)


class StepStatus(str, Enum):
    """Status of a processing step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ProcessingStep:
    """Result of a single processing step.

    Attributes:
        name: Step name (e.g., "graph_update", "summary_generation").
        status: Current status of the step.
        started_at: When the step started.
        completed_at: When the step completed (or failed).
        error_message: Error message if step failed.
        metadata: Additional step-specific metadata.
    """

    name: str
    status: StepStatus = StepStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def mark_running(self) -> None:
        """Mark step as running."""
        self.status = StepStatus.RUNNING
        self.started_at = datetime.now(timezone.utc)

    def mark_completed(self, metadata: dict[str, Any] | None = None) -> None:
        """Mark step as completed."""
        self.status = StepStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)
        if metadata:
            self.metadata.update(metadata)

    def mark_failed(self, error: str) -> None:
        """Mark step as failed."""
        self.status = StepStatus.FAILED
        self.completed_at = datetime.now(timezone.utc)
        self.error_message = error

    def mark_skipped(self, reason: str) -> None:
        """Mark step as skipped."""
        self.status = StepStatus.SKIPPED
        self.completed_at = datetime.now(timezone.utc)
        self.metadata["skip_reason"] = reason


@dataclass
class ProcessingResult:
    """Result of full post-processing pipeline.

    Attributes:
        user_id: User being processed.
        conversation_id: Conversation that triggered processing.
        steps: Results of each processing step.
        started_at: When pipeline started.
        completed_at: When pipeline completed.
        package: Generated context package (if successful).
        success: Whether pipeline completed successfully.
    """

    user_id: UUID
    conversation_id: UUID
    steps: list[ProcessingStep] = field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    package: ContextPackage | None = None
    success: bool = False

    @property
    def failed_steps(self) -> list[ProcessingStep]:
        """Get list of failed steps."""
        return [s for s in self.steps if s.status == StepStatus.FAILED]

    @property
    def completed_steps(self) -> list[ProcessingStep]:
        """Get list of completed steps."""
        return [s for s in self.steps if s.status == StepStatus.COMPLETED]

    @property
    def partial_success(self) -> bool:
        """True if some steps completed despite failures."""
        return len(self.completed_steps) > 0 and len(self.failed_steps) > 0


class PostProcessingPipeline:
    """Orchestrates post-processing after conversation ends.

    Pipeline steps (Spec 029: All humanization modules wired):
    1. Update knowledge graphs (GraphUpdater)
    2. Generate summaries (SummaryGenerator)
    3. Simulate life events for tomorrow (LifeSimulator) - Spec 022
    4. Update emotional state (StateComputer) - Spec 023
    5. Check for conflicts (ConflictGenerator) - Spec 027
    6. Schedule touchpoints (TouchpointScheduler) - Spec 025
    7. Pre-compose layers (LayerComposer)
    8. Store context package (PackageStore)

    Attributes:
        graph_updater: Updates knowledge graphs.
        summary_generator: Generates daily/weekly summaries.
        life_simulator: Generates Nikita's daily life events.
        state_computer: Computes emotional state after conversations.
        conflict_generator: Checks for conflict triggers.
        touchpoint_scheduler: Schedules proactive touchpoints.
        layer_composer: Pre-composes Layers 2-4.
        package_store: Stores context packages.
    """

    def __init__(
        self,
        graph_updater: Any | None = None,
        summary_generator: Any | None = None,
        life_simulator: Any | None = None,
        state_computer: Any | None = None,
        conflict_generator: Any | None = None,
        touchpoint_scheduler: Any | None = None,
        layer_composer: Any | None = None,
        package_store: PackageStore | None = None,
    ) -> None:
        """Initialize pipeline.

        Args:
            graph_updater: GraphUpdater instance (lazy loaded if None).
            summary_generator: SummaryGenerator instance (lazy loaded if None).
            life_simulator: LifeSimulator instance (lazy loaded if None).
            state_computer: StateComputer instance (lazy loaded if None).
            conflict_generator: ConflictGenerator instance (lazy loaded if None).
            touchpoint_scheduler: TouchpointScheduler instance (lazy loaded if None).
            layer_composer: LayerComposer instance (lazy loaded if None).
            package_store: PackageStore instance (lazy loaded if None).
        """
        self._graph_updater = graph_updater
        self._summary_generator = summary_generator
        self._life_simulator = life_simulator
        self._state_computer = state_computer
        self._conflict_generator = conflict_generator
        self._touchpoint_scheduler = touchpoint_scheduler
        self._layer_composer = layer_composer
        self._package_store = package_store

    @property
    def graph_updater(self) -> Any:
        """Get graph updater (lazy load)."""
        if self._graph_updater is None:
            from nikita.post_processing.graph_updater import get_graph_updater

            self._graph_updater = get_graph_updater()
        return self._graph_updater

    @property
    def summary_generator(self) -> Any:
        """Get summary generator (lazy load)."""
        if self._summary_generator is None:
            from nikita.post_processing.summary_generator import get_summary_generator

            self._summary_generator = get_summary_generator()
        return self._summary_generator

    @property
    def life_simulator(self) -> Any:
        """Get life simulator (lazy load)."""
        if self._life_simulator is None:
            from nikita.life_simulation.simulator import get_life_simulator

            self._life_simulator = get_life_simulator()
        return self._life_simulator

    @property
    def state_computer(self) -> Any:
        """Get emotional state computer (lazy load) - Spec 023."""
        if self._state_computer is None:
            from nikita.emotional_state import get_state_computer

            self._state_computer = get_state_computer()
        return self._state_computer

    @property
    def conflict_generator(self) -> Any:
        """Get conflict generator (lazy load) - Spec 027."""
        if self._conflict_generator is None:
            from nikita.conflicts.generator import get_conflict_generator

            self._conflict_generator = get_conflict_generator()
        return self._conflict_generator

    @property
    def touchpoint_scheduler(self) -> Any:
        """Get touchpoint scheduler (lazy load) - Spec 025."""
        if self._touchpoint_scheduler is None:
            from nikita.touchpoints.scheduler import TouchpointScheduler

            self._touchpoint_scheduler = TouchpointScheduler()
        return self._touchpoint_scheduler

    @property
    def layer_composer(self) -> Any:
        """Get layer composer (lazy load)."""
        if self._layer_composer is None:
            from nikita.post_processing.layer_composer import get_layer_composer

            self._layer_composer = get_layer_composer()
        return self._layer_composer

    @property
    def package_store(self) -> PackageStore:
        """Get package store (lazy load)."""
        if self._package_store is None:
            self._package_store = get_package_store()
        return self._package_store

    async def process(
        self,
        user_id: UUID,
        conversation_id: UUID,
        transcript: list[dict[str, str]] | None = None,
    ) -> ProcessingResult:
        """Run full post-processing pipeline.

        Args:
            user_id: User to process for.
            conversation_id: Conversation that triggered processing.
            transcript: Optional conversation transcript for processing.

        Returns:
            ProcessingResult with status of all steps.
        """
        result = ProcessingResult(
            user_id=user_id,
            conversation_id=conversation_id,
            started_at=datetime.now(timezone.utc),
        )

        # Initialize steps (Spec 029: All humanization modules wired)
        graph_step = ProcessingStep(name="graph_update")
        summary_step = ProcessingStep(name="summary_generation")
        life_sim_step = ProcessingStep(name="life_simulation")
        emotional_step = ProcessingStep(name="emotional_state")  # Spec 023
        conflict_step = ProcessingStep(name="conflict_check")  # Spec 027
        touchpoint_step = ProcessingStep(name="touchpoint_scheduling")  # Spec 025
        layer_step = ProcessingStep(name="layer_composition")
        storage_step = ProcessingStep(name="package_storage")

        result.steps = [
            graph_step,
            summary_step,
            life_sim_step,
            emotional_step,
            conflict_step,
            touchpoint_step,
            layer_step,
            storage_step,
        ]

        # Step 1: Update graphs
        await self._run_graph_update(user_id, conversation_id, transcript, graph_step)

        # Step 2: Generate summaries
        await self._run_summary_generation(user_id, conversation_id, summary_step)

        # Step 3: Generate life events for tomorrow (Spec 022)
        await self._run_life_simulation(user_id, life_sim_step)

        # Step 4: Update emotional state (Spec 023)
        await self._run_emotional_state_update(user_id, transcript, emotional_step)

        # Step 5: Check for conflicts (Spec 027)
        await self._run_conflict_check(user_id, conflict_step)

        # Step 6: Schedule touchpoints (Spec 025)
        await self._run_touchpoint_scheduling(user_id, touchpoint_step)

        # Step 7: Pre-compose layers
        package = await self._run_layer_composition(user_id, layer_step)

        # Step 8: Store package
        if package:
            await self._run_package_storage(user_id, package, storage_step)
            result.package = package

        # Finalize
        result.completed_at = datetime.now(timezone.utc)
        result.success = len(result.failed_steps) == 0

        # Log result
        if result.success:
            logger.info(
                f"Post-processing completed for user {user_id}: "
                f"{len(result.completed_steps)}/{len(result.steps)} steps"
            )
        else:
            logger.warning(
                f"Post-processing partial failure for user {user_id}: "
                f"failed steps: {[s.name for s in result.failed_steps]}"
            )

        return result

    async def _run_graph_update(
        self,
        user_id: UUID,
        conversation_id: UUID,
        transcript: list[dict[str, str]] | None,
        step: ProcessingStep,
    ) -> None:
        """Run graph update step."""
        step.mark_running()
        try:
            facts_count, events_count = await self.graph_updater.update(
                user_id=user_id,
                conversation_id=conversation_id,
                transcript=transcript,
            )
            step.mark_completed(
                {"facts_extracted": facts_count, "events_extracted": events_count}
            )
        except Exception as e:
            logger.exception(f"Graph update failed for user {user_id}")
            step.mark_failed(str(e))

    async def _run_summary_generation(
        self,
        user_id: UUID,
        conversation_id: UUID,
        step: ProcessingStep,
    ) -> None:
        """Run summary generation step."""
        step.mark_running()
        try:
            daily_updated, weekly_updated = await self.summary_generator.generate(
                user_id=user_id,
                conversation_id=conversation_id,
            )
            step.mark_completed(
                {"daily_updated": daily_updated, "weekly_updated": weekly_updated}
            )
        except Exception as e:
            logger.exception(f"Summary generation failed for user {user_id}")
            step.mark_failed(str(e))

    async def _run_life_simulation(
        self,
        user_id: UUID,
        step: ProcessingStep,
    ) -> None:
        """Run life simulation step (Spec 022).

        Generates tomorrow's events for Nikita. Errors don't fail the pipeline.
        """
        step.mark_running()
        try:
            events = await self.life_simulator.generate_next_day_events(user_id=user_id)
            step.mark_completed({"events_generated": len(events)})
        except Exception as e:
            # Log but don't fail pipeline (AC-T014.3)
            logger.warning(f"Life simulation failed for user {user_id}: {e}")
            step.mark_failed(str(e))

    async def _run_emotional_state_update(
        self,
        user_id: UUID,
        transcript: list[dict[str, str]] | None,
        step: ProcessingStep,
    ) -> None:
        """Run emotional state update step (Spec 023).

        Computes and stores Nikita's emotional state after conversation.
        Errors don't fail the pipeline.
        """
        step.mark_running()
        try:
            from nikita.emotional_state import ConversationTone, get_state_store

            # Analyze transcript to determine conversation tones
            tones: list[ConversationTone] = []
            if transcript:
                msg_count = len(transcript)
                # Derive tone from conversation length and content
                if msg_count > 10:
                    tones.append(ConversationTone.PLAYFUL)  # Long engaged convo
                elif msg_count > 5:
                    tones.append(ConversationTone.SUPPORTIVE)
                elif msg_count < 3:
                    tones.append(ConversationTone.COLD)  # Very short convo
                else:
                    tones.append(ConversationTone.NEUTRAL)

            # Get user context for relationship modifiers
            from nikita.db.database import get_session_maker
            from nikita.db.repositories.user_repository import UserRepository

            async with get_session_maker()() as session:
                user_repo = UserRepository(session)
                user = await user_repo.get(user_id)
                chapter = user.chapter if user else 1
                rel_score = user.relationship_score / 100.0 if user else 0.5

            # Compute new emotional state (sync method)
            new_state = self.state_computer.compute(
                user_id=user_id,
                conversation_tones=tones,
                chapter=chapter,
                relationship_score=rel_score,
            )

            # Store state
            store = get_state_store()
            await store.update_state(user_id, new_state)

            step.mark_completed({
                "arousal": new_state.arousal,
                "valence": new_state.valence,
                "dominance": new_state.dominance,
                "intimacy": new_state.intimacy,
                "tones": [t.value for t in tones],
            })
        except Exception as e:
            logger.warning(f"Emotional state update failed for user {user_id}: {e}")
            step.mark_failed(str(e))

    async def _run_conflict_check(
        self,
        user_id: UUID,
        step: ProcessingStep,
    ) -> None:
        """Run conflict check step (Spec 027).

        Checks for conflict triggers based on user behavior patterns.
        Errors don't fail the pipeline.
        """
        step.mark_running()
        try:
            from datetime import timedelta

            from nikita.conflicts.generator import GenerationContext
            from nikita.conflicts.store import get_conflict_store
            from nikita.db.database import get_session_maker
            from nikita.db.repositories.user_repository import UserRepository

            # Get user context
            async with get_session_maker()() as session:
                user_repo = UserRepository(session)
                user = await user_repo.get(user_id)
                chapter = user.chapter if user else 1
                rel_score = user.relationship_score if user else 50

            # Check for recent triggers (last hour)
            store = get_conflict_store()
            since = datetime.now(timezone.utc) - timedelta(hours=1)
            recent_triggers = store.get_user_triggers(str(user_id), since=since)

            if recent_triggers:
                # Build generation context
                context = GenerationContext(
                    user_id=str(user_id),
                    chapter=chapter,
                    relationship_score=rel_score,
                )

                # Try to generate conflict from triggers
                result = self.conflict_generator.generate(
                    triggers=recent_triggers,
                    context=context,
                )

                step.mark_completed({
                    "conflict_triggered": result.generated,
                    "conflict_type": result.conflict.conflict_type.value if result.conflict else None,
                    "triggers_checked": len(recent_triggers),
                })
            else:
                step.mark_completed({
                    "conflict_triggered": False,
                    "triggers_checked": 0,
                })
        except Exception as e:
            logger.warning(f"Conflict check failed for user {user_id}: {e}")
            step.mark_failed(str(e))

    async def _run_touchpoint_scheduling(
        self,
        user_id: UUID,
        step: ProcessingStep,
    ) -> None:
        """Run touchpoint scheduling step (Spec 025).

        Evaluates whether to schedule next proactive message from Nikita.
        Errors don't fail the pipeline.
        """
        step.mark_running()
        try:
            from nikita.db.database import get_session_maker
            from nikita.db.repositories.user_repository import UserRepository

            # Get user context
            async with get_session_maker()() as session:
                user_repo = UserRepository(session)
                user = await user_repo.get(user_id)
                chapter = user.chapter if user else 1

            # Evaluate user for touchpoint triggers
            triggers = self.touchpoint_scheduler.evaluate_user(
                user_id=user_id,
                chapter=chapter,
                last_interaction_at=datetime.now(timezone.utc),  # Just had conversation
            )

            if triggers:
                # Schedule the first trigger
                trigger_ctx = triggers[0]
                touchpoint = self.touchpoint_scheduler.schedule(
                    user_id=user_id,
                    trigger_context=trigger_ctx,
                    delivery_delay_minutes=60,  # 1 hour after conversation ends
                )
                step.mark_completed({
                    "scheduled": True,
                    "trigger_type": trigger_ctx.trigger_type.value,
                    "triggers_found": len(triggers),
                })
            else:
                step.mark_completed({
                    "scheduled": False,
                    "reason": "no_triggers_applicable",
                })
        except Exception as e:
            logger.warning(f"Touchpoint scheduling failed for user {user_id}: {e}")
            step.mark_failed(str(e))

    async def _run_layer_composition(
        self,
        user_id: UUID,
        step: ProcessingStep,
    ) -> ContextPackage | None:
        """Run layer composition step."""
        step.mark_running()
        try:
            package = await self.layer_composer.compose(user_id=user_id)
            step.mark_completed({"package_created": True})
            return package
        except Exception as e:
            logger.exception(f"Layer composition failed for user {user_id}")
            step.mark_failed(str(e))
            return None

    async def _run_package_storage(
        self,
        user_id: UUID,
        package: ContextPackage,
        step: ProcessingStep,
    ) -> None:
        """Run package storage step."""
        step.mark_running()
        try:
            await self.package_store.set(user_id, package)
            step.mark_completed({"stored": True})
        except Exception as e:
            logger.exception(f"Package storage failed for user {user_id}")
            step.mark_failed(str(e))


# Module-level singleton
_default_pipeline: PostProcessingPipeline | None = None


def get_post_processing_pipeline() -> PostProcessingPipeline:
    """Get the singleton PostProcessingPipeline instance.

    Returns:
        Cached PostProcessingPipeline instance.
    """
    global _default_pipeline
    if _default_pipeline is None:
        _default_pipeline = PostProcessingPipeline()
    return _default_pipeline
