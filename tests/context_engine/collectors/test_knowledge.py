"""Tests for KnowledgeCollector (Spec 039 Phase 1)."""

import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nikita.context_engine.collectors.knowledge import (
    KnowledgeCollector,
    KnowledgeData,
    PersonaData,
    ChapterBehavior,
    CONFIG_DATA_DIR,
    PROMPTS_DIR,
)
from nikita.context_engine.collectors.base import CollectorContext


@pytest.fixture
def mock_session():
    """Create mock async session."""
    session = MagicMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def collector_context(mock_session):
    """Create collector context."""
    return CollectorContext(
        session=mock_session,
        user_id=uuid.uuid4(),
    )


@pytest.fixture
def mock_user():
    """Create mock User model."""
    user = MagicMock()
    user.chapter = 2
    return user


class TestPersonaData:
    """Tests for PersonaData model."""

    def test_default_values(self):
        """Test default persona values."""
        data = PersonaData()
        assert data.name == "Nikita"
        assert data.full_name == "Nikita Volkov"
        assert data.age == 27
        assert data.occupation == "Independent security researcher"
        assert data.location == "Berlin, Germany"
        assert data.traits_summary == ""
        assert data.attachment_style == ""
        assert data.core_wounds == []
        assert data.defense_mechanisms == []
        assert data.values == []
        assert data.speaking_style == {}

    def test_with_custom_values(self):
        """Test with custom persona values."""
        data = PersonaData(
            name="Test",
            age=30,
            traits_summary="Smart and witty",
            core_wounds=["Abandonment", "Trust issues"],
            values=["Honesty", "Independence"],
        )
        assert data.name == "Test"
        assert data.age == 30
        assert len(data.core_wounds) == 2
        assert "Independence" in data.values


class TestChapterBehavior:
    """Tests for ChapterBehavior model."""

    def test_default_values(self):
        """Test default chapter behavior."""
        behavior = ChapterBehavior()
        assert behavior.chapter == 1
        assert behavior.name == "Curiosity"
        assert behavior.behavior_summary == ""
        assert behavior.flirtiness_level == 0.7
        assert behavior.testing_level == 0.3
        assert behavior.vulnerability_allowed == 0.2
        assert behavior.key_behaviors == []

    def test_chapter_validation(self):
        """Test chapter value validation (1-5)."""
        behavior = ChapterBehavior(chapter=5)
        assert behavior.chapter == 5

    def test_level_validation(self):
        """Test level values are between 0 and 1."""
        behavior = ChapterBehavior(
            flirtiness_level=0.9,
            testing_level=0.5,
            vulnerability_allowed=0.8,
        )
        assert behavior.flirtiness_level == 0.9
        assert behavior.testing_level == 0.5
        assert behavior.vulnerability_allowed == 0.8


class TestKnowledgeData:
    """Tests for KnowledgeData model."""

    def test_default_structure(self):
        """Test KnowledgeData with default nested models."""
        data = KnowledgeData(
            persona=PersonaData(),
            chapter_behavior=ChapterBehavior(),
        )
        assert data.persona.name == "Nikita"
        assert data.chapter_behavior.chapter == 1
        assert data.persona_canon == ""
        assert data.chapter_behavior_text == ""
        assert data.psychological_guidance == ""


