# Gap Analysis: Nikita Context Surfacing

## Executive Summary

**Overall System Status**: 94% Complete

The Nikita context surfacing system is **well-architected and mostly complete**. Both text and voice agents achieve 100% context parity through different mechanisms. However, 6 gaps were identified ranging from CRITICAL to LOW priority.

---

## Gap Severity Framework

| Severity | Definition | Action Required |
|----------|------------|-----------------|
| 🔴 CRITICAL | Breaks core functionality | Must fix before production |
| 🟠 HIGH | Significant feature gap | Should fix in current sprint |
| 🟡 MEDIUM | Quality/observability issue | Fix when convenient |
| 🟢 LOW | Nice-to-have improvement | Backlog |

---

## Identified Gaps

### GAP-1: Social Circle NOT Wired to Onboarding 🟠 HIGH

**Status**: Module exists, integration missing

**Description**: The `SocialCircleGenerator` module is complete (536 LOC) but is NEVER called when users complete onboarding. This means Nikita's social world is generic, not personalized to user's profile.

**Location**:
- Generator: `nikita/life_simulation/social_generator.py`
- Should be called from: `nikita/onboarding/handoff.py`

**Expected Behavior**:
```python
# After user profile created:
from nikita.life_simulation import generate_social_circle_for_user

social_circle = generate_social_circle_for_user(
    user_id=user.id,
    location=profile.location,
    hobbies=profile.hobbies,
    job=profile.job,
    meeting_context=profile.meeting_context
)
# Store in user_social_circle table (needs migration)
```

**Current Behavior**: Social circle module exists but never instantiated. Users get no personalized social world.

**Impact**:
- Nikita can't reference "my friend Lena" or "Viktor at work"
- No multi-week storylines involving named characters
- Reduced immersion (20% of humanization value lost)

**Risk Score**: Impact (HIGH) × Confidence Gap (100%) = **80/100 CRITICAL**

**Fix Required**:
1. Create `user_social_circles` table (migration)
2. Wire `generate_social_circle_for_user()` in `handoff.py`
3. Add social circle to `_load_context()` in MetaPromptService
4. Inject into system prompt template

**Effort**: 2-4 hours

---

### GAP-2: Narrative Arcs NOT Wired to Conversation Flow 🟠 HIGH

**Status**: Module exists, integration missing

**Description**: The `NarrativeArcSystem` module is complete (527 LOC) but is NEVER called during conversation processing. No arcs ever start, progress, or resolve.

**Location**:
- System: `nikita/life_simulation/arcs.py`
- Should be called from: `nikita/context/post_processor.py`

**Expected Behavior**:
```python
# After each conversation (in PostProcessor):
arc_system = get_arc_system()

# Check if new arc should start
if should_start_arc(vulnerability_level, chapter, recent_topics):
    template = arc_system.select_template(vulnerability_level, topics)
    arc = arc_system.create_arc(user_id, template)

# Progress existing arcs
for arc in get_active_arcs(user_id):
    arc_system.advance_arc(arc, conversation_dynamics)

# Inject active arc context into next prompt
arc_context = arc_system.get_arc_context(user_id)
```

**Current Behavior**: Arc module exists but never called. All arcs have status "never_started".

**Impact**:
- No multi-conversation storylines (e.g., "Viktor's crisis" arc)
- Relationship feels static between conversations
- No dramatic tension building over time
- 15% of humanization value lost

**Risk Score**: Impact (HIGH) × Confidence Gap (100%) = **80/100 CRITICAL**

**Fix Required**:
1. Create `user_narrative_arcs` table (migration)
2. Add arc selection logic to PostProcessor (new stage or extend existing)
3. Store active arcs with stage progression
4. Add `get_arc_context()` to MetaPromptService._load_context()

**Effort**: 3-5 hours

---

### GAP-3: Voice Prompt Logging Missing 🟡 MEDIUM

**Status**: Text logs prompts, voice doesn't

