# Nikita Spec Inventory

**Generated**: 2025-11-28
**Updated**: 2025-12-11 (006-vice-personalization complete)
**Total Specs**: 14 (13 implemented, 1 TODO)

---

## Spec Matrix

| # | Spec | Type | Status | Depends On | Blocks |
|---|------|------|--------|------------|--------|
| 001 | nikita-text-agent | Feature | ✅ IMPLEMENTED (156 tests) | 012 | 002, 007 |
| 009 | database-infrastructure | **Infra** | ✅ IMPLEMENTED | Supabase | All features |
| 010 | api-infrastructure | **Infra** | ✅ IMPLEMENTED | 009 | 002, 007, 008 |
| 011 | background-tasks | **Infra** | ✅ IMPLEMENTED | 009, 010 | 002, 005, 008 |
| **012** | **context-engineering** | **Feature** | ✅ IMPLEMENTED (50 tests) | 009, 013, 014 | 001, 002, 007 |
| **013** | **configuration-system** | **Feature** | ✅ IMPLEMENTED (89 tests) | - | 012, 003-006 |
| **014** | **engagement-model** | **Feature** | ✅ IMPLEMENTED (179 tests) | 009, 013 | 012, 003, 005 |
| 003 | scoring-engine | Feature | ✅ IMPLEMENTED (60 tests) | 009, 013, 014 | 004, 005, 006 |
| 004 | chapter-boss-system | Feature | ✅ IMPLEMENTED (142 tests) | 009, 013, 003, 014 | 008 |
| 005 | decay-system | Feature | ✅ IMPLEMENTED (44 tests) | 009, 011, 013, 014, 003 | 008 |
| 006 | vice-personalization | Feature | ✅ IMPLEMENTED (70 tests) | 009, 013, 003 | 007 |
| 002 | telegram-integration | Feature | ✅ DEPLOYED (74 tests) | 009, 010, 011, 001, 012 | - |
| 007 | voice-agent | Feature | ❌ TODO | 009, 010, 012, 003-006 | - |
| 008 | player-portal | Feature | ✅ WORKING (2025-12-10) | 009, 010, 011, 003-006 | - |

---

## Implementation Order (Updated 2025-12-02)

### Phase A: Infrastructure Foundation
1. **009-database-infrastructure** - Repository pattern, migrations, RLS
2. **010-api-infrastructure** - FastAPI routes, auth, middleware
3. **011-background-tasks** - pg_cron, Edge Functions

### Phase B: Core System Architecture (NEW)
4. **013-configuration-system** - Hybrid layered config (YAML + prompts + code)
5. **014-engagement-model** - Calibration detection, clinginess/neglect algorithms
6. **012-context-engineering** - 6-stage context generation pipeline

### Phase C: Core Game Engine
7. **003-scoring-engine** - Core mechanic (4 metrics, deltas, **calibration multiplier**)
8. **004-chapter-boss-system** - Progression + win/lose (**2-3 week timeline**)
9. **005-decay-system** - Hourly decay + game over (**chapter-dependent recovery**)
10. **006-vice-personalization** - Personality adaptation

### Phase D: Platform Integration
11. **002-telegram-integration** - Primary user interface

### Phase E: Advanced Features
12. **007-voice-agent** - Second modality (ElevenLabs)
13. **008-player-portal** - Dashboard + voice call initiation

---

## Infrastructure Coverage

### 009-database-infrastructure
**Tables Defined**: users, user_metrics, user_vice_preferences, conversations, score_history, daily_summaries, pending_responses, job_history, **engagement_history**
**Used By**: ALL features

### 010-api-infrastructure
**Endpoints Defined**:
- `/api/v1/telegram/webhook` (002)
- `/api/v1/telegram/set-webhook` (002)
- `/api/v1/voice/server-tool` (007)
- `/api/v1/voice/callback` (007)
- `/api/v1/portal/stats/{user_id}` (008)
- `/api/v1/portal/conversations/{user_id}` (008)
- `/api/v1/portal/daily-summary/{user_id}/{date}` (008)
**Used By**: 002, 007, 008

### 011-background-tasks
**Jobs Defined**:
- `apply-hourly-decay` (005) - **Updated: hourly instead of daily**
- `deliver-responses` (002)
- `generate-daily-summaries` (008)
**Used By**: 002, 005, 008

---

## Core System Architecture Coverage (NEW)

### 012-context-engineering
**Components Defined**:
- ContextGenerator (6-stage pipeline)
- PlayerProfile, TemporalContext, MemoryContext, NikitaState dataclasses
- Meta-prompt specification
- Token budget allocation (~3700 tokens)
**Used By**: 001, 002, 007

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
| 012-context-engineering | ✅ UserRepo, ConvRepo, EngagementRepo | - | - |
| 013-configuration-system | - | - | - |
| 014-engagement-model | ✅ UserRepo, EngagementHistRepo | - | - |
| 002-telegram | ✅ UserRepo, ConvRepo | ✅ /telegram/* | ✅ deliver-responses |
| 003-scoring | ✅ UserRepo, ScoreHistRepo, EngagementHistRepo | - | - |
| 004-chapter | ✅ UserRepo, EngagementHistRepo | - | - |
| 005-decay | ✅ UserRepo, EngagementHistRepo | - | ✅ apply-hourly-decay |
| 006-vice | ✅ VicePreferenceRepo | - | - |
| 007-voice | ✅ ConvRepo, UserRepo | ✅ /voice/* | - |
| 008-portal | ✅ All repos | ✅ /portal/* | ✅ generate-summaries |

### Feature → Core Architecture Mapping (NEW)

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

---

## Verification Checklist

- [x] All 14 specs have spec.md
- [x] Infrastructure specs (009-011) have Dependencies section
- [x] Core architecture specs (012-014) have Dependencies section
- [x] Feature specs (002-008) have Infrastructure Dependencies section
- [x] All database tables referenced in feature specs are defined in 009
- [x] All API endpoints referenced in feature specs are defined in 010
- [x] All background tasks referenced in feature specs are defined in 011
- [x] All config files referenced in feature specs are defined in 013
- [x] All engagement states referenced in feature specs are defined in 014
- [x] Implementation order respects dependency graph

---

## Next Steps (SDD Workflow)

For each spec in implementation order:
1. `/plan {spec}/spec.md` → Generate implementation plan
2. `/tasks {spec}/plan.md` → Generate task breakdown
3. `/audit {spec}` → Validate consistency

**Ready for Phase A**: Infrastructure implementation can begin.
