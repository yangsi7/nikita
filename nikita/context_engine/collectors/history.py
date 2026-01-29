"""History collector for Context Engine (Spec 039).

Collects conversation history context: threads, thoughts, summaries.
"""

from datetime import UTC, date, datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field

from nikita.context_engine.collectors.base import BaseCollector, CollectorContext
from nikita.context_engine.models import ThreadInfo
from nikita.db.repositories.summary_repository import DailySummaryRepository
from nikita.db.repositories.thread_repository import ConversationThreadRepository
from nikita.db.repositories.thought_repository import NikitaThoughtRepository


class HistoryData(BaseModel):
    """Output from HistoryCollector."""

    # Open threads (unresolved topics)
    open_threads: list[ThreadInfo] = Field(default_factory=list)
    thread_count_by_type: dict[str, int] = Field(default_factory=dict)

    # Recent thoughts (Nikita's inner life)
    recent_thoughts: list[str] = Field(default_factory=list)

    # Daily summaries
    today_summary: str | None = Field(default=None)
    today_key_moments: list[str] = Field(default_factory=list)
    week_summaries: list[str] = Field(default_factory=list)

    # Last conversation summary
    last_conversation_summary: str | None = Field(default=None)


class HistoryCollector(BaseCollector[HistoryData]):
    """Collector that gathers conversation history context.

    Collects:
    - Open conversation threads (questions, follow-ups, promises)
    - Nikita's recent thoughts (inner life simulation)
    - Daily summaries (today + past week)
    - Last conversation summary
    """

    name = "history"
    timeout_seconds = 5.0
    max_retries = 2

    async def collect(self, ctx: CollectorContext) -> HistoryData:
        """Collect history context from database.

        Args:
            ctx: Collector context with session and user_id.

        Returns:
            HistoryData with threads, thoughts, and summaries.
        """
        # Initialize repositories
        thread_repo = ConversationThreadRepository(ctx.session)
        thought_repo = NikitaThoughtRepository(ctx.session)
        summary_repo = DailySummaryRepository(ctx.session)

        # Collect all data in parallel
        threads_data = await self._collect_threads(thread_repo, ctx.user_id)
        thoughts_data = await self._collect_thoughts(thought_repo, ctx.user_id)
        summaries_data = await self._collect_summaries(summary_repo, ctx.user_id)

        return HistoryData(
            open_threads=threads_data["threads"],
            thread_count_by_type=threads_data["counts"],
            recent_thoughts=thoughts_data,
            today_summary=summaries_data["today_summary"],
            today_key_moments=summaries_data["today_key_moments"],
            week_summaries=summaries_data["week_summaries"],
            last_conversation_summary=summaries_data["last_conversation"],
        )

    async def _collect_threads(
        self,
        repo: ConversationThreadRepository,
        user_id,
    ) -> dict[str, Any]:
        """Collect open threads organized by type."""
        threads_by_type = await repo.get_threads_for_prompt(user_id, max_per_type=10)

        threads_list: list[ThreadInfo] = []
        counts: dict[str, int] = {}
        now = datetime.now(UTC)

        for thread_type, threads in threads_by_type.items():
            counts[thread_type] = len(threads)
            for thread in threads:
                # Calculate age in hours
                age_hours = 0.0
                if thread.created_at:
                    delta = now - thread.created_at
                    age_hours = delta.total_seconds() / 3600

                threads_list.append(
                    ThreadInfo(
                        topic=thread.content,
                        status=thread.status,
                        priority=self._calculate_priority(thread_type, age_hours),
                        age_hours=age_hours,
                        last_mentioned=thread.created_at,  # Use created_at as proxy
                        notes=thread_type,  # Store type in notes for context
                    )
                )

        # Sort by priority descending
        threads_list.sort(key=lambda t: t.priority, reverse=True)

        return {"threads": threads_list[:20], "counts": counts}  # Limit to 20

    def _calculate_priority(self, thread_type: str, age_hours: float) -> int:
        """Calculate thread priority based on type and age."""
        # Base priority by type
        type_priority = {
            "question": 4,  # Highest - unanswered questions
            "promise": 3,  # High - things Nikita promised
            "follow_up": 2,  # Medium - topics to revisit
            "topic": 1,  # Low - general topics
        }
        base = type_priority.get(thread_type, 1)

        # Boost recent threads
        if age_hours < 1:
            return min(base + 2, 5)
        elif age_hours < 24:
            return min(base + 1, 5)
        elif age_hours > 72:
            return max(base - 1, 0)

        return base

    async def _collect_thoughts(
        self,
        repo: NikitaThoughtRepository,
        user_id,
    ) -> list[str]:
        """Collect Nikita's recent thoughts."""
        thoughts = await repo.get_active_thoughts(user_id, limit=10)
        return [t.content for t in thoughts if t.content]

    async def _collect_summaries(
        self,
        repo: DailySummaryRepository,
        user_id,
    ) -> dict[str, Any]:
        """Collect today's summary and past week's summaries."""
        today = date.today()
        week_ago = today - timedelta(days=7)

        # Get today's summary
        today_summary = await repo.get_by_date(user_id, today)
        today_text = None
        today_moments: list[str] = []

        if today_summary:
            today_text = today_summary.summary_text or today_summary.nikita_summary_text
            if today_summary.key_moments:
                today_moments = [m.get("description", str(m)) for m in today_summary.key_moments if m]

        # Get week's summaries
        week_summaries = await repo.get_range(user_id, week_ago, today - timedelta(days=1))
        week_texts: list[str] = []
        for summary in week_summaries:
            text = summary.summary_text or summary.nikita_summary_text
            if text:
                week_texts.append(f"{summary.date.strftime('%A')}: {text}")

        # Get last conversation summary (most recent summary with text)
        recent = await repo.get_recent(user_id, limit=1)
        last_conv = None
        if recent and (recent[0].summary_text or recent[0].nikita_summary_text):
            last_conv = recent[0].summary_text or recent[0].nikita_summary_text

        return {
            "today_summary": today_text,
            "today_key_moments": today_moments,
            "week_summaries": week_texts,
            "last_conversation": last_conv,
        }

    def get_fallback(self) -> HistoryData:
        """Return empty history if collection fails."""
        return HistoryData()
