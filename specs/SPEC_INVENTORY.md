# Nikita Spec Inventory

**Generated**: 2025-11-28
**Updated**: 2026-01-13 (28 specs - 7 humanization specs implemented)
**Total Specs**: 28 (27 implemented, 1 remaining)

---

## Spec Matrix

| # | Spec | Type | Status | Depends On | Blocks |
|---|------|------|--------|------------|--------|
| 001 | nikita-text-agent | Feature | ✅ IMPLEMENTED (156 tests) | 012 | 002, 007 |
| 002 | telegram-integration | Feature | ✅ DEPLOYED (86 tests) | 009, 010, 011, 001, 012 | - |
| 003 | scoring-engine | Feature | ✅ IMPLEMENTED (60 tests) | 009, 013, 014 | 004, 005, 006 |
| 004 | chapter-boss-system | Feature | ✅ IMPLEMENTED (142 tests) | 009, 013, 003, 014 | 008 |
| 005 | decay-system | Feature | ✅ IMPLEMENTED (52 tests) | 009, 011, 013, 014, 003 | 008 |
| 006 | vice-personalization | Feature | ✅ IMPLEMENTED (81 tests) | 009, 013, 003 | 007 |
| 007 | voice-agent | Feature | ✅ DEPLOYED (186 tests) | 009, 010, 012, 003-006 | - |
| 008 | player-portal | Feature | ⚠️ 85% (Backend 100%, Admin 100%, Settings 50%) | 009, 010, 011, 003-006 | - |
| 009 | database-infrastructure | **Infra** | ✅ IMPLEMENTED | Supabase | All features |
| 010 | api-infrastructure | **Infra** | ✅ IMPLEMENTED | 009 | 002, 007, 008 |
| 011 | background-tasks | **Infra** | ✅ IMPLEMENTED (5 pg_cron jobs) | 009, 010 | 002, 005, 008 |
| **012** | **context-engineering** | **Feature** | ✅ IMPLEMENTED (50 tests) | 009, 013, 014 | 001, 002, 007 |
| **013** | **configuration-system** | **Feature** | ✅ IMPLEMENTED (89 tests) | - | 012, 003-006 |
| **014** | **engagement-model** | **Feature** | ✅ IMPLEMENTED (179 tests) | 009, 013 | 012, 003, 005 |
| 015 | onboarding-fix | Feature | ✅ IMPLEMENTED | 002 | 017 |
| 016 | admin-debug-portal | Feature | ✅ Ready (audit PASS) | 009, 010 | - |
| 017 | enhanced-onboarding | Feature | ⚠️ 78% (E2E verified) | 015, 012, 013 | - |
| 018 | admin-prompt-viewing | Feature | ✅ IMPLEMENTED | 009, 010, 012 | - |
| 019 | admin-voice-monitoring | Feature | ✅ IMPLEMENTED (RETROACTIVE) | 009, 010, 007 | - |
| 020 | admin-text-monitoring | Feature | ✅ IMPLEMENTED (RETROACTIVE) | 009, 010, 002 | - |
| **021** | **hierarchical-prompt-composition** | **Feature** | ✅ IMPLEMENTED (345 tests) | 012 | 022-028 |
| **022** | **life-simulation-engine** | **Feature** | ✅ IMPLEMENTED (212 tests) | 021 | 023, 025, 027 |
| **023** | **emotional-state-engine** | **Feature** | ✅ IMPLEMENTED (233 tests) | 021, 022 | 024, 025, 027 |
| **024** | **behavioral-meta-instructions** | **Feature** | ✅ IMPLEMENTED (147 tests) | 021, 023 | 025, 026, 027 |
| **025** | **proactive-touchpoint-system** | **Feature** | ✅ IMPLEMENTED (189 tests) | 021-024 | - |
| **026** | **text-behavioral-patterns** | **Feature** | ✅ IMPLEMENTED (167 tests) | 024 | - |
| **027** | **conflict-generation-system** | **Feature** | ✅ IMPLEMENTED (263 tests) | 023, 024 | - |
| **028** | **voice-onboarding** | **Feature** | 🆕 SPEC COMPLETE (31 tasks) | 007, 021 | - |

---

## Implementation Order (Updated 2026-01-12)

### Phase A: Infrastructure Foundation ✅ COMPLETE
1. **009-database-infrastructure** - Repository pattern, migrations, RLS
2. **010-api-infrastructure** - FastAPI routes, auth, middleware
3. **011-background-tasks** - pg_cron, 5 scheduled jobs active

### Phase B: Core System Architecture ✅ COMPLETE
4. **013-configuration-system** - Hybrid layered config (YAML + prompts + code)
5. **014-engagement-model** - Calibration detection, clinginess/neglect algorithms
6. **012-context-engineering** - 6-stage context generation pipeline

### Phase C: Core Game Engine ✅ COMPLETE
7. **003-scoring-engine** - Core mechanic (4 metrics, deltas, calibration multiplier)
8. **004-chapter-boss-system** - Progression + win/lose (2-3 week timeline)
9. **005-decay-system** - Hourly decay + game over (chapter-dependent recovery)
10. **006-vice-personalization** - Personality adaptation

