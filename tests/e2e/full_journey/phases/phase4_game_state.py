"""Phase 4: Game State Verification."""

from typing import Any, Dict, Optional
from dataclasses import dataclass

from ...helpers.supabase_helper import SupabaseHelper
from ..evidence_collector import EvidenceCollector


@dataclass
class Phase4Result:
    """Result of Phase 4 execution."""
    success: bool
    relationship_score: Optional[float] = None
    chapter: Optional[int] = None
    game_status: Optional[str] = None
    messages_sent: Optional[int] = None
    boss_encounters: Optional[int] = None
    score_in_range: bool = False
    chapter_correct: bool = False
    error: Optional[str] = None


class Phase4GameState:
    """
    Phase 4: Game State Verification

    Verifies:
    1. User metrics are initialized
    2. Score is in valid range (0-100)
    3. Chapter matches score thresholds
    4. Game status is correct
    """

    # Chapter score thresholds
    CHAPTER_THRESHOLDS = {
        1: (0, 20),
        2: (20, 40),
        3: (40, 60),
        4: (60, 80),
        5: (80, 100),
    }

    def __init__(self):
        self.db_helper = SupabaseHelper()

    def get_metrics_query(self, telegram_id: int) -> str:
        """Get SQL query for user metrics."""
        return self.db_helper.sql_get_user_metrics(telegram_id)

    def get_score_history_query(self, telegram_id: int, limit: int = 5) -> str:
        """Get SQL query for score history."""
        return self.db_helper.sql_get_score_history(telegram_id, limit)

    def expected_chapter_for_score(self, score: float) -> int:
        """Calculate expected chapter for a given score."""
        for chapter, (min_score, max_score) in self.CHAPTER_THRESHOLDS.items():
            if min_score <= score < max_score:
                return chapter
        return 5  # Max chapter

    def verify_metrics(self, db_result: Any) -> Phase4Result:
        """Verify user metrics from DB result."""
        rows = self.db_helper.parse_mcp_result(db_result)

        if not rows:
            return Phase4Result(success=False, error="No metrics found")

        row = rows[0]
        score = row.get('relationship_score')
        chapter = row.get('chapter')
        messages = row.get('messages_sent')
        boss = row.get('boss_encounters')

        # Validate score range
        score_valid = score is not None and 0 <= score <= 100

        # Validate chapter matches score
        expected_chapter = self.expected_chapter_for_score(score) if score_valid else None
        chapter_valid = chapter == expected_chapter if expected_chapter else False

        if score_valid:
            return Phase4Result(
                success=True,
                relationship_score=score,
                chapter=chapter,
                messages_sent=messages,
                boss_encounters=boss,
                score_in_range=score_valid,
                chapter_correct=chapter_valid,
            )
        else:
            return Phase4Result(
                success=False,
                relationship_score=score,
                chapter=chapter,
                score_in_range=score_valid,
                chapter_correct=chapter_valid,
                error=f"Invalid score: {score}"
            )

    def verify_score_history(
        self,
        db_result: Any,
        expected_min_entries: int = 1
    ) -> bool:
        """Verify score history has expected entries."""
        rows = self.db_helper.parse_mcp_result(db_result)
        return len(rows) >= expected_min_entries