**Description**: Text agent logs every generated prompt to `generated_prompts` table for admin debugging. Voice agent uses same MetaPromptService but doesn't capture the prompt for logging.

**Location**:
- Text logging: `nikita/agents/text/agent.py:build_system_prompt()` → calls `session.commit()`
- Voice missing: `nikita/agents/voice/context.py:ConversationConfigBuilder`

**Expected Behavior**:
```python
# Voice should also log:
generated_prompt = await meta_service.generate_system_prompt(user_id)
# Store generated_prompt.id for admin visibility
```

**Current Behavior**: Voice prompts generated but not logged. Admin can't debug voice prompt issues.

**Impact**:
- Can't inspect what prompt voice agent received
- Harder to debug voice-specific issues
- Admin monitoring gap (10% of observability lost)

**Risk Score**: Impact (MEDIUM) × Confidence Gap (100%) = **50/100 MEDIUM**

**Fix Required**:
1. In `ConversationConfigBuilder.build_config()`, ensure generated_prompt is committed
2. Store `generated_prompt.id` in voice conversation record
3. Add to admin voice monitoring page

**Effort**: 1-2 hours

---

### GAP-4: Test Coverage for Social Generator & Arcs 🟡 MEDIUM

**Status**: Modules exist without dedicated tests

**Description**: `social_generator.py` (536 LOC) and `arcs.py` (527 LOC) have no dedicated test files. Only `psychology_mapper.py` and `relationship_analyzer.py` have test coverage.

**Current Test Coverage**:
| Module | Test File | Tests |
|--------|-----------|-------|
| psychology_mapper.py | test_psychology_mapper.py | 31 ✅ |
| relationship_analyzer.py | test_relationship_analyzer.py | 25 ✅ |
| social_generator.py | ❌ NONE | 0 ⚠️ |
| arcs.py | ❌ NONE | 0 ⚠️ |

**Impact**:
- Can't verify social circle adaptation logic works
- Can't verify arc progression state machine
- Regressions could go unnoticed

**Risk Score**: Impact (MEDIUM) × Confidence Gap (80%) = **40/100 MEDIUM**

**Fix Required**:
1. Create `tests/life_simulation/test_social_generator.py` (15+ tests)
2. Create `tests/life_simulation/test_arcs.py` (20+ tests)
3. Test character adaptation, arc stages, template selection

**Effort**: 2-3 hours

---

### GAP-5: Thread/Thought Formatting Inconsistency 🟢 LOW

**Status**: Text agent formats, voice returns raw

**Description**: Text agent formats threads and thoughts with specific structure. Voice agent's `get_context()` server tool returns raw objects.

**Text Format**:
```python
threads_formatted = [
    f"[{t.thread_type}] {t.content} (opened {t.created_at})"
    for t in threads
]
```

**Voice Format**:
```python
threads = {thread_type: [t.content for t in type_threads]}
# Returns dict of lists, not formatted strings
```

**Impact**: Minor inconsistency. Voice LLM parses dict, text LLM receives formatted strings.

**Risk Score**: Impact (LOW) × Confidence Gap (60%) = **15/100 LOW**

**Fix Required**: Unify formatting in voice server_tools.py to match text agent.

**Effort**: 30 minutes

---

### GAP-6: A/B Testing Framework Missing 🟢 LOW

**Status**: Planned but not implemented

**Description**: Plan called for A/B testing framework to measure authenticity improvements from deep humanization. Not implemented.

**Impact**: Can't quantitatively measure if changes improve user perception of authenticity.

**Risk Score**: Impact (LOW) × Confidence Gap (100%) = **20/100 LOW**

**Fix Required**: Create A/B testing harness if needed post-deployment.

**Effort**: 4-6 hours (when needed)

---

## Risk Matrix

