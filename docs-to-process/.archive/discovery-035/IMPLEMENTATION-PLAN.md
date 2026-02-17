# Implementation Plan: Nikita Context Surfacing Fixes

## Executive Summary

**Goal**: Fix 6 identified gaps to achieve 100% completion of Nikita's context surfacing system

**Total Effort**: 13-20 hours
**Priority Items**: GAP-1 (Social Circle) + GAP-2 (Narrative Arcs) = 5-9 hours

---

## Implementation Phases

### Phase 0: Validation (Spikes) - 1 hour

Before implementation, verify assumptions:

**Spike 0.1**: Verify social_generator.py works standalone
```bash
cd /Users/yangsim/Nanoleq/sideProjects/nikita
python -c "
from nikita.life_simulation.social_generator import get_social_generator, generate_social_circle_for_user
sg = get_social_generator()
print('Core characters:', [c.name for c in sg.CORE_CHARACTERS])
circle = generate_social_circle_for_user('test-user', 'Berlin', ['hacking'], 'security', 'party')
print('Generated:', [f.name for f in circle.friends])
"
```

**Spike 0.2**: Verify arcs.py works standalone
```bash
python -c "
from nikita.life_simulation.arcs import get_arc_system, ArcCategory
arc_sys = get_arc_system()
print('Templates:', list(arc_sys.ARC_TEMPLATES.keys()))
template = arc_sys.select_template(vulnerability_level=2, recent_topics=['work', 'stress'])
print('Selected:', template.name if template else None)
"
```

**Acceptance Criteria**:
- [x] social_generator imports without error
- [x] arc_system imports without error
- [ ] Both produce expected output

---

### Phase 1: Database Migrations - 2 hours

#### T1.1: Create user_social_circles table

**File**: `migrations/0015_social_circles.sql` (or use Supabase MCP)

```sql
CREATE TABLE user_social_circles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    friend_name TEXT NOT NULL,
    friend_role TEXT NOT NULL,
    personality_traits JSONB NOT NULL DEFAULT '[]',
    storyline_potential TEXT,
    trigger_conditions JSONB DEFAULT '[]',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, friend_name)
);

CREATE INDEX idx_social_circles_user_id ON user_social_circles(user_id);
```

**Acceptance Criteria**:
- [ ] Migration applied successfully
- [ ] Table exists with correct schema
- [ ] RLS policies created if needed

#### T1.2: Create user_narrative_arcs table

**File**: `migrations/0016_narrative_arcs.sql`

```sql
CREATE TABLE user_narrative_arcs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    arc_template TEXT NOT NULL,
    arc_category TEXT NOT NULL,
    current_stage TEXT NOT NULL DEFAULT 'setup',
    stage_progress INTEGER DEFAULT 0,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    expected_duration INTEGER DEFAULT 5, -- conversations
    emotional_impact JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_narrative_arcs_user_id ON user_narrative_arcs(user_id);
CREATE INDEX idx_narrative_arcs_active ON user_narrative_arcs(is_active) WHERE is_active = true;
```

**Acceptance Criteria**:
- [ ] Migration applied successfully
- [ ] Table exists with correct schema

---

### Phase 2: Social Circle Integration - 3 hours

#### T2.1: Create SocialCircle Repository

**File**: `nikita/db/repositories/social_circle_repository.py`

```python
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

class SocialCircleRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_circle_for_user(
        self,
        user_id: UUID,
        friends: list[FriendCharacter]
    ) -> list[UserSocialCircle]:
        """Store generated social circle."""
        ...

    async def get_circle(self, user_id: UUID) -> list[UserSocialCircle]:
        """Get user's social circle."""
        ...

    async def get_active_friends(self, user_id: UUID) -> list[UserSocialCircle]:
        """Get friends available for storylines."""
        ...
```

**Acceptance Criteria**:
- [ ] Repository creates friends from FriendCharacter objects
- [ ] Repository retrieves social circle for user
- [ ] Tests pass (5+ tests)

#### T2.2: Wire to Onboarding Handoff

**File**: `nikita/onboarding/handoff.py`

**Modify** `complete_onboarding()` or `create_profile()`:

```python
from nikita.life_simulation import generate_social_circle_for_user

async def complete_onboarding(user_id: UUID, profile: OnboardingProfile):
    # ... existing code ...

    # NEW: Generate personalized social circle
    social_circle = generate_social_circle_for_user(
        user_id=str(user_id),
        location=profile.location,
        hobbies=profile.hobbies or [],
        job=profile.job,
        meeting_context=profile.meeting_context
    )

    # Store in database
    repo = SocialCircleRepository(session)
    await repo.create_circle_for_user(user_id, social_circle.friends)
```

**Acceptance Criteria**:
- [ ] Social circle generated on profile creation
- [ ] Friends stored in database
- [ ] Integration test passes

#### T2.3: Add to MetaPromptService._load_context()

**File**: `nikita/meta_prompts/service.py`

**Modify** `_load_context()`:

```python
# In TIER 5: PERSONALIZATION section
social_circle = await self._get_social_circle(user_id)
context["social_circle"] = [
    f"{f.friend_name} ({f.friend_role}): {f.personality_traits}"
    for f in social_circle
]
```

