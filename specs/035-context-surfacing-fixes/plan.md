# Implementation Plan: Spec 035 Context Surfacing Fixes

**Spec**: [spec.md](./spec.md)
**Status**: Ready for Implementation
**Estimated Effort**: 14 hours

---

## Executive Summary

This plan wires existing `social_generator.py` and `arcs.py` modules into the production pipeline, adds voice prompt observability, and ensures comprehensive test coverage.

**Critical Path**:
1. Database migrations (blocking all integration work)
2. Social Circle + Narrative Arc integration (parallel after migrations)
3. Voice logging + Tests (parallel after integration)
4. E2E verification (final)

---

## Phase 1: Database & Models (2 hours)

### P1.1: Create Migrations via Supabase MCP [P]

**Tasks**:
1. Create `user_social_circles` table (FR-001)
2. Create `user_narrative_arcs` table (FR-002)
3. Add `platform` column to `generated_prompts` table (FR-010)

**SQL for user_social_circles**:
```sql
CREATE TABLE user_social_circles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    friend_name TEXT NOT NULL,
    friend_role TEXT NOT NULL,
    age INTEGER,
    occupation TEXT,
    personality TEXT,
    relationship_to_nikita TEXT,
    storyline_potential JSONB DEFAULT '[]',
    trigger_conditions JSONB DEFAULT '[]',
    adapted_traits JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, friend_name)
);

CREATE INDEX idx_social_circles_user_id ON user_social_circles(user_id);
CREATE INDEX idx_social_circles_active ON user_social_circles(user_id, is_active) WHERE is_active = true;
```

**SQL for user_narrative_arcs**:
```sql
CREATE TABLE user_narrative_arcs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    template_name TEXT NOT NULL,
    category TEXT NOT NULL,
    current_stage TEXT NOT NULL DEFAULT 'setup',
    stage_progress INTEGER DEFAULT 0,
    conversations_in_arc INTEGER DEFAULT 0,
    max_conversations INTEGER DEFAULT 5,
    current_description TEXT,
    involved_characters JSONB DEFAULT '[]',
    emotional_impact JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_narrative_arcs_user_id ON user_narrative_arcs(user_id);
CREATE INDEX idx_narrative_arcs_active ON user_narrative_arcs(user_id, is_active) WHERE is_active = true;
```

**SQL for platform column**:
```sql
ALTER TABLE generated_prompts ADD COLUMN platform VARCHAR(10) DEFAULT 'text';
UPDATE generated_prompts SET platform = 'text' WHERE platform IS NULL;
```

### P1.2: Create SQLAlchemy Models [P]

**File**: `nikita/db/models/social_circle.py`
```python
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from nikita.db.models.base import Base

class UserSocialCircle(Base):
    __tablename__ = "user_social_circles"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    friend_name: Mapped[str] = mapped_column(String(100), nullable=False)
    friend_role: Mapped[str] = mapped_column(String(50), nullable=False)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    occupation: Mapped[str | None] = mapped_column(String(100), nullable=True)
    personality: Mapped[str | None] = mapped_column(Text, nullable=True)
    relationship_to_nikita: Mapped[str | None] = mapped_column(Text, nullable=True)
    storyline_potential: Mapped[list] = mapped_column(JSONB, default=list)
    trigger_conditions: Mapped[list] = mapped_column(JSONB, default=list)
    adapted_traits: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
```

**File**: `nikita/db/models/narrative_arc.py`
```python
class UserNarrativeArc(Base):
    __tablename__ = "user_narrative_arcs"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    template_name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    current_stage: Mapped[str] = mapped_column(String(20), default="setup")
    stage_progress: Mapped[int] = mapped_column(Integer, default=0)
    conversations_in_arc: Mapped[int] = mapped_column(Integer, default=0)
    max_conversations: Mapped[int] = mapped_column(Integer, default=5)
    current_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    involved_characters: Mapped[list] = mapped_column(JSONB, default=list)
    emotional_impact: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    started_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
```

### P1.3: Create Repository Classes [P]

**File**: `nikita/db/repositories/social_circle_repository.py`
- `create_circle_for_user(user_id, friends)` - Bulk insert friends
- `get_circle(user_id)` - Get all friends
- `get_active_friends(user_id)` - Get active friends only

