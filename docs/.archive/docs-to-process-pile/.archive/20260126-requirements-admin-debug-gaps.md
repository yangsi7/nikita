# Requirements: Admin Dashboard Debug Gap Analysis

**Status**: Phase 1 - Requirements Extraction
**Date**: 2026-01-26
**Source**: Discovery-driven planning skill

---

## 1. Problem Statement

The admin dashboard has good coverage of **scoring, engagement, and conversations** but **completely lacks visibility into the humanization layer** (thoughts, threads, arcs, characters) that makes Nikita feel human. This prevents effective debugging when users report "Nikita feels robotic" or "conversations lack continuity."

### Current Debug Workflow (Broken)

```
User reports: "Nikita feels disconnected"
  ├─ ✅ Check conversations → Messages look fine
  ├─ ✅ Check scores → Metrics are normal
  ├─ ✅ Check prompts → Prompt was generated
  ├─ ❌ Check threads → NO VISIBILITY (why no follow-up?)
  ├─ ❌ Check thoughts → NO VISIBILITY (what was she thinking?)
  ├─ ❌ Check arcs → NO VISIBILITY (is storyline stuck?)
  ├─ ❌ Check characters → NO VISIBILITY (are friends available?)
  └─ ❌ DEBUGGING BLOCKED - Can't trace humanization failure
```

---

## 2. Critical Requirements (Must-Haves)

### CR-1: Conversation Thread Visibility
**Problem**: Can't debug why Nikita isn't following up on unresolved topics
**Solution**: Add `/admin/users/{id}/threads` endpoint + UI page
**Data**: thread_type, content, status (open/resolved/expired), source_conversation_id, created_at
**Use Case**: "Why didn't Nikita ask about the job interview she mentioned?"

### CR-2: Nikita Thoughts Visibility
**Problem**: Can't debug what Nikita is "thinking" between conversations
**Solution**: Add `/admin/users/{id}/thoughts` endpoint + UI page
**Data**: thought_type (14 types), content, psychological_context, expires_at, used_at
**Use Case**: "Why does Nikita seem emotionally flat? What's her inner state?"

### CR-3: Engagement History Timeline
**Problem**: Can only see current engagement state, not transitions
**Solution**: Add `/admin/users/{id}/engagement-history` endpoint + chart
**Data**: state transitions over time, confidence scores, drift detection
**Use Case**: "When did this user drift from IN_ZONE to DISTANT? Why?"

### CR-4: Social Circle & Character Visibility
**Problem**: Can't debug if generated characters are being used
**Solution**: Add `/admin/users/{id}/social-circle` endpoint + UI
**Data**: friend_name, role, personality, trigger_conditions, usage_count
**Use Case**: "Has 'Alex' (the best friend) ever been mentioned in conversations?"

### CR-5: Narrative Arc Inspector
**Problem**: Can't debug if storylines are progressing
**Solution**: Add `/admin/users/{id}/narrative-arcs` endpoint + UI
**Data**: template_name, category, current_stage (1-5), stage_progress, conversations_in_arc
**Use Case**: "Is the 'career crisis' arc stuck at stage 2?"

### CR-6: User Backstory Verification
**Problem**: Can't verify onboarding choices were saved correctly
**Solution**: Add backstory to user detail view
**Data**: how_met, venue_research, scenario (from user_backstories table)
**Use Case**: "Did the 'met at coffee shop' scenario get saved?"

---

## 3. Important Requirements (Should-Haves)

### IR-1: Humanization Context in Prompts
**Problem**: Can't see what humanization context was actually injected into prompts
**Solution**: Expand prompt detail view to show context_snapshot breakdown
**Data**: threads_injected, thoughts_injected, arcs_active, characters_available
**Use Case**: "Did the prompt actually include the unresolved thread?"

### IR-2: Continuity Timeline View
**Problem**: No combined view of threads + thoughts + arcs over time
**Solution**: Add timeline visualization showing all continuity elements
**Data**: Combined view of threads created/resolved, thoughts generated/used, arc progressions
**Use Case**: "Show me what happened to this user's story over the past week"

### IR-3: Full-Text Conversation Search
**Problem**: Can't search for specific keywords across conversations
**Solution**: Add search endpoint and UI
**Data**: Search across conversation messages, threads, thoughts
**Use Case**: "Find all conversations where 'job interview' was mentioned"