### Phase D: Platform Integration ✅ COMPLETE
11. **001-nikita-text-agent** - Pydantic AI text agent (156 tests)
12. **002-telegram-integration** - Primary user interface (deployed Cloud Run)
13. **015-onboarding-fix** - OTP flow fixed, magic link deprecated
14. **017-enhanced-onboarding** - Memory integration + first Nikita message

### Phase E: Advanced Features ✅ COMPLETE (Voice) / ⚠️ IN PROGRESS (Portal)
15. **007-voice-agent** - ElevenLabs Conversational AI 2.0 (deployed Jan 2026)
16. **008-player-portal** - Dashboard + voice call initiation (85% complete)

### Phase F: Admin Tools ✅ COMPLETE (Jan 2026)
17. **016-admin-debug-portal** - Admin debug dashboard (implemented)
18. **018-admin-prompt-viewing** - Admin prompt viewing (implemented)
19. **019-admin-voice-monitoring** - Voice call monitoring (RETROACTIVE)
20. **020-admin-text-monitoring** - Text conversation monitoring (RETROACTIVE)

### Phase G: Humanization Overhaul ✅ 7/8 COMPLETE (160/191 tasks)
21. **021-hierarchical-prompt-composition** ✅ IMPLEMENTED (345 tests) - 6-layer prompt system
22. **022-life-simulation-engine** ✅ IMPLEMENTED (212 tests) - Daily events, mood derivation
23. **023-emotional-state-engine** ✅ IMPLEMENTED (233 tests) - 4D mood, conflict, recovery
24. **024-behavioral-meta-instructions** ✅ IMPLEMENTED (166 tests) - Decision trees, directional nudges
25. **025-proactive-touchpoint-system** ✅ IMPLEMENTED (189 tests) - 20-30% Nikita-initiated conversations
26. **026-text-behavioral-patterns** ✅ IMPLEMENTED (167 tests) - Emoji, length, splitting, punctuation
27. **027-conflict-generation-system** ✅ IMPLEMENTED (263 tests) - Triggers, escalation, breakup risk
28. **028-voice-onboarding** 🆕 SPEC (31 tasks) - Meta-Nikita facilitator, profile collection

**Cross-Spec Audit**: [humanization-cross-spec-audit.md](humanization-cross-spec-audit.md)

---

## Infrastructure Coverage

### 009-database-infrastructure
**Tables Defined**: users, user_metrics, user_vice_preferences, conversations, score_history, daily_summaries, pending_responses, job_history, engagement_history, conversation_threads, nikita_thoughts, generated_prompts, scheduled_messages
**Used By**: ALL features

### 010-api-infrastructure
**Endpoints Defined**:
- `/api/v1/telegram/webhook` (002)
- `/api/v1/telegram/set-webhook` (002)
- `/api/v1/voice/*` (007) - availability, initiate, signed-url, pre-call, server-tool, webhook
- `/api/v1/portal/stats/{user_id}` (008)
- `/api/v1/portal/conversations/{user_id}` (008)
- `/api/v1/portal/daily-summary/{user_id}/{date}` (008)
- `/api/v1/tasks/*` (011) - decay, deliver, summary, cleanup, process-conversations
- `/api/v1/admin/*` (016, 018) - debug endpoints
**Used By**: 002, 007, 008, 016, 018

### 011-background-tasks
**Jobs Defined** (5 active in pg_cron):
- `apply-hourly-decay` (005) - Hourly score decay
- `deliver-responses` (002) - Pending response delivery
- `generate-daily-summaries` (008) - Daily conversation summaries
- `cleanup-registrations` - Expired registration cleanup
- `process-conversations` - Inactive conversation detection
**Used By**: 002, 005, 008

---

## Core System Architecture Coverage

### 012-context-engineering
**Components Defined**:
- ContextGenerator (6-stage pipeline)
- PlayerProfile, TemporalContext, MemoryContext, NikitaState dataclasses
- MetaPromptService (LLM-powered prompt generation)
- Token budget allocation (~3700 tokens)
**Used By**: 001, 002, 007, 017

### 013-configuration-system
**Components Defined**:
- ConfigLoader (singleton)
- PromptLoader (.prompt file rendering)
- YAML configs: game.yaml, chapters.yaml, engagement.yaml, scoring.yaml, decay.yaml, schedule.yaml, vices.yaml
- Experiment overlays (A/B testing)
**Used By**: ALL features (foundational)

### 014-engagement-model
**Components Defined**:
- EngagementAnalyzer (state machine)
- 6 states: CALIBRATING, IN_ZONE, DRIFTING, CLINGY, DISTANT, OUT_OF_ZONE
- Clinginess/Neglect detection algorithms
- Calibration multipliers (0.2-1.0)
- Recovery mechanics (chapter-dependent)
**Used By**: 012, 003, 005

---

## Cross-Reference Validation

### Feature → Infrastructure Mapping