**File**: `nikita/db/repositories/narrative_arc_repository.py`
- `create_arc(user_id, template)` - Create from template
- `get_active_arcs(user_id)` - Get active arcs (limit 2)
- `advance_arc(arc_id, new_stage)` - Update stage
- `resolve_arc(arc_id)` - Set is_active=False, resolved_at
- `increment_conversation_count(arc_id)` - Increment counter

---

## Phase 2: Social Circle Integration (3 hours)

### P2.1: Wire to Onboarding Handoff (FR-005)

**File**: `nikita/onboarding/handoff.py`

**Location**: After profile creation in `complete_handoff()` or equivalent

```python
from nikita.life_simulation import generate_social_circle_for_user
from nikita.db.repositories.social_circle_repository import SocialCircleRepository

async def complete_handoff(self, user_id: UUID, profile: UserOnboardingProfile) -> HandoffResult:
    # ... existing code ...

    # NEW: Generate personalized social circle
    try:
        social_circle = generate_social_circle_for_user(
            user_id=str(user_id),
            location=profile.location or "Berlin",
            hobbies=profile.hobbies or [],
            job=profile.occupation or "",
            meeting_context=profile.how_we_met or "party"
        )

        # Store in database
        repo = SocialCircleRepository(self.session)
        await repo.create_circle_for_user(user_id, social_circle.characters)
        logger.info(f"Created social circle with {len(social_circle.characters)} characters for user {user_id}")
    except Exception as e:
        logger.warning(f"Failed to create social circle for user {user_id}: {e}")
        # Non-blocking - continue with handoff

    # ... rest of handoff ...
```

### P2.2: Add to MetaPromptService._load_context() (FR-007)

**File**: `nikita/meta_prompts/service.py`

**Location**: TIER 5: PERSONALIZATION section

```python
async def _load_context(self, user_id: UUID) -> dict[str, Any]:
    # ... existing code ...

    # TIER 5: PERSONALIZATION
    # ... existing personalization loading ...

    # NEW: Load social circle
    social_circle = await self._get_social_circle(user_id)
    context["social_circle"] = social_circle
    context["social_circle_formatted"] = self._format_social_circle(social_circle)

    # ... rest of context loading ...

async def _get_social_circle(self, user_id: UUID) -> list[dict]:
    """Load user's social circle from database."""
    repo = SocialCircleRepository(self.session)
    friends = await repo.get_active_friends(user_id)
    return [
        {
            "name": f.friend_name,
            "role": f.friend_role,
            "personality": f.personality,
            "relationship": f.relationship_to_nikita,
        }
        for f in friends[:5]  # Limit for token budget
    ]

def _format_social_circle(self, circle: list[dict]) -> str:
    """Format social circle for prompt injection."""
    if not circle:
        return "No specific friends to mention today."

    lines = []
    for friend in circle:
        lines.append(f"- **{friend['name']}** ({friend['role']}): {friend['personality'][:100]}")
    return "\n".join(lines)
```

### P2.3: Update system_prompt.meta.md Template (FR-008)

**File**: `nikita/meta_prompts/templates/system_prompt.meta.md`

**Add section** (after personality, before memory):

```markdown
## NIKITA'S SOCIAL WORLD

These are your close friends, family, and connections. Reference them naturally in conversation when relevant:

{% if social_circle_formatted %}
{{ social_circle_formatted }}
{% else %}
Your social world is rich but private - share naturally as trust builds.
{% endif %}

Remember:
- Friends are real people with ongoing lives
- Reference them when topics naturally arise
- Share friend drama when appropriate for the relationship stage
- Don't force mentions - let them come up organically
```

### P2.4: Write Social Circle Tests

**File**: `tests/life_simulation/test_social_generator.py`

15+ tests covering:
- Core character generation
- Location adaptation (Berlin, NYC, small city)
- Hobby adaptation (tech, creative, sports)
- Job adaptation (finance, tech, creative)
- Meeting context integration
- Character count (5-8)
- Role coverage
- Serialization

---

## Phase 3: Narrative Arc Integration (4 hours)

### P3.1: Add _update_narrative_arcs() to PostProcessor (FR-006)

**File**: `nikita/context/post_processor.py`

**Location**: After `_analyze_psychology()` stage (~line 225)

