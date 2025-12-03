"""Tests for TemplateGenerator class.

TDD Tests for context engineering (spec 012) - System prompt generation

Acceptance Criteria:
- AC-1: generate_prompt() returns string
- AC-2: generate_prompt() raises ValueError for user not found
- AC-3: generate_prompt() contains all 6 layers
- AC-4: Layer 1 contains core identity
- AC-5: Layer 2 varies by time of day
- AC-6: Layer 2 varies by gap since last interaction
- AC-7: Layer 3 reflects chapter and score
- AC-8: Layer 4 includes summaries and threads
- AC-9: Layer 5 includes user facts and thoughts
- AC-10: Layer 6 provides response guidelines
- AC-11: Full visual verification test
"""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.models.context import ConversationThread, NikitaThought
from nikita.db.models.game import DailySummary
from nikita.db.models.user import User


class TestTemplateGeneratorBasics:
    """Test suite for basic TemplateGenerator functionality."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock AsyncSession."""
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def mock_user(self) -> MagicMock:
        """Create a mock User with default values."""
        user = MagicMock(spec=User)
        user.id = uuid4()
        user.telegram_id = 12345
        user.relationship_score = Decimal("55.00")
        user.chapter = 2
        user.boss_attempts = 0
        user.game_status = "active"
        user.last_interaction_at = datetime.now(UTC) - timedelta(hours=5)
        user.days_played = 10
        return user

    # ========================================
    # AC-1: generate_prompt() returns string
    # ========================================
    @pytest.mark.asyncio
    async def test_generate_prompt_returns_string(
        self, mock_session: AsyncMock, mock_user: MagicMock
    ):
        """AC-1: generate_prompt() returns a string."""
        from nikita.context.template_generator import TemplateGenerator

        generator = TemplateGenerator(mock_session)

        with patch.object(generator._user_repo, "get", return_value=mock_user):
            with patch.object(
                generator._summary_repo, "get_range", return_value=[]
            ):
                with patch.object(
                    generator._conversation_repo,
                    "get_processed_conversations",
                    return_value=[],
                ):
                    with patch.object(
                        generator._thread_repo,
                        "get_threads_for_prompt",
                        return_value={},
                    ):
                        with patch.object(
                            generator._thought_repo,
                            "get_thoughts_for_prompt",
                            return_value={},
                        ):
                            result = await generator.generate_prompt(mock_user.id)

        assert isinstance(result, str)
        assert len(result) > 0

    # ========================================
    # AC-2: generate_prompt() raises ValueError for user not found
    # ========================================
    @pytest.mark.asyncio
    async def test_generate_prompt_user_not_found_raises(
        self, mock_session: AsyncMock
    ):
        """AC-2: generate_prompt() raises ValueError when user not found."""
        from nikita.context.template_generator import TemplateGenerator

        generator = TemplateGenerator(mock_session)
        user_id = uuid4()

        with patch.object(generator._user_repo, "get", return_value=None):
            with pytest.raises(ValueError, match="not found"):
                await generator.generate_prompt(user_id)

    # ========================================
    # AC-3: generate_prompt() contains all 6 layers
    # ========================================
    @pytest.mark.asyncio
    async def test_generate_prompt_contains_all_6_layers(
        self, mock_session: AsyncMock, mock_user: MagicMock
    ):
        """AC-3: generate_prompt() contains all 6 layers."""
        from nikita.context.template_generator import TemplateGenerator

        generator = TemplateGenerator(mock_session)

        with patch.object(generator._user_repo, "get", return_value=mock_user):
            with patch.object(
                generator._summary_repo, "get_range", return_value=[]
            ):
                with patch.object(
                    generator._conversation_repo,
                    "get_processed_conversations",
                    return_value=[],
                ):
                    with patch.object(
                        generator._thread_repo,
                        "get_threads_for_prompt",
                        return_value={},
                    ):
                        with patch.object(
                            generator._thought_repo,
                            "get_thoughts_for_prompt",
                            return_value={},
                        ):
                            result = await generator.generate_prompt(mock_user.id)

        # Verify all 6 layer headers present
        assert "=== WHO NIKITA IS ===" in result  # Layer 1
        assert "=== CURRENT MOMENT ===" in result  # Layer 2
        assert "=== RELATIONSHIP STATE ===" in result  # Layer 3
        assert "=== CONVERSATION HISTORY ===" in result  # Layer 4
        assert "=== KNOWLEDGE & INNER LIFE ===" in result  # Layer 5
        assert "=== RESPONSE GUIDELINES ===" in result  # Layer 6