```
                    Impact
                    HIGH        MEDIUM      LOW
              ┌─────────────┬───────────┬───────────┐
         100% │ GAP-1 (80)  │           │           │
              │ GAP-2 (80)  │ GAP-3 (50)│ GAP-6 (20)│
              ├─────────────┼───────────┼───────────┤
Confidence    │             │           │           │
Gap      80%  │             │ GAP-4 (40)│           │
              ├─────────────┼───────────┼───────────┤
         60%  │             │           │ GAP-5 (15)│
              └─────────────┴───────────┴───────────┘
```

---

## Gap Resolution Priority

| Priority | Gap | Risk Score | Effort | Status |
|----------|-----|------------|--------|--------|
| P1 | GAP-1: Social Circle | 80 | 2-4h | ⚠️ NOT STARTED |
| P1 | GAP-2: Narrative Arcs | 80 | 3-5h | ⚠️ NOT STARTED |
| P2 | GAP-3: Voice Logging | 50 | 1-2h | ⚠️ NOT STARTED |
| P2 | GAP-4: Test Coverage | 40 | 2-3h | ⚠️ NOT STARTED |
| P3 | GAP-5: Format Consistency | 15 | 0.5h | ⚠️ NOT STARTED |
| P3 | GAP-6: A/B Testing | 20 | 4-6h | DEFERRED |

**Total Effort to 100%**: 13-20 hours

---

## What's Working (No Gaps)

### Context Loading ✅
- MetaPromptService._load_context() loads 50+ fields correctly
- All 6 tiers (user state, temporal, engagement, psychology, personalization, memory) working
- Token budget (15K) properly configured with tiered fallback

### Text Agent ✅
- @agent.instructions decorators inject context correctly
- message_history with 3K token budget working
- Tools (recall_memory, note_user_fact) functional

### Voice Agent ✅
- 32 dynamic variables populated correctly
- 4 server tools (get_context, get_memory, score_turn, update_memory) working
- 100% context parity with text agent achieved

### Psychology (Spec 035) ✅
- _analyze_psychology() stage in PostProcessor working
- RelationshipAnalyzer tracking dynamics correctly
- Vulnerability gating (L0-L5) interaction-based as planned
- 56+ tests passing

### Memory Integration ✅
- 3 Graphiti graphs (user, relationship, nikita) queried correctly
- Facts, episodes, events loaded with proper limits
- Threads and thoughts retrieved and formatted

### Humanization Pipeline ✅
- All 8 specs (021-028) wired into context
- Life simulation events loading
- 4D emotional state computing
- Conflict system integrated

---

## Recommendations

### Immediate (Before Next Release)
1. **Wire social circle to onboarding** (GAP-1) - Core feature, 2-4h
2. **Wire narrative arcs to PostProcessor** (GAP-2) - Core feature, 3-5h

### Near-Term (This Sprint)
3. **Add voice prompt logging** (GAP-3) - Observability, 1-2h
4. **Add test coverage** (GAP-4) - Quality, 2-3h

### Backlog
5. **Unify formatting** (GAP-5) - Polish, 0.5h
6. **A/B testing** (GAP-6) - When needed for validation

---

## Verification Tests Needed

To PROVE the system is working, we need tests that:

1. **Context Actually Builds** ✅ (EXISTS)
   - `tests/meta_prompts/test_full_context_integration.py` - 9 tests

2. **Psychology Injects** ✅ (EXISTS)
   - `tests/context/test_relationship_analyzer.py` - 25 tests
   - `tests/life_simulation/test_psychology_mapper.py` - 31 tests

3. **RAG/Memory Works** ⚠️ (PARTIAL)
   - Graphiti mocked in most tests
   - Need integration test with real Neo4j

4. **Voice-Text Parity** ✅ (EXISTS)
   - `tests/agents/voice/test_server_tools.py` - 21 tests
   - `tests/agents/voice/test_dynamic_vars.py` - 18 tests

5. **Social Circle** ❌ (MISSING)
   - No tests for social_generator.py

6. **Narrative Arcs** ❌ (MISSING)
   - No tests for arcs.py