```python
from nikita.life_simulation.arcs import get_arc_system
from nikita.db.repositories.narrative_arc_repository import NarrativeArcRepository

async def process(self, conversation: Conversation) -> PostProcessingResult:
    # ... existing stages ...

    # Stage 2.5: Analyze psychology (existing)
    psych_insight, rel_health = await self._analyze_psychology(...)

    # Stage 2.6: Update narrative arcs (NEW)
    arc_updates = await self._update_narrative_arcs(
        user_id=conversation.user_id,
        vulnerability_level=self._get_vulnerability_level(conversation),
        conversation_topics=extraction.topics if extraction else [],
        conversation_dynamics=rel_health,
    )
    result.arc_updates = arc_updates

    # ... rest of processing ...

async def _update_narrative_arcs(
    self,
    user_id: UUID,
    vulnerability_level: int,
    conversation_topics: list[str],
    conversation_dynamics: Any,
) -> dict:
    """Stage 2.6: Update narrative arcs based on conversation."""
    arc_system = get_arc_system()
    arc_repo = NarrativeArcRepository(self.session)

    # Get active arcs
    active_arcs = await arc_repo.get_active_arcs(user_id)

    # Check if should start new arc (max 2 active)
    new_arc = None
    if len(active_arcs) < 2:
        template = arc_system.select_template(
            vulnerability_level=vulnerability_level,
            recent_topics=conversation_topics,
        )
        if template and self._should_start_arc(template, active_arcs):
            new_arc = await arc_repo.create_arc(user_id, template)
            active_arcs.append(new_arc)
            logger.info(f"Started new arc '{template.name}' for user {user_id}")

    # Progress existing arcs
    for arc in active_arcs:
        await arc_repo.increment_conversation_count(arc.id)
        if arc.should_advance():
            arc.advance_stage()
            await arc_repo.advance_arc(arc.id, arc.stage)
            logger.info(f"Advanced arc {arc.id} to stage {arc.stage}")

    return {
        "active_arcs": len(active_arcs),
        "new_arc": new_arc.template_name if new_arc else None,
        "advanced": [a.id for a in active_arcs if a.stage != "setup"],
    }

def _should_start_arc(self, template, active_arcs: list) -> bool:
    """Check if we should start this arc."""
    # Don't start if similar category already active
    active_categories = {a.category for a in active_arcs}
    if template.category.value in active_categories:
        return False
    # Random chance (30% per conversation)
    import random
    return random.random() < 0.30
```

### P3.2: Add Arc Context to MetaPromptService._load_context() (FR-007)

**File**: `nikita/meta_prompts/service.py`

```python
async def _load_context(self, user_id: UUID) -> dict[str, Any]:
    # ... existing code ...

    # TIER 5: PERSONALIZATION
    # ... social circle loading ...

    # NEW: Load narrative arcs
    narrative_arcs = await self._get_active_arcs(user_id)
    context["narrative_arcs"] = narrative_arcs
    context["narrative_arcs_formatted"] = self._format_narrative_arcs(narrative_arcs)

    # ... rest of context loading ...

async def _get_active_arcs(self, user_id: UUID) -> list[dict]:
    """Load user's active narrative arcs."""
    repo = NarrativeArcRepository(self.session)
    arcs = await repo.get_active_arcs(user_id)
    return [
        {
            "name": a.template_name,
            "category": a.category,
            "stage": a.current_stage,
            "description": a.current_description,
            "characters": a.involved_characters,
        }
        for a in arcs
    ]

def _format_narrative_arcs(self, arcs: list[dict]) -> str:
    """Format narrative arcs for prompt injection."""
    if not arcs:
        return "No active storylines right now."

    lines = []
    for arc in arcs:
        stage_emoji = {"setup": "🌱", "rising": "📈", "climax": "⚡", "falling": "📉", "resolved": "✅"}
        emoji = stage_emoji.get(arc["stage"], "📖")
        lines.append(f"- {emoji} **{arc['name']}** ({arc['stage']}): {arc['description'][:80]}...")
    return "\n".join(lines)
```

### P3.3: Update system_prompt.meta.md Template (FR-008)

**Add section** (after social world):

```markdown
## ONGOING STORYLINES

These are multi-conversation arcs you're experiencing. Weave them naturally:

{% if narrative_arcs_formatted %}
{{ narrative_arcs_formatted }}
{% else %}
Life is flowing smoothly - no major drama right now.
{% endif %}

Remember:
- Arcs progress over multiple conversations
- Don't resolve arcs in a single message
- Build tension gradually for climax stages
- Reference arc characters from your social circle
```

### P3.4: Write Narrative Arc Tests

**File**: `tests/life_simulation/test_arcs.py`