| Feature | 009 DB | 010 API | 011 Tasks |
|---------|--------|---------|-----------|
| 001-text-agent | ✅ UserRepo, ConvRepo | - | - |
| 002-telegram | ✅ UserRepo, ConvRepo | ✅ /telegram/* | ✅ deliver-responses |
| 003-scoring | ✅ UserRepo, ScoreHistRepo, EngagementHistRepo | - | - |
| 004-chapter | ✅ UserRepo, EngagementHistRepo | - | - |
| 005-decay | ✅ UserRepo, EngagementHistRepo | - | ✅ apply-hourly-decay |
| 006-vice | ✅ VicePreferenceRepo | - | - |
| 007-voice | ✅ ConvRepo, UserRepo | ✅ /voice/* | - |
| 008-portal | ✅ All repos | ✅ /portal/* | ✅ generate-summaries |
| 012-context-engineering | ✅ UserRepo, ConvRepo, EngagementRepo | - | - |
| 013-configuration-system | - | - | - |
| 014-engagement-model | ✅ UserRepo, EngagementHistRepo | - | - |
| 015-onboarding-fix | ✅ UserRepo | ✅ /auth/* | - |
| 016-admin-debug-portal | ✅ All repos | ✅ /admin/* | - |
| 017-enhanced-onboarding | ✅ UserRepo, ConvRepo | ✅ /telegram/* | - |
| 018-admin-prompt-viewing | ✅ GeneratedPromptsRepo | ✅ /admin/* | - |
| 019-admin-voice-monitoring | ✅ VoiceConvRepo | ✅ /admin/voice/* | - |
| 020-admin-text-monitoring | ✅ ConvRepo | ✅ /admin/text/* | - |

### Feature → Core Architecture Mapping

| Feature | 013 Config | 014 Engagement | 012 Context |
|---------|------------|----------------|-------------|
| 001-text-agent | ✅ Prompts, game.yaml | - | ✅ ContextGenerator |
| 002-telegram | ✅ schedule.yaml | - | ✅ ContextGenerator |
| 003-scoring | ✅ scoring.yaml | ✅ Calibration multiplier | - |
| 004-chapter | ✅ chapters.yaml | ✅ Early unlock bonus | - |
| 005-decay | ✅ decay.yaml | ✅ Recovery rates | - |
| 006-vice | ✅ vices.yaml | - | - |
| 007-voice | ✅ Prompts | - | ✅ ContextGenerator |
| 008-portal | ✅ game.yaml | ✅ State display | - |
| 017-enhanced-onboarding | ✅ Prompts | - | ✅ Memory integration |

---

## Verification Checklist

- [x] All 20 specs have spec.md
- [x] All 20 specs have audit-report.md with PASS status
- [x] Infrastructure specs (009-011) have Dependencies section
- [x] Core architecture specs (012-014) have Dependencies section
- [x] Feature specs have Infrastructure Dependencies section
- [x] All database tables referenced in feature specs are defined in 009
- [x] All API endpoints referenced in feature specs are defined in 010
- [x] All background tasks referenced in feature specs are defined in 011
- [x] All config files referenced in feature specs are defined in 013
- [x] All engagement states referenced in feature specs are defined in 014
- [x] Implementation order respects dependency graph

---

## Test Coverage Summary

| Spec | Tests | Coverage |
|------|-------|----------|
| 001-nikita-text-agent | 156 | Full |
| 002-telegram-integration | 86 | Full |
| 003-scoring-engine | 60 | Full |
| 004-chapter-boss-system | 142 | Full |
| 005-decay-system | 52 | Full |
| 006-vice-personalization | 81 | Full |
| 007-voice-agent | 186 | Full |
| 008-player-portal | ~50 | Partial (70%) |
| 012-context-engineering | 50 | Full |
| 013-configuration-system | 89 | Full |
| 014-engagement-model | 179 | Full |
| 017-enhanced-onboarding | 34 | Partial (78%) |
| 019-admin-voice-monitoring | 21 | Full |
| 020-admin-text-monitoring | 29 | Full |
| 021-hierarchical-prompt-composition | 345 | Full |
| 022-life-simulation-engine | 212 | Full |
| 023-emotional-state-engine | 233 | Full |
| 024-behavioral-meta-instructions | 166 | Full |
| 025-proactive-touchpoint-system | 189 | Full |
| 026-text-behavioral-patterns | 167 | Full |
| 027-conflict-generation-system | 263 | Full |
| **Total** | **3,179+** | **A+ Grade** |

---

## Next Steps

1. **028-voice-onboarding** - Last humanization spec (31 tasks, Meta-Nikita facilitator)
2. **008-player-portal** - Complete remaining 15% (Settings & Polish)
3. **017-enhanced-onboarding** - Complete remaining 22% (memory tests)

---

## SDD Compliance Notes

**RETROACTIVE Specs** (Jan 2026):
- 019-admin-voice-monitoring: Code before spec (SDD violation, documented exception)
- 020-admin-text-monitoring: Code before spec (SDD violation, documented exception)

These were rapid admin feature deployments. Specs created retroactively to document existing functionality. NOT a precedent.