**Acceptance Criteria**:
- [ ] Social circle loaded in context
- [ ] Available in system prompt template
- [ ] Token count within budget

#### T2.4: Add to system_prompt.meta.md

**File**: `nikita/meta_prompts/templates/system_prompt.meta.md`

Add section:

```markdown
## NIKITA'S SOCIAL WORLD

These are Nikita's close friends and family. Reference them naturally:

{% for friend in social_circle %}
- **{{friend.name}}** ({{friend.role}}): {{friend.traits}}
{% endfor %}
```

**Acceptance Criteria**:
- [ ] Template includes social circle section
- [ ] Friends available for LLM to reference

---

### Phase 3: Narrative Arc Integration - 4 hours

#### T3.1: Create NarrativeArc Repository

**File**: `nikita/db/repositories/narrative_arc_repository.py`

```python
class NarrativeArcRepository:
    async def create_arc(self, user_id: UUID, template: ArcTemplate) -> UserNarrativeArc:
        """Create new narrative arc for user."""
        ...

    async def get_active_arcs(self, user_id: UUID) -> list[UserNarrativeArc]:
        """Get all active (unresolved) arcs."""
        ...

    async def advance_arc(self, arc_id: UUID, new_stage: ArcStage) -> UserNarrativeArc:
        """Progress arc to next stage."""
        ...

    async def resolve_arc(self, arc_id: UUID) -> UserNarrativeArc:
        """Mark arc as resolved."""
        ...
```

**Acceptance Criteria**:
- [ ] CRUD operations for arcs
- [ ] Stage progression works
- [ ] Tests pass (8+ tests)

#### T3.2: Add Arc Selection to PostProcessor

**File**: `nikita/context/post_processor.py`

**Add new stage** after `_analyze_psychology()`:

```python
async def _update_narrative_arcs(
    self,
    user_id: UUID,
    conversation_dynamics: ConversationDynamics,
    vulnerability_level: int
) -> dict:
    """Update narrative arcs based on conversation."""
    arc_system = get_arc_system()
    arc_repo = NarrativeArcRepository(self.session)

    # Get active arcs
    active_arcs = await arc_repo.get_active_arcs(user_id)

    # Check if should start new arc (max 2 active)
    if len(active_arcs) < 2:
        template = arc_system.select_template(
            vulnerability_level=vulnerability_level,
            recent_topics=conversation_dynamics.topics
        )
        if template and self._should_start_arc(template, active_arcs):
            new_arc = await arc_repo.create_arc(user_id, template)
            active_arcs.append(new_arc)

    # Progress existing arcs
    for arc in active_arcs:
        new_stage = arc_system.should_advance(arc, conversation_dynamics)
        if new_stage:
            await arc_repo.advance_arc(arc.id, new_stage)

    return {"active_arcs": [a.to_dict() for a in active_arcs]}
```

**Acceptance Criteria**:
- [ ] Arcs created when appropriate
- [ ] Arcs progress through stages
- [ ] Max 2 active arcs enforced

#### T3.3: Add Arc Context to MetaPromptService

**File**: `nikita/meta_prompts/service.py`

```python
# In _load_context()
narrative_arcs = await self._get_active_arcs(user_id)
context["narrative_arcs"] = arc_system.get_arc_context(narrative_arcs)
```

**Acceptance Criteria**:
- [ ] Arc context loaded
- [ ] Available in prompt template

#### T3.4: Add to system_prompt.meta.md

Add section:

```markdown
## ONGOING STORYLINES

These are multi-conversation arcs Nikita is experiencing:

{% for arc in narrative_arcs %}
- **{{arc.name}}** ({{arc.stage}}): {{arc.current_situation}}
{% endfor %}

Weave these naturally into conversation without forcing them.
```

---

### Phase 4: Observability & Tests - 3 hours

#### T4.1: Add Voice Prompt Logging

**File**: `nikita/agents/voice/context.py`

**Modify** `ConversationConfigBuilder.build_config()`:

```python
async def build_config(self, user: User, ...) -> dict:
    # Generate prompt (already done)
    generated_prompt = await self.meta_service.generate_system_prompt(user.id)

    # NEW: Ensure prompt is committed (logged)
    self.session.add(generated_prompt)
    await self.session.commit()

    # Store reference for admin visibility
    self.generated_prompt_id = generated_prompt.id
```

**Acceptance Criteria**:
- [ ] Voice prompts logged to generated_prompts table
- [ ] Admin can view voice prompts

#### T4.2: Create test_social_generator.py

**File**: `tests/life_simulation/test_social_generator.py`

```python
class TestSocialCircleGenerator:
    def test_generates_core_characters(self):
        """Should include core characters (Lena, Viktor, Max, etc.)."""

    def test_adapts_to_location(self):
        """Should adapt friend jobs/activities to user location."""

    def test_adapts_to_hobbies(self):
        """Should include friends sharing user hobbies."""

    def test_adapts_to_job(self):
        """Should include friends in related professions."""

    def test_meeting_context_integration(self):
        """Should reference meeting context in friend backstories."""
```