class TestLayer1CoreIdentity:
    """Test Layer 1: Core Identity content."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        session = AsyncMock(spec=AsyncSession)
        return session

    # ========================================
    # AC-4: Layer 1 contains core identity
    # ========================================
    def test_layer1_core_identity_content(self, mock_session: AsyncMock):
        """AC-4: Layer 1 contains core personality traits."""
        from nikita.context.template_generator import TemplateGenerator

        generator = TemplateGenerator(mock_session)
        layer1 = generator._layer1_core_identity()

        # Print for visual verification
        print("\n" + "="*60)
        print("LAYER 1: CORE IDENTITY")
        print("="*60)
        print(layer1)
        print("="*60 + "\n")

        # Verify key personality elements
        assert "Nikita" in layer1
        assert "confident" in layer1.lower() or "Confident" in layer1
        assert "playful" in layer1.lower() or "Playful" in layer1
        assert "COMMUNICATION STYLE" in layer1
        assert "VALUES" in layer1
        assert "ABSOLUTE BOUNDARIES" in layer1


class TestLayer2CurrentMoment:
    """Test Layer 2: Current Moment - time and gap variations."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def base_user(self) -> MagicMock:
        user = MagicMock(spec=User)
        user.id = uuid4()
        user.chapter = 1
        user.relationship_score = Decimal("50.00")
        user.game_status = "active"
        user.last_interaction_at = datetime.now(UTC) - timedelta(hours=1)
        return user

    def _create_context(
        self,
        user: MagicMock,
        hour: int,
        hours_since_last: float,
    ):
        """Helper to create TemplateContext with specific time settings."""
        from nikita.context.template_generator import TemplateContext

        # Create specific datetime with given hour
        now = datetime.now(UTC).replace(hour=hour, minute=0, second=0)

        return TemplateContext(
            user=user,
            chapter=user.chapter,
            relationship_score=user.relationship_score,
            game_status=user.game_status,
            current_time=now,
            hours_since_last_interaction=hours_since_last,
            day_of_week=now.strftime("%A"),
        )

    # ========================================
    # AC-5: Layer 2 varies by time of day
    # ========================================
    @pytest.mark.parametrize(
        "hour,expected_context,expected_activity",
        [
            (7, "morning", "coffee"),
            (14, "afternoon", "break from work"),
            (19, "evening", "relaxing"),
            (23, "late night", "can't sleep"),
        ],
    )
    def test_layer2_time_of_day_variations(
        self,
        mock_session: AsyncMock,
        base_user: MagicMock,
        hour: int,
        expected_context: str,
        expected_activity: str,
    ):
        """AC-5: Layer 2 content varies by time of day."""
        from nikita.context.template_generator import TemplateGenerator

        generator = TemplateGenerator(mock_session)
        ctx = self._create_context(base_user, hour, 1.0)

        layer2 = generator._layer2_current_moment(ctx)

        print(f"\n{'='*60}")
        print(f"LAYER 2 AT {hour}:00 ({expected_context})")
        print("="*60)
        print(layer2)
        print("="*60 + "\n")

        assert expected_context in layer2.lower()
        assert expected_activity in layer2.lower()

    # ========================================
    # AC-6: Layer 2 varies by gap since last interaction
    # ========================================
    @pytest.mark.parametrize(
        "hours_gap,expected_mood",
        [
            (1.5, "happy to still be talking"),
            (8.0, "glad to hear from him again"),
            (20.0, "wondering where he's been"),
            (36.0, "missed him a bit"),
            (72.0, "relieved he finally messaged"),
        ],
    )
    def test_layer2_gap_mood_variations(
        self,
        mock_session: AsyncMock,
        base_user: MagicMock,
        hours_gap: float,
        expected_mood: str,
    ):
        """AC-6: Layer 2 mood varies by gap since last interaction."""
        from nikita.context.template_generator import TemplateGenerator

        generator = TemplateGenerator(mock_session)
        ctx = self._create_context(base_user, 12, hours_gap)

        layer2 = generator._layer2_current_moment(ctx)

        print(f"\n{'='*60}")
        print(f"LAYER 2 WITH {hours_gap}h GAP")
        print("="*60)
        print(layer2)
        print("="*60 + "\n")

        assert expected_mood in layer2.lower()