20+ tests covering:
- Arc system singleton
- Template selection by vulnerability level (0, 3, 5)
- Template selection by topic (work, friend, family)
- Stage progression (all 5 stages)
- should_advance logic
- Max duration enforcement
- Resolution timestamp
- Max 2 active arcs
- Context formatting
- Serialization
- Category filtering
- Character involvement
- Emotional impact values

---

## Phase 4: Voice Logging & Final Tests (3 hours)

### P4.1: Add Voice Prompt Logging (FR-009)

**File**: `nikita/agents/voice/context.py`

**Location**: In `ConversationConfigBuilder.build_config()` or equivalent

```python
async def build_config(self, user: User, ...) -> dict:
    # ... existing code generating prompt ...

    # Generate personalized prompt
    generated_prompt = await self.meta_service.generate_system_prompt(
        user_id=user.id,
        # ... other params ...
    )

    # NEW: Log voice prompt to database
    generated_prompt.platform = "voice"  # Mark as voice
    self.session.add(generated_prompt)
    await self.session.commit()

    # Store reference for admin visibility
    self.generated_prompt_id = generated_prompt.id
    logger.info(f"Logged voice prompt {generated_prompt.id} for user {user.id}")

    # ... rest of config building ...
```

### P4.2: Add Platform Field Migration (FR-010)

Already included in P1.1 migrations.

### P4.3: Write Integration Tests

**File**: `tests/integration/test_context_surfacing_e2e.py`

```python
class TestContextSurfacingE2E:
    async def test_handoff_creates_social_circle(self):
        """Verify social circle created on handoff."""

    async def test_post_processor_updates_arcs(self):
        """Verify arcs updated after conversation."""

    async def test_social_circle_in_generated_prompt(self):
        """Verify social circle section in prompt."""

    async def test_arcs_in_generated_prompt(self):
        """Verify arc section in prompt."""

    async def test_voice_prompt_logged_with_platform(self):
        """Verify voice prompts have platform='voice'."""
```

---

## Phase 5: E2E Verification (2 hours)

### P5.1: Deploy to Cloud Run

```bash
gcloud run deploy nikita-api --source . --region us-central1 --project gcp-transcribe-test
```

### P5.2: Verify Social Circle Creation

1. Create test user via voice onboarding
2. Check database:
   ```sql
   SELECT * FROM user_social_circles WHERE user_id = 'xxx';
   ```
3. Verify 5-8 friends created

### P5.3: Verify Arc Creation

1. Have 3-5 conversations with test user
2. Check database:
   ```sql
   SELECT * FROM user_narrative_arcs WHERE user_id = 'xxx';
   ```
3. Verify arc started and progresses

### P5.4: Verify Generated Prompts

1. Check text prompt:
   ```sql
   SELECT * FROM generated_prompts WHERE user_id = 'xxx' AND platform = 'text';
   ```
2. Check voice prompt:
   ```sql
   SELECT * FROM generated_prompts WHERE user_id = 'xxx' AND platform = 'voice';
   ```
3. Verify social circle and arc sections present in prompt content

---

## Task Summary

| Phase | Tasks | Effort | Dependencies |
|-------|-------|--------|--------------|
| P1 | Database + Models | 2h | None |
| P2 | Social Circle Integration | 3h | P1 |
| P3 | Narrative Arc Integration | 4h | P1 |
| P4 | Voice Logging + Tests | 3h | P2, P3 |
| P5 | E2E Verification | 2h | P4 |

**Total**: 14 hours

**Parallel Opportunities**:
- P1.1, P1.2, P1.3 can run in parallel after migrations
- P2 and P3 can run in parallel after P1
- P4.1 and P4.3 can run in parallel

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Migration fails | Test on staging first; have rollback SQL ready |
| Arc logic complex | Start with 2-3 simple templates; add more post-launch |
| Token budget exceeded | Limit social circle to 5 friends; arcs to 2 active |
| Performance regression | Add caching for social circle (rarely changes) |

---

## Verification Commands

```bash
# After implementation:

# 1. Run all new tests
pytest tests/life_simulation/test_social_generator.py tests/life_simulation/test_arcs.py -v

# 2. Run integration tests
pytest tests/integration/test_context_surfacing_e2e.py -v

# 3. Check test count
pytest tests/ --collect-only | grep "test session starts" -A 1

# 4. Deploy
gcloud run deploy nikita-api --source . --region us-central1 --project gcp-transcribe-test
```