**Target**: 15+ tests

#### T4.3: Create test_arcs.py

**File**: `tests/life_simulation/test_arcs.py`

```python
class TestNarrativeArcSystem:
    def test_template_selection_by_vulnerability(self):
        """Should select appropriate templates for vulnerability level."""

    def test_arc_stage_progression(self):
        """Should progress through setup → rising → climax → falling → resolved."""

    def test_arc_context_formatting(self):
        """Should format arc context for prompt injection."""

    def test_max_duration_enforcement(self):
        """Should resolve arcs after max duration."""
```

**Target**: 20+ tests

#### T4.4: Create Integration Test

**File**: `tests/integration/test_context_surfacing_e2e.py`

```python
class TestContextSurfacingE2E:
    async def test_full_context_build(self):
        """Verify all 6 tiers load correctly."""

    async def test_social_circle_in_prompt(self):
        """Verify social circle appears in generated prompt."""

    async def test_arc_context_in_prompt(self):
        """Verify active arcs appear in generated prompt."""

    async def test_voice_text_parity(self):
        """Verify voice and text get equivalent context."""
```

---

### Phase 5: Verification - 1 hour

#### T5.1: Run Full Test Suite

```bash
cd /Users/yangsim/Nanoleq/sideProjects/nikita
source .venv/bin/activate

# Run all new tests
pytest tests/life_simulation/test_social_generator.py -v
pytest tests/life_simulation/test_arcs.py -v
pytest tests/integration/test_context_surfacing_e2e.py -v

# Run full suite
pytest tests/ -v --tb=short
```

**Acceptance Criteria**:
- [ ] All new tests pass
- [ ] No regressions in existing tests
- [ ] Total tests: 1300+ (up from 1248)

#### T5.2: Manual E2E Verification

1. **Create new user via Telegram** (or use existing test user)
2. **Check social circle created**:
   ```sql
   SELECT * FROM user_social_circles WHERE user_id = 'xxx';
   ```
3. **Verify context includes friends**:
   - Check generated_prompts table for social circle section
4. **Have conversation that should trigger arc**:
   - Talk about work stress, friend drama, etc.
5. **Check arc created**:
   ```sql
   SELECT * FROM user_narrative_arcs WHERE user_id = 'xxx';
   ```

---

## Summary

| Phase | Tasks | Effort | Dependencies |
|-------|-------|--------|--------------|
| 0. Validation | Spikes | 1h | None |
| 1. Migrations | 2 tables | 2h | None |
| 2. Social Circle | 4 tasks | 3h | Phase 1 |
| 3. Narrative Arcs | 4 tasks | 4h | Phase 1 |
| 4. Tests | 4 tasks | 3h | Phase 2, 3 |
| 5. Verification | 2 tasks | 1h | Phase 4 |

**Total**: 14 hours

**Critical Path**: Phase 1 → Phase 2 + Phase 3 (parallel) → Phase 4 → Phase 5

---

## Files to Create/Modify

### New Files
- `migrations/0015_social_circles.sql`
- `migrations/0016_narrative_arcs.sql`
- `nikita/db/models/social_circle.py`
- `nikita/db/models/narrative_arc.py`
- `nikita/db/repositories/social_circle_repository.py`
- `nikita/db/repositories/narrative_arc_repository.py`
- `tests/life_simulation/test_social_generator.py`
- `tests/life_simulation/test_arcs.py`
- `tests/integration/test_context_surfacing_e2e.py`

### Modified Files
- `nikita/onboarding/handoff.py` - Wire social circle generation
- `nikita/context/post_processor.py` - Add arc update stage
- `nikita/meta_prompts/service.py` - Load social circle + arcs in context
- `nikita/meta_prompts/templates/system_prompt.meta.md` - Add template sections
- `nikita/agents/voice/context.py` - Add prompt logging
- `nikita/db/models/__init__.py` - Export new models

---

## Verification Commands

```bash
# After implementation, run these to verify:

# 1. Check migrations applied
psql $DATABASE_URL -c "SELECT * FROM user_social_circles LIMIT 1;"
psql $DATABASE_URL -c "SELECT * FROM user_narrative_arcs LIMIT 1;"

# 2. Run tests
pytest tests/life_simulation/test_social_generator.py tests/life_simulation/test_arcs.py -v

# 3. Test context loading
python -c "
import asyncio
from nikita.meta_prompts.service import MetaPromptService
from nikita.db.session import get_session_maker

async def test():
    async with get_session_maker()() as session:
        service = MetaPromptService(session)
        context = await service._load_context('test-user-id')
        print('Social circle:', context.get('social_circle'))
        print('Arcs:', context.get('narrative_arcs'))

asyncio.run(test())
"

# 4. E2E test via Telegram MCP
# Send message, check generated prompt in admin UI
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Migration fails | Test on staging first, have rollback script |
| Arc logic complex | Start with 2-3 templates, add more later |
| Token budget exceeded | Limit social circle to 5 friends in prompt |
| Performance impact | Add caching for social circle (rarely changes) |