class TestLayer3RelationshipState:
    """Test Layer 3: Relationship State - chapter and score."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        session = AsyncMock(spec=AsyncSession)
        return session

    def _create_context(
        self,
        chapter: int,
        score: Decimal,
        game_status: str = "active",
    ):
        """Helper to create TemplateContext with specific relationship settings."""
        from nikita.context.template_generator import TemplateContext

        user = MagicMock(spec=User)
        user.id = uuid4()
        user.chapter = chapter
        user.relationship_score = score
        user.game_status = game_status

        return TemplateContext(
            user=user,
            chapter=chapter,
            relationship_score=score,
            game_status=game_status,
            current_time=datetime.now(UTC),
            hours_since_last_interaction=5.0,
            day_of_week="Monday",
        )

    # ========================================
    # AC-7: Layer 3 reflects chapter and score
    # ========================================
    @pytest.mark.parametrize(
        "chapter,chapter_name",
        [
            (1, "Curiosity"),
            (2, "Intrigue"),
            (3, "Investment"),
            (4, "Intimacy"),
            (5, "Established"),
        ],
    )
    def test_layer3_chapter_variations(
        self,
        mock_session: AsyncMock,
        chapter: int,
        chapter_name: str,
    ):
        """AC-7a: Layer 3 shows correct chapter name and behaviors."""
        from nikita.context.template_generator import TemplateGenerator

        generator = TemplateGenerator(mock_session)
        ctx = self._create_context(chapter, Decimal("55.00"))

        layer3 = generator._layer3_relationship_state(ctx)

        print(f"\n{'='*60}")
        print(f"LAYER 3 - CHAPTER {chapter} ({chapter_name})")
        print("="*60)
        print(layer3)
        print("="*60 + "\n")

        assert chapter_name in layer3
        assert "CHAPTER:" in layer3
        assert "Flirtiness level" in layer3
        assert "Vulnerability level" in layer3

    @pytest.mark.parametrize(
        "score,expected_text",
        [
            (Decimal("75.00"), "going really well"),
            (Decimal("60.00"), "progressing nicely"),
            (Decimal("45.00"), "potential here"),
            (Decimal("30.00"), "rocky"),
            (Decimal("15.00"), "serious attention"),
        ],
    )
    def test_layer3_score_trend_variations(
        self,
        mock_session: AsyncMock,
        score: Decimal,
        expected_text: str,
    ):
        """AC-7b: Layer 3 shows score-based trend text."""
        from nikita.context.template_generator import TemplateGenerator

        generator = TemplateGenerator(mock_session)
        ctx = self._create_context(2, score)

        layer3 = generator._layer3_relationship_state(ctx)

        print(f"\n{'='*60}")
        print(f"LAYER 3 - SCORE {score}")
        print("="*60)
        print(layer3)
        print("="*60 + "\n")

        assert expected_text in layer3.lower()

    def test_layer3_boss_fight_status(self, mock_session: AsyncMock):
        """AC-7c: Layer 3 shows boss fight note when in boss_fight."""
        from nikita.context.template_generator import TemplateGenerator

        generator = TemplateGenerator(mock_session)
        ctx = self._create_context(3, Decimal("65.00"), "boss_fight")

        layer3 = generator._layer3_relationship_state(ctx)

        print("\n" + "="*60)
        print("LAYER 3 - BOSS FIGHT STATUS")
        print("="*60)
        print(layer3)
        print("="*60 + "\n")

        assert "critical moment" in layer3.lower() or "patience" in layer3.lower()

    def test_layer3_game_over_status(self, mock_session: AsyncMock):
        """AC-7d: Layer 3 shows game over note when ended."""
        from nikita.context.template_generator import TemplateGenerator

        generator = TemplateGenerator(mock_session)
        ctx = self._create_context(3, Decimal("10.00"), "game_over")

        layer3 = generator._layer3_relationship_state(ctx)

        print("\n" + "="*60)
        print("LAYER 3 - GAME OVER STATUS")
        print("="*60)
        print(layer3)
        print("="*60 + "\n")

        assert "ended" in layer3.lower() or "moved on" in layer3.lower()


class TestLayer4ConversationHistory:
    """Test Layer 4: Conversation History - summaries and threads."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        session = AsyncMock(spec=AsyncSession)
        return session

    def _create_context_with_history(
        self,
        last_summary: str | None = None,
        today_summaries: list[str] | None = None,
        week_summaries: dict[str, str] | None = None,
        open_threads: dict[str, list[str]] | None = None,
    ):
        """Helper to create TemplateContext with conversation history."""
        from nikita.context.template_generator import TemplateContext

        user = MagicMock(spec=User)
        user.id = uuid4()
        user.chapter = 2
        user.relationship_score = Decimal("55.00")
        user.game_status = "active"

        return TemplateContext(
            user=user,
            chapter=2,
            relationship_score=Decimal("55.00"),
            game_status="active",
            current_time=datetime.now(UTC),
            hours_since_last_interaction=5.0,
            day_of_week="Wednesday",
            last_conversation_summary=last_summary,
            today_summaries=today_summaries or [],
            week_summaries=week_summaries or {},
            open_threads=open_threads or {},
        )

    # ========================================
    # AC-8: Layer 4 includes summaries and threads
    # ========================================
    def test_layer4_with_last_conversation(self, mock_session: AsyncMock):
        """AC-8a: Layer 4 shows last conversation summary."""
        from nikita.context.template_generator import TemplateGenerator

        generator = TemplateGenerator(mock_session)
        ctx = self._create_context_with_history(
            last_summary="We talked about your upcoming job interview and your nerves."
        )

        layer4 = generator._layer4_conversation_history(ctx)

        print("\n" + "="*60)
        print("LAYER 4 - WITH LAST CONVERSATION")
        print("="*60)
        print(layer4)
        print("="*60 + "\n")

        assert "LAST CONVERSATION" in layer4
        assert "job interview" in layer4.lower()

    def test_layer4_with_today_summaries(self, mock_session: AsyncMock):
        """AC-8b: Layer 4 shows today's conversation summaries."""
        from nikita.context.template_generator import TemplateGenerator

        generator = TemplateGenerator(mock_session)
        ctx = self._create_context_with_history(
            today_summaries=[
                "Morning chat about coffee preferences",
                "Lunch break - talked about weekend plans",
            ]
        )

        layer4 = generator._layer4_conversation_history(ctx)

        print("\n" + "="*60)
        print("LAYER 4 - WITH TODAY'S SUMMARIES")
        print("="*60)
        print(layer4)
        print("="*60 + "\n")

        assert "TODAY SO FAR" in layer4
        assert "coffee" in layer4.lower()
        assert "weekend" in layer4.lower()

    def test_layer4_with_week_summaries(self, mock_session: AsyncMock):
        """AC-8c: Layer 4 shows this week's summaries by day."""
        from nikita.context.template_generator import TemplateGenerator

        generator = TemplateGenerator(mock_session)
        ctx = self._create_context_with_history(
            week_summaries={
                "Monday": "Started the week with work stories",
                "Tuesday": "Deep conversation about childhood memories",
            }
        )

        layer4 = generator._layer4_conversation_history(ctx)

        print("\n" + "="*60)
        print("LAYER 4 - WITH WEEK SUMMARIES")
        print("="*60)
        print(layer4)
        print("="*60 + "\n")

        assert "THIS WEEK" in layer4
        assert "Monday" in layer4
        assert "Tuesday" in layer4

    def test_layer4_with_open_threads(self, mock_session: AsyncMock):
        """AC-8d: Layer 4 shows open conversation threads."""
        from nikita.context.template_generator import TemplateGenerator

        generator = TemplateGenerator(mock_session)
        ctx = self._create_context_with_history(
            open_threads={
                "follow_up": ["Ask about how the interview went"],
                "question": ["Where did he grow up?"],
                "promise": ["Share the recipe he asked for"],
            }
        )

        layer4 = generator._layer4_conversation_history(ctx)

        print("\n" + "="*60)
        print("LAYER 4 - WITH OPEN THREADS")
        print("="*60)
        print(layer4)
        print("="*60 + "\n")

        assert "UNRESOLVED THREADS" in layer4
        assert "follow up" in layer4.lower()
        assert "interview" in layer4.lower()