class TestKnowledgeCollector:
    """Tests for KnowledgeCollector."""

    def test_collector_name(self):
        """Test collector name is 'knowledge'."""
        collector = KnowledgeCollector()
        assert collector.name == "knowledge"

    def test_collector_timeout(self):
        """Test timeout is 2s (fast for file I/O)."""
        collector = KnowledgeCollector()
        assert collector.timeout_seconds == 2.0

    def test_max_retries(self):
        """Test max retries is 1 (files rarely fail transiently)."""
        collector = KnowledgeCollector()
        assert collector.max_retries == 1

    def test_config_data_dir_exists(self):
        """Test CONFIG_DATA_DIR points to valid path."""
        assert CONFIG_DATA_DIR.exists()

    def test_prompts_dir_exists(self):
        """Test PROMPTS_DIR points to valid path."""
        assert PROMPTS_DIR.exists()

    def test_get_chapter_behavior_all_chapters(self):
        """Test chapter behavior configs for chapters 1-5."""
        collector = KnowledgeCollector()

        # Chapter 1: Curiosity
        ch1 = collector._get_chapter_behavior(1)
        assert ch1.name == "Curiosity"
        assert ch1.flirtiness_level == 0.8
        assert "Flirty and playful" in ch1.key_behaviors

        # Chapter 2: Testing
        ch2 = collector._get_chapter_behavior(2)
        assert ch2.name == "Testing"
        assert ch2.testing_level == 0.7
        assert "Testing boundaries" in ch2.key_behaviors

        # Chapter 3: Depth
        ch3 = collector._get_chapter_behavior(3)
        assert ch3.name == "Depth"
        assert ch3.vulnerability_allowed == 0.5

        # Chapter 4: Authenticity
        ch4 = collector._get_chapter_behavior(4)
        assert ch4.name == "Authenticity"
        assert ch4.vulnerability_allowed == 0.8

        # Chapter 5: Commitment
        ch5 = collector._get_chapter_behavior(5)
        assert ch5.name == "Commitment"
        assert ch5.testing_level == 0.2
        assert ch5.vulnerability_allowed == 0.9

    def test_get_chapter_behavior_invalid_defaults_to_1(self):
        """Test invalid chapter defaults to chapter 1 behavior."""
        collector = KnowledgeCollector()
        behavior = collector._get_chapter_behavior(99)
        assert behavior.name == "Curiosity"
        assert behavior.chapter == 1

    def test_build_persona_canon(self):
        """Test persona canon text generation."""
        collector = KnowledgeCollector()
        persona = PersonaData(
            full_name="Nikita Volkov",
            age=27,
            occupation="Security researcher",
            location="Berlin",
            traits_summary="- Smart: Very intelligent",
            core_wounds=["Abandonment: Fear of being left"],
            values=["Honesty", "Independence"],
        )

        canon = collector._build_persona_canon(persona)

        assert "Nikita Volkov" in canon
        assert "27" in canon
        assert "Berlin" in canon
        assert "Smart: Very intelligent" in canon
        assert "Abandonment" in canon
        assert "Honesty" in canon

    def test_build_chapter_text(self):
        """Test chapter behavior text generation."""
        collector = KnowledgeCollector()
        behavior = ChapterBehavior(
            chapter=3,
            name="Depth",
            behavior_summary="Deep emotional exchanges",
            flirtiness_level=0.5,
            testing_level=0.6,
            vulnerability_allowed=0.5,
            key_behaviors=["Sharing deeper thoughts", "Trust testing"],
        )

        text = collector._build_chapter_text(behavior)

        assert "Chapter 3: Depth" in text
        assert "Deep emotional exchanges" in text
        assert "Sharing deeper thoughts" in text
        assert "Flirtiness: 50%" in text
        assert "Testing: 60%" in text
        assert "Vulnerability allowed: 50%" in text

    def test_build_traits_summary(self):
        """Test traits summary building from dict."""
        collector = KnowledgeCollector()
        traits = {
            "intelligence": {"description": "Sharp analytical mind"},
            "humor": {"description": "Dark, witty humor"},
            "simple_trait": "Just a string",
        }

        summary = collector._build_traits_summary(traits)

        assert "Intelligence: Sharp analytical mind" in summary
        assert "Humor: Dark, witty humor" in summary
        assert "Simple_Trait: Just a string" in summary

    @pytest.mark.asyncio
    async def test_collect_loads_persona_and_chapter(self, collector_context, mock_user):
        """Test collect() loads persona and chapter behavior."""
        collector = KnowledgeCollector()

        mock_user_repo = AsyncMock()
        mock_user_repo.get.return_value = mock_user

        with patch(
            "nikita.db.repositories.user_repository.UserRepository",
            return_value=mock_user_repo,
        ):
            result = await collector.collect(collector_context)

        assert isinstance(result, KnowledgeData)
        assert result.persona.name == "Nikita"
        assert result.chapter_behavior.chapter == 2
        assert result.chapter_behavior.name == "Testing"
        assert "Chapter 2" in result.chapter_behavior_text

    @pytest.mark.asyncio
    async def test_collect_defaults_to_chapter_1_if_no_user(self, collector_context):
        """Test collect() defaults to chapter 1 if user not found."""
        collector = KnowledgeCollector()

        mock_user_repo = AsyncMock()
        mock_user_repo.get.return_value = None

        with patch(
            "nikita.db.repositories.user_repository.UserRepository",
            return_value=mock_user_repo,
        ):
            result = await collector.collect(collector_context)

        assert result.chapter_behavior.chapter == 1
        assert result.chapter_behavior.name == "Curiosity"

    def test_load_yaml_caches_result(self):
        """Test YAML loading uses cache."""
        collector = KnowledgeCollector()

        # Clear cache first
        collector._cache = {}

        # Load same file twice
        data1 = collector._load_yaml(PROMPTS_DIR / "base_personality.yaml")
        data2 = collector._load_yaml(PROMPTS_DIR / "base_personality.yaml")

        # Both should be the same cached object
        assert data1 is data2
        assert str(PROMPTS_DIR / "base_personality.yaml") in collector._cache

    def test_load_yaml_handles_missing_file(self):
        """Test YAML loading handles missing file gracefully."""
        collector = KnowledgeCollector()
        collector._cache = {}

        result = collector._load_yaml(Path("/nonexistent/file.yaml"))
        assert result == {}

    def test_get_fallback(self):
        """Test fallback returns minimal valid KnowledgeData."""
        collector = KnowledgeCollector()
        fallback = collector.get_fallback()

        assert isinstance(fallback, KnowledgeData)
        assert fallback.persona.name == "Nikita"
        assert "Nikita Volkov" in fallback.persona_canon
        assert fallback.chapter_behavior.chapter == 1
        assert "Chapter 1" in fallback.chapter_behavior_text
        assert fallback.psychological_guidance == ""