### IR-4: Processing Pipeline Deep Dive
**Problem**: Can see pipeline status but not stage-specific data
**Solution**: Expand pipeline view to show extracted entities, tone analysis, thread extraction details
**Data**: extracted_entities, emotional_tone, extracted_facts per stage
**Use Case**: "What entities were extracted from this conversation?"

### IR-5: Vice Discovery Timeline
**Problem**: Can see current vice preferences but not how they were discovered
**Solution**: Add vice history with timestamps and source conversations
**Data**: When each vice was first detected, intensity changes over time
**Use Case**: "When did we detect this user's 'dark humor' preference?"

---

## 4. Optional Requirements (Nice-to-Haves)

### OR-1: Real-Time Updates
**Problem**: Dashboard requires manual refresh
**Solution**: WebSocket or Server-Sent Events for live updates
**Use Case**: Watch conversation in real-time as it happens

### OR-2: Export Functionality
**Problem**: Can't export data for external analysis
**Solution**: CSV/JSON export buttons on all list views
**Use Case**: Export conversation history for review

### OR-3: Comparison Mode
**Problem**: Can't compare two users side-by-side
**Solution**: Multi-user comparison view
**Use Case**: "Why is User A thriving but User B struggling in the same chapter?"

### OR-4: What-If Scenario Modeling
**Problem**: Can't preview what would happen with different inputs
**Solution**: Simulation mode for testing prompts/scoring
**Use Case**: "If I change this user's chapter, what prompt would generate?"

---

## 5. Known Gaps (To Be Investigated)

| Gap ID | Description | Severity | Investigation Needed |
|--------|-------------|----------|---------------------|
| GAP-01 | ConversationThreads table may have no data | HIGH | Query prod DB to verify data exists |
| GAP-02 | NikitaThoughts psychological_context field added recently | MEDIUM | Verify schema matches model |
| GAP-03 | SocialCircle may not be populated for existing users | MEDIUM | Check if generation runs on existing users |
| GAP-04 | NarrativeArc may not be populated | MEDIUM | Verify arc generation is triggered |
| GAP-05 | EngagementHistory table may not exist (model found but no repo) | HIGH | Verify table in Supabase |
| GAP-06 | Missing indexes on thread_type, thought_type, current_stage | MEDIUM | May cause slow queries |

---

## 6. Constraints

### C-1: Performance
- Neo4j queries have 30s timeout, 60s cold start
- All new endpoints must complete in <500ms (warm cache)
- Pagination required for all list endpoints (50 items max)

### C-2: Security
- All admin access must be logged to audit_logs
- PII must be redacted from logs
- @silent-agents.com email domain required

### C-3: Compatibility
- Must work with existing admin UI patterns
- Must use existing component library (shadcn/ui)
- Must follow existing API schema patterns

---

## 7. Success Criteria

1. **Debugging Completeness**: Admin can trace any "Nikita feels robotic" report through all humanization layers
2. **Data Visibility**: 100% of humanization data (threads, thoughts, arcs, characters) visible in admin
3. **Performance**: All new endpoints <500ms response time
4. **Test Coverage**: All new endpoints have unit tests
5. **E2E Verification**: Can trigger conversation via Telegram, see all data flow through admin

---

## 8. Out of Scope

- Player-facing portal changes (this is admin-only)
- Game mechanics changes (scoring, decay, chapters)
- Voice agent changes (ElevenLabs integration)
- New humanization features (only exposing existing data)

---

## 9. Dependencies

| Dependency | Status | Risk |
|-----------|--------|------|
| ConversationThread model exists | ✅ Confirmed | LOW |
| NikitaThought model exists | ✅ Confirmed | LOW |
| UserSocialCircle model exists | ✅ Confirmed | LOW |
| UserNarrativeArc model exists | ✅ Confirmed | LOW |
| UserBackstory model exists | ✅ Confirmed | LOW |
| EngagementHistory model exists | ⚠️ Needs verification | MEDIUM |
| Tables have data | ⚠️ Needs verification | HIGH |
| Post-processing populates tables | ⚠️ Needs verification | HIGH |

---

## 10. Questions for Stakeholder

1. **Priority**: Should we focus on threads+thoughts first (continuity debugging) or arcs+characters (narrative debugging)?
2. **Scope**: Should we verify data exists in production before building UI, or build UI and surface "no data" gracefully?
3. **Testing Approach**: Should we test via Chrome MCP + Telegram MCP, or write automated E2E tests?
4. **Timeline**: Is this a single sprint or phased rollout?