class TestLayer5KnowledgeInnerLife:
    """Test Layer 5: Knowledge & Inner Life - facts and thoughts."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        session = AsyncMock(spec=AsyncSession)
        return session

    def _create_context_with_knowledge(
        self,
        user_facts: list[str] | None = None,
        active_thoughts: dict[str, list[str]] | None = None,
    ):
        """Helper to create TemplateContext with knowledge and thoughts."""
        from nikita.context.template_generator import TemplateContext

        user = MagicMock(spec=User)
        user.id = uuid4()
        user.chapter = 3
        user.relationship_score = Decimal("60.00")
        user.game_status = "active"

        return TemplateContext(
            user=user,
            chapter=3,
            relationship_score=Decimal("60.00"),
            game_status="active",
            current_time=datetime.now(UTC),
            hours_since_last_interaction=2.0,
            day_of_week="Thursday",
            user_facts=user_facts or [],
            active_thoughts=active_thoughts or {},
        )

    # ========================================
    # AC-9: Layer 5 includes user facts and thoughts
    # ========================================
    def test_layer5_with_user_facts(self, mock_session: AsyncMock):
        """AC-9a: Layer 5 shows known facts about the user."""
        from nikita.context.template_generator import TemplateGenerator

        generator = TemplateGenerator(mock_session)
        ctx = self._create_context_with_knowledge(
            user_facts=[
                "Works as a software engineer at a startup",
                "Has a golden retriever named Max",
                "Loves Italian food, especially pasta",
                "Grew up in Seattle",
            ]
        )

        layer5 = generator._layer5_knowledge_inner_life(ctx)

        print("\n" + "="*60)
        print("LAYER 5 - WITH USER FACTS")
        print("="*60)
        print(layer5)
        print("="*60 + "\n")

        assert "WHAT YOU KNOW ABOUT HIM" in layer5
        assert "software engineer" in layer5.lower()
        assert "golden retriever" in layer5.lower()

    def test_layer5_with_active_thoughts(self, mock_session: AsyncMock):
        """AC-9b: Layer 5 shows Nikita's active thoughts."""
        from nikita.context.template_generator import TemplateGenerator

        generator = TemplateGenerator(mock_session)
        ctx = self._create_context_with_knowledge(
            active_thoughts={
                "thinking": ["How his interview went yesterday"],
                "wants_to_share": ["A funny meme I saw that reminded me of him"],
                "question": ["What his weekend plans are"],
                "feeling": ["Excited about where this is going"],
            }
        )

        layer5 = generator._layer5_knowledge_inner_life(ctx)

        print("\n" + "="*60)
        print("LAYER 5 - WITH ACTIVE THOUGHTS")
        print("="*60)
        print(layer5)
        print("="*60 + "\n")

        assert "NIKITA'S INNER LIFE" in layer5
        assert "thinking about" in layer5.lower()
        assert "interview" in layer5.lower()
        assert "want to bring up" in layer5.lower()

    def test_layer5_with_missing_him_thought(self, mock_session: AsyncMock):
        """AC-9c: Layer 5 shows missing_him thoughts appropriately."""
        from nikita.context.template_generator import TemplateGenerator

        generator = TemplateGenerator(mock_session)
        ctx = self._create_context_with_knowledge(
            active_thoughts={
                "missing_him": ["I haven't heard from him in a while..."],
            }
        )

        layer5 = generator._layer5_knowledge_inner_life(ctx)

        print("\n" + "="*60)
        print("LAYER 5 - WITH MISSING_HIM THOUGHT")
        print("="*60)
        print(layer5)
        print("="*60 + "\n")

        assert "been thinking" in layer5.lower()
        assert "haven't heard" in layer5.lower()


