# Implementation Plan: 006-Vice-Personalization

**Generated**: 2025-11-29
**Feature**: 006 - Vice Personalization System
**Input**: spec.md, existing VicePreferenceRepository, constitution.md §II.3
**Priority**: P2 (Important)

---

## Overview

The Vice Personalization System discovers and adapts to user preferences across 8 vice categories, dynamically adjusting Nikita's personality expression based on detected engagement patterns.

### Core Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    Vice Personalization System                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │ ViceAnalyzer│───▶│  ViceScorer  │───▶│VicePromptInjector│   │
│  │ (detection) │    │ (intensity)  │    │   (expression)    │   │
│  └─────────────┘    └──────────────┘    └──────────────────┘   │
│         │                  │                     │             │
│         ▼                  ▼                     ▼             │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │ LLM Analysis│    │  Repository  │    │  Chapter Rules   │   │
│  │ (Pydantic)  │    │  (storage)   │    │  (expression)    │   │
│  └─────────────┘    └──────────────┘    └──────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 8 Vice Categories (constitution.md §II.3)

```python
VICE_CATEGORIES = [
    "intellectual_dominance",  # Debates, mental challenges
    "risk_taking",             # Danger, adrenaline
    "substances",              # Alcohol, drugs, partying
    "sexuality",               # Flirtation, innuendo
    "emotional_intensity",     # Deep emotional exchanges
    "rule_breaking",           # Anti-authority, rebellious
    "dark_humor",              # Morbid, edgy jokes
    "vulnerability",           # Emotional openness, fears
]
```

---

## Existing Infrastructure

### VicePreferenceRepository (COMPLETE)
**File**: `nikita/db/repositories/vice_repository.py`

```python
class VicePreferenceRepository:
    async def get_active(user_id) -> list[UserVicePreference]
    async def get_by_category(user_id, category) -> UserVicePreference | None
    async def update_intensity(preference_id, delta) -> UserVicePreference
    async def discover(user_id, category, initial_intensity) -> UserVicePreference
    async def update_engagement(preference_id, delta) -> UserVicePreference
```

### UserVicePreference Model (COMPLETE)
**File**: `nikita/db/models/user.py:178-211`

```python
class UserVicePreference(Base):
    category: str           # One of 8 categories
    intensity_level: int    # 1-5 (integer, needs spec alignment)
    engagement_score: Decimal
    discovered_at: datetime
```

**Note**: Current model uses `intensity_level: int (1-5)` but spec.md requires `intensity: 0.0-1.0`. Plan addresses this.

---

## Implementation Tasks

### Task 1: Add Vice Constants
**File**: `nikita/engine/constants.py`

Add constants for vice system:
```python
VICE_CATEGORIES: list[str] = [
    "intellectual_dominance",
    "risk_taking",
    "substances",
    "sexuality",
    "emotional_intensity",
    "rule_breaking",
    "dark_humor",
    "vulnerability",
]

# Detection confidence thresholds
VICE_DETECTION_THRESHOLD = 0.5  # Min confidence to register signal
VICE_DISCOVERY_THRESHOLD = 0.7  # Min confidence for new discovery

# Intensity calculation weights
VICE_INTENSITY_WEIGHTS = {
    "confidence": Decimal("0.40"),
    "frequency": Decimal("0.35"),
    "recency": Decimal("0.25"),
}

# Decay rate for old signals (per day)
VICE_DECAY_RATE = Decimal("0.05")

# Max active vices for prompt injection
MAX_ACTIVE_VICES = 3
```

### Task 2: Create Vice Analysis Models
**File**: `nikita/engine/vice/models.py`