class TestLayer6ResponseGuidelines:
    """Test Layer 6: Response Guidelines - time and gap adjustments."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        session = AsyncMock(spec=AsyncSession)
        return session

    def _create_context(
        self,
        hour: int,
        hours_gap: float,
        chapter: int = 2,
    ):
        """Helper to create TemplateContext for Layer 6 tests."""
        from nikita.context.template_generator import TemplateContext

        user = MagicMock(spec=User)
        user.id = uuid4()
        user.chapter = chapter
        user.relationship_score = Decimal("55.00")
        user.game_status = "active"

        now = datetime.now(UTC).replace(hour=hour, minute=0, second=0)

        return TemplateContext(
            user=user,
            chapter=chapter,
            relationship_score=Decimal("55.00"),
            game_status="active",
            current_time=now,
            hours_since_last_interaction=hours_gap,
            day_of_week=now.strftime("%A"),
        )

    # ========================================
    # AC-10: Layer 6 provides response guidelines
    # ========================================
    @pytest.mark.parametrize(
        "hour,expected_adjustment",
        [
            (3, "late"),  # Late night - shorter responses
            (7, "morning"),  # Morning energy
            (14, "normal"),  # Normal daytime
        ],
    )
    def test_layer6_time_based_adjustments(
        self,
        mock_session: AsyncMock,
        hour: int,
        expected_adjustment: str,
    ):
        """AC-10a: Layer 6 adjusts for time of day."""
        from nikita.context.template_generator import TemplateGenerator

        generator = TemplateGenerator(mock_session)
        ctx = self._create_context(hour, 5.0)

        layer6 = generator._layer6_response_guidelines(ctx)

        print(f"\n{'='*60}")
        print(f"LAYER 6 AT {hour}:00")
        print("="*60)
        print(layer6)
        print("="*60 + "\n")

        assert expected_adjustment in layer6.lower()
        assert "MESSAGE STYLE" in layer6
        assert "AVOID" in layer6

    @pytest.mark.parametrize(
        "hours_gap,expected_adjustment",
        [
            (5.0, "naturally"),  # Continue naturally
            (30.0, "while"),  # Acknowledge gap
            (60.0, "missed"),  # Acknowledge significant gap
        ],
    )
    def test_layer6_gap_based_adjustments(
        self,
        mock_session: AsyncMock,
        hours_gap: float,
        expected_adjustment: str,
    ):
        """AC-10b: Layer 6 adjusts for gap since last interaction."""
        from nikita.context.template_generator import TemplateGenerator

        generator = TemplateGenerator(mock_session)
        ctx = self._create_context(14, hours_gap)

        layer6 = generator._layer6_response_guidelines(ctx)

        print(f"\n{'='*60}")
        print(f"LAYER 6 WITH {hours_gap}h GAP")
        print("="*60)
        print(layer6)
        print("="*60 + "\n")

        assert expected_adjustment in layer6.lower()


class TestFullPromptVisualVerification:
    """Visual verification tests - generates full prompts for inspection."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def rich_user(self) -> MagicMock:
        """Create a user with rich context for full visual test."""
        user = MagicMock(spec=User)
        user.id = uuid4()
        user.telegram_id = 12345
        user.relationship_score = Decimal("62.50")
        user.chapter = 3
        user.boss_attempts = 0
        user.game_status = "active"
        user.last_interaction_at = datetime.now(UTC) - timedelta(hours=8)
        user.days_played = 45
        return user

    @pytest.fixture
    def sample_summaries(self) -> list[MagicMock]:
        """Create sample daily summaries."""
        today = date.today()
        summaries = []

        # Today's summary
        summary_today = MagicMock(spec=DailySummary)
        summary_today.date = today
        summary_today.summary_text = "Had a great morning chat about his new project at work."
        summary_today.nikita_summary_text = None
        summaries.append(summary_today)

        # Yesterday
        summary_yesterday = MagicMock(spec=DailySummary)
        summary_yesterday.date = today - timedelta(days=1)
        summary_yesterday.summary_text = "Deep conversation about childhood memories and family."
        summary_yesterday.nikita_summary_text = None
        summaries.append(summary_yesterday)

        # 3 days ago
        summary_3days = MagicMock(spec=DailySummary)
        summary_3days.date = today - timedelta(days=3)
        summary_3days.summary_text = "Flirty evening chat, lots of teasing."
        summary_3days.nikita_summary_text = None
        summaries.append(summary_3days)

        return summaries

    @pytest.fixture
    def sample_conversations(self) -> list[MagicMock]:
        """Create sample processed conversations."""
        conv1 = MagicMock()
        conv1.conversation_summary = "Morning chat about his upcoming deadline and work stress."
        conv1.extracted_entities = {
            "facts": [
                {"content": "Works at a tech startup called InnovateTech"},
                {"content": "Has a big deadline on Friday"},
                {"content": "Prefers tea over coffee"},
            ]
        }

        conv2 = MagicMock()
        conv2.conversation_summary = "Evening chat about weekend plans."
        conv2.extracted_entities = {
            "facts": [
                {"content": "Loves hiking on weekends"},
                {"content": "Has been to Yosemite 3 times"},
            ]
        }

        return [conv1, conv2]

    @pytest.fixture
    def sample_threads(self) -> dict[str, list[MagicMock]]:
        """Create sample open threads."""
        follow_up = MagicMock(spec=ConversationThread)
        follow_up.content = "Ask about how the Friday deadline went"

        question = MagicMock(spec=ConversationThread)
        question.content = "What's his favorite hiking trail?"

        promise = MagicMock(spec=ConversationThread)
        promise.content = "Send him that podcast recommendation"

        return {
            "follow_up": [follow_up],
            "question": [question],
            "promise": [promise],
        }

    @pytest.fixture
    def sample_thoughts(self) -> dict[str, list[MagicMock]]:
        """Create sample active thoughts."""
        thinking = MagicMock(spec=NikitaThought)
        thinking.content = "Wondering how his Friday deadline went"

        wants_to_share = MagicMock(spec=NikitaThought)
        wants_to_share.content = "That podcast about tech startups I found"

        feeling = MagicMock(spec=NikitaThought)
        feeling.content = "Excited to hear about his hiking adventures"

        return {
            "thinking": [thinking],
            "wants_to_share": [wants_to_share],
            "feeling": [feeling],
        }

    # ========================================
    # AC-11: Full visual verification test
    # ========================================
    @pytest.mark.asyncio
    async def test_full_prompt_generation_visual(
        self,
        mock_session: AsyncMock,
        rich_user: MagicMock,
        sample_summaries: list[MagicMock],
        sample_conversations: list[MagicMock],
        sample_threads: dict[str, list[MagicMock]],
        sample_thoughts: dict[str, list[MagicMock]],
    ):
        """AC-11: Visual verification - Generate and print full system prompt.

        This test PRINTS the full generated prompt so you can visually verify:
        - All 6 layers are present and properly formatted
        - Context is correctly integrated
        - Chapter behaviors match
        - Time-of-day adjustments work
        - User facts appear correctly
        - Nikita's thoughts are natural
        """
        from nikita.context.template_generator import TemplateGenerator

        generator = TemplateGenerator(mock_session)

        # Mock all repository methods
        with patch.object(generator._user_repo, "get", return_value=rich_user):
            with patch.object(
                generator._summary_repo, "get_range", return_value=sample_summaries
            ):
                with patch.object(
                    generator._conversation_repo,
                    "get_processed_conversations",
                    side_effect=[
                        [sample_conversations[0]],  # First call: recent conversation
                        sample_conversations,  # Second call: all processed conversations
                    ],
                ):
                    with patch.object(
                        generator._thread_repo,
                        "get_threads_for_prompt",
                        return_value=sample_threads,
                    ):
                        with patch.object(
                            generator._thought_repo,
                            "get_thoughts_for_prompt",
                            return_value=sample_thoughts,
                        ):
                            prompt = await generator.generate_prompt(rich_user.id)

        # Print full prompt for visual verification
        print("\n")
        print("="*80)
        print(" FULL GENERATED SYSTEM PROMPT - VISUAL VERIFICATION")
        print("="*80)
        print(prompt)
        print("="*80)
        print(f" Total length: {len(prompt)} characters (~{len(prompt)//4} tokens)")
        print("="*80)
        print("\n")

        # Basic structural assertions
        assert "=== WHO NIKITA IS ===" in prompt
        assert "=== CURRENT MOMENT ===" in prompt
        assert "=== RELATIONSHIP STATE ===" in prompt
        assert "=== CONVERSATION HISTORY ===" in prompt
        assert "=== KNOWLEDGE & INNER LIFE ===" in prompt
        assert "=== RESPONSE GUIDELINES ===" in prompt

        # Content assertions
        assert "Investment" in prompt  # Chapter 3 name
        assert "deadline" in prompt.lower()  # From threads/summaries
        assert "hiking" in prompt.lower()  # From facts

    @pytest.mark.asyncio
    async def test_convenience_function_generate_system_prompt(
        self,
        mock_session: AsyncMock,
        rich_user: MagicMock,
    ):
        """AC-11b: Convenience function works correctly."""
        from nikita.context.template_generator import generate_system_prompt

        with patch(
            "nikita.context.template_generator.TemplateGenerator"
        ) as MockGenerator:
            mock_instance = MagicMock()
            mock_instance.generate_prompt = AsyncMock(
                return_value="Mock system prompt content"
            )
            MockGenerator.return_value = mock_instance

            result = await generate_system_prompt(mock_session, rich_user.id)

        assert result == "Mock system prompt content"
        MockGenerator.assert_called_once_with(mock_session)
        mock_instance.generate_prompt.assert_called_once_with(rich_user.id)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def basic_user(self) -> MagicMock:
        user = MagicMock(spec=User)
        user.id = uuid4()
        user.chapter = 1
        user.relationship_score = Decimal("50.00")
        user.game_status = "active"
        user.last_interaction_at = None  # Never interacted
        return user

    @pytest.mark.asyncio
    async def test_user_with_no_last_interaction(
        self, mock_session: AsyncMock, basic_user: MagicMock
    ):
        """Edge case: User has never interacted before."""
        from nikita.context.template_generator import TemplateGenerator

        generator = TemplateGenerator(mock_session)

        with patch.object(generator._user_repo, "get", return_value=basic_user):
            with patch.object(
                generator._summary_repo, "get_range", return_value=[]
            ):
                with patch.object(
                    generator._conversation_repo,
                    "get_processed_conversations",
                    return_value=[],
                ):
                    with patch.object(
                        generator._thread_repo,
                        "get_threads_for_prompt",
                        return_value={},
                    ):
                        with patch.object(
                            generator._thought_repo,
                            "get_thoughts_for_prompt",
                            return_value={},
                        ):
                            prompt = await generator.generate_prompt(basic_user.id)

        # Should handle gracefully with 0.0 hours since last interaction
        assert "=== WHO NIKITA IS ===" in prompt
        assert len(prompt) > 1000  # Still generates substantial prompt

    @pytest.mark.asyncio
    async def test_empty_context_still_generates_valid_prompt(
        self, mock_session: AsyncMock
    ):
        """Edge case: All optional context is empty."""
        from nikita.context.template_generator import TemplateGenerator

        user = MagicMock(spec=User)
        user.id = uuid4()
        user.chapter = 1
        user.relationship_score = Decimal("50.00")
        user.game_status = "active"
        user.last_interaction_at = datetime.now(UTC) - timedelta(hours=1)

        generator = TemplateGenerator(mock_session)

        with patch.object(generator._user_repo, "get", return_value=user):
            with patch.object(
                generator._summary_repo, "get_range", return_value=[]
            ):
                with patch.object(
                    generator._conversation_repo,
                    "get_processed_conversations",
                    return_value=[],
                ):
                    with patch.object(
                        generator._thread_repo,
                        "get_threads_for_prompt",
                        return_value={},
                    ):
                        with patch.object(
                            generator._thought_repo,
                            "get_thoughts_for_prompt",
                            return_value={},
                        ):
                            prompt = await generator.generate_prompt(user.id)

        print("\n" + "="*60)
        print("MINIMAL CONTEXT PROMPT (no history/threads/thoughts)")
        print("="*60)
        print(prompt)
        print("="*60 + "\n")

        # All 6 layers still present
        assert "=== WHO NIKITA IS ===" in prompt
        assert "=== CURRENT MOMENT ===" in prompt
        assert "=== RELATIONSHIP STATE ===" in prompt
        assert "=== CONVERSATION HISTORY ===" in prompt
        assert "=== KNOWLEDGE & INNER LIFE ===" in prompt
        assert "=== RESPONSE GUIDELINES ===" in prompt