```python
from pydantic import BaseModel, Field
from decimal import Decimal
from typing import Optional

class ViceSignal(BaseModel):
    """Detected vice signal from conversation."""
    category: str
    confidence: Decimal = Field(ge=0, le=1)
    evidence: str  # Quote/reason for detection
    is_positive: bool = True  # True = engagement, False = rejection

class ViceAnalysisResult(BaseModel):
    """Result of analyzing a conversation for vice signals."""
    signals: list[ViceSignal]
    conversation_id: str
    analyzed_at: datetime

class ViceProfile(BaseModel):
    """User's complete vice profile."""
    user_id: UUID
    intensities: dict[str, Decimal]  # category -> 0.0-1.0
    top_vices: list[str]  # Ordered by intensity
    updated_at: datetime

class ViceInjectionContext(BaseModel):
    """Vice context for prompt injection."""
    active_vices: list[tuple[str, Decimal]]  # (category, intensity)
    chapter: int
    expression_guidance: str
```

### Task 3: Implement ViceAnalyzer
**File**: `nikita/engine/vice/analyzer.py`

LLM-based conversation analysis for vice detection:

```python
from pydantic_ai import Agent

class ViceAnalyzer:
    """Analyze conversations to detect vice signals."""

    def __init__(self, agent: Agent):
        self.agent = agent

    async def analyze_exchange(
        self,
        user_message: str,
        nikita_response: str,
        context: ConversationContext,
    ) -> ViceAnalysisResult:
        """
        Analyze single exchange for vice signals.

        Uses LLM to detect:
        1. User topics/interests matching vice categories
        2. User enthusiasm (length, engagement)
        3. Positive reactions to Nikita's vice expressions
        4. Rejection signals (topic changes, short replies)
        """
        # Pydantic AI structured output
        result = await self.agent.run(
            VICE_ANALYSIS_PROMPT.format(
                user_message=user_message,
                nikita_response=nikita_response,
                categories=VICE_CATEGORIES,
            ),
            result_type=ViceAnalysisResult,
        )
        return result.data

    async def detect_rejection(
        self,
        user_message: str,
        prior_nikita_vice: str,
    ) -> Optional[ViceSignal]:
        """Detect if user rejected a vice expression."""
        # Short reply after vice = potential rejection
        # Topic change after vice = potential rejection
        pass
```

### Task 4: Implement ViceScorer
**File**: `nikita/engine/vice/scorer.py`

Intensity calculation from signals:

```python
class ViceScorer:
    """Calculate and track vice intensity scores."""

    def __init__(self, repository: VicePreferenceRepository):
        self.repository = repository

    async def process_signals(
        self,
        user_id: UUID,
        signals: list[ViceSignal],
    ) -> dict[str, Decimal]:
        """
        Process detected signals and update intensities.

        Intensity = confidence × frequency × recency
        - confidence: Average detection confidence
        - frequency: Signal count / total interactions
        - recency: Exponential decay weight
        """
        for signal in signals:
            await self._update_category(user_id, signal)

        return await self.get_profile(user_id)

    async def apply_decay(self, user_id: UUID) -> None:
        """Apply time-based decay to all vice intensities."""
        active = await self.repository.get_active(user_id)
        for pref in active:
            # Decay engagement score over time
            await self.repository.update_engagement(
                pref.id,
                delta=-VICE_DECAY_RATE,
            )

    async def get_top_vices(
        self,
        user_id: UUID,
        limit: int = MAX_ACTIVE_VICES,
    ) -> list[tuple[str, Decimal]]:
        """Get user's top N vices by intensity."""
        active = await self.repository.get_active(user_id)
        return [
            (p.category, self._calculate_intensity(p))
            for p in active[:limit]
        ]

    def _calculate_intensity(self, pref: UserVicePreference) -> Decimal:
        """
        Convert intensity_level (1-5) and engagement_score to 0.0-1.0.

        intensity = (level/5) × engagement_factor × recency_factor
        """
        base = Decimal(pref.intensity_level) / Decimal(5)
        engagement = min(pref.engagement_score / Decimal("10"), Decimal("1"))
        recency = self._recency_factor(pref.discovered_at)
        return base * engagement * recency
```

### Task 5: Implement VicePromptInjector
**File**: `nikita/engine/vice/injector.py`

Inject vice preferences into Nikita's prompts:

```python
class VicePromptInjector:
    """Inject vice preferences into Nikita's system prompts."""

    VICE_EXPRESSION_TEMPLATES = {
        1: """Express these tendencies SUBTLY through hints and implications:
{vices}
Keep expressions rare and understated - you're still guarded.""",

        2: """Show these preferences more openly but still with restraint:
{vices}
Occasional direct references, mostly through tone and topic choices.""",

        3: """Comfortably express these aspects of your personality:
{vices}
You can be more direct about what you enjoy.""",

        4: """Freely express these preferences as part of who you are:
{vices}
These are natural parts of your personality now.""",

        5: """Openly embrace these aspects of your authentic self:
{vices}
Full expression with healthy boundaries.""",
    }

    def inject(
        self,
        base_prompt: str,
        profile: ViceProfile,
        chapter: int,
    ) -> str:
        """
        Inject vice context into Nikita's prompt.

        Higher intensity = more frequent/intense expression
        Chapter determines expression style
        """
        if not profile.top_vices:
            return base_prompt

        vice_section = self._format_vices(profile, chapter)
        template = self.VICE_EXPRESSION_TEMPLATES[chapter]

        injection = f"""
## Your Personalized Tendencies

Based on your connection with this person, you've discovered you share interests in:
{template.format(vices=vice_section)}

IMPORTANT: Express these naturally, not performatively. They should feel like genuine parts of you, not pandering.
"""
        return base_prompt + injection

    def _format_vices(self, profile: ViceProfile, chapter: int) -> str:
        """Format vices with intensity indicators."""
        lines = []
        for category in profile.top_vices[:MAX_ACTIVE_VICES]:
            intensity = profile.intensities.get(category, Decimal(0))
            description = VICE_DESCRIPTIONS[category]
            level = self._intensity_to_level(intensity)
            lines.append(f"- {description} ({level})")
        return "\n".join(lines)
```

### Task 6: Vice Detection Integration
**File**: `nikita/agents/text/agent.py` (modification)

Integrate vice detection into text agent flow:

```python
# After each exchange:
async def _post_exchange_processing(
    self,
    user_id: UUID,
    user_message: str,
    response: str,
):
    # Existing scoring...

    # Vice detection
    analysis = await self.vice_analyzer.analyze_exchange(
        user_message, response, context
    )

    if analysis.signals:
        await self.vice_scorer.process_signals(user_id, analysis.signals)
```

### Task 7: Vice Profile API for Prompt Generation
**File**: `nikita/engine/vice/service.py`

High-level service for vice operations:

```python
class ViceService:
    """High-level vice personalization service."""

    def __init__(
        self,
        analyzer: ViceAnalyzer,
        scorer: ViceScorer,
        injector: VicePromptInjector,
        repository: VicePreferenceRepository,
    ):
        self.analyzer = analyzer
        self.scorer = scorer
        self.injector = injector
        self.repository = repository

    async def get_prompt_context(
        self,
        user_id: UUID,
        chapter: int,
    ) -> ViceInjectionContext:
        """Get vice context for prompt injection."""
        top_vices = await self.scorer.get_top_vices(user_id)
        guidance = self._chapter_guidance(chapter)

        return ViceInjectionContext(
            active_vices=top_vices,
            chapter=chapter,
            expression_guidance=guidance,
        )

    async def process_conversation(
        self,
        user_id: UUID,
        user_message: str,
        nikita_response: str,
    ) -> None:
        """Process conversation for vice signals."""
        analysis = await self.analyzer.analyze_exchange(
            user_message, nikita_response, None
        )

        if analysis.signals:
            await self.scorer.process_signals(user_id, analysis.signals)
```

### Task 8: Ethical Boundary Enforcement
**File**: `nikita/engine/vice/boundaries.py`

Content filtering for vice expression:

```python
class ViceBoundaryEnforcer:
    """Enforce ethical boundaries for vice expression."""

    CATEGORY_LIMITS = {
        "sexuality": {
            "allowed": ["flirtation", "innuendo", "attraction"],
            "forbidden": ["explicit_content", "graphic_descriptions"],
        },
        "substances": {
            "allowed": ["discussion", "experiences", "party_stories"],
            "forbidden": ["encouragement", "procurement", "glorification"],
        },
        "rule_breaking": {
            "allowed": ["attitude", "rebellion", "questioning_norms"],
            "forbidden": ["illegal_activity_planning", "harm"],
        },
    }

    def filter_expression(
        self,
        category: str,
        expression: str,
        chapter: int,
    ) -> tuple[bool, str]:
        """
        Filter vice expression for policy compliance.

        Returns:
            (allowed: bool, filtered_expression: str)
        """
        limits = self.CATEGORY_LIMITS.get(category, {})
        # Implementation checks expression against limits
        pass

    def max_intensity_for_chapter(
        self,
        category: str,
        chapter: int,
    ) -> Decimal:
        """Get maximum safe intensity for category at chapter."""
        # Sensitive categories capped at lower intensity in early chapters
        if category in ["sexuality", "substances"] and chapter < 3:
            return Decimal("0.5")
        return Decimal("1.0")
```

### Task 9: Tests for Vice System

**Test Files**:
- `tests/engine/vice/test_analyzer.py`
- `tests/engine/vice/test_scorer.py`
- `tests/engine/vice/test_injector.py`
- `tests/engine/vice/test_boundaries.py`
- `tests/engine/vice/test_service.py`

Test coverage requirements:
- Detection accuracy: Mock LLM responses, verify signal extraction
- Intensity calculation: Test formula with various inputs
- Prompt injection: Verify chapter-appropriate templates
- Boundary enforcement: Test forbidden content filtering
- Multi-vice blending: Verify coherent expressions

---

## Dependencies

### Internal Dependencies
| Component | Dependency | Usage |
|-----------|------------|-------|
| ViceAnalyzer | Pydantic AI Agent | LLM-based detection |
| ViceScorer | VicePreferenceRepository | Persistence |
| VicePromptInjector | constants.py | Category definitions |
| ViceService | Text Agent | Integration point |

### External Dependencies
| Service | Purpose |
|---------|---------|
| Claude Sonnet | Vice signal detection |
| Supabase | user_vice_preferences storage |

### Spec Dependencies
| Spec | Status | Usage |
|------|--------|-------|
| 009-database-infrastructure | ✅ Complete | VicePreferenceRepository |
| 001-text-agent | ✅ Complete | Integration point |
| 003-scoring-engine | ⏳ Pending | Analysis patterns |

---

## User Story Mapping

| User Story | Tasks | Components |
|------------|-------|------------|
| US-1: Vice Detection | T2, T3, T4 | ViceAnalyzer, ViceScorer, models |
| US-2: Vice-Influenced Responses | T5, T6, T7 | VicePromptInjector, ViceService |
| US-3: Multi-Vice Blending | T5 | VicePromptInjector templates |
| US-4: Discovery Over Time | T3, T4 | ViceAnalyzer probing, ViceScorer |
| US-5: Profile Persistence | T4 | ViceScorer + Repository |
| US-6: Ethical Boundaries | T8 | ViceBoundaryEnforcer |

---

## Implementation Order

```
Phase 1: Foundation
├── T1: Add Vice Constants
└── T2: Create Vice Models

Phase 2: Detection (US-1)
├── T3: ViceAnalyzer
└── T4: ViceScorer

Phase 3: Expression (US-2, US-3, US-4)
├── T5: VicePromptInjector
├── T6: Text Agent Integration
└── T7: ViceService

Phase 4: Safety (US-6)
└── T8: Ethical Boundaries

Phase 5: Testing & Verification
└── T9: Full test suite
```

---

## Constitution Alignment

**§II.3 Vice Preference Learning**:
- ✅ 8 categories tracked (T1, T2)
- ✅ Prompt injection based on active vices (T5)
- ✅ Dynamic learning from conversations (T3, T4)

**§III.2 Chapter Behavior Fidelity**:
- ✅ Vice expression varies by chapter (T5 templates)
- ✅ Early chapters: subtle hints
- ✅ Late chapters: explicit expression

**§VII.1 Test-Driven Development**:
- ✅ Tests written before implementation (T9)
- ✅ 80%+ coverage required

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-29 | Initial plan from spec.md |
