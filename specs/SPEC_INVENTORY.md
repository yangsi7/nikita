# Nikita Spec Inventory

**Generated**: 2025-11-28
**Total Specs**: 11 (1 implemented, 3 infrastructure, 7 features)

---

## Spec Matrix

| # | Spec | Type | Status | Depends On | Blocks |
|---|------|------|--------|------------|--------|
| 001 | nikita-text-agent | Feature | ✅ IMPLEMENTED | - | 002, 007 |
| 009 | database-infrastructure | **Infra** | spec.md | Supabase | All features |
| 010 | api-infrastructure | **Infra** | spec.md | 009 | 002, 007, 008 |
| 011 | background-tasks | **Infra** | spec.md | 009, 010 | 002, 005, 008 |
| 003 | scoring-engine | Feature | spec.md | 009 | 004, 005, 006 |
| 004 | chapter-boss-system | Feature | spec.md | 009, 003 | 008 |
| 005 | decay-system | Feature | spec.md | 009, 011, 003 | 008 |
| 006 | vice-personalization | Feature | spec.md | 009, 003 | 007 |
| 002 | telegram-integration | Feature | spec.md | 009, 010, 011, 001 | - |
| 007 | voice-agent | Feature | spec.md | 009, 010, 003-006 | - |
| 008 | player-portal | Feature | spec.md | 009, 010, 011, 003-006 | - |

---

## Implementation Order (Infra-First)

### Phase A: Infrastructure Foundation
1. **009-database-infrastructure** - Repository pattern, migrations, RLS
2. **010-api-infrastructure** - FastAPI routes, auth, middleware
3. **011-background-tasks** - pg_cron, Edge Functions

### Phase B: Core Game Engine
4. **003-scoring-engine** - Core mechanic (4 metrics, deltas)
5. **004-chapter-boss-system** - Progression + win/lose conditions
6. **005-decay-system** - Daily decay + game over
7. **006-vice-personalization** - Personality adaptation

### Phase C: Platform Integration
8. **002-telegram-integration** - Primary user interface

### Phase D: Advanced Features
9. **007-voice-agent** - Second modality (ElevenLabs)
10. **008-player-portal** - Dashboard + voice call initiation

---

## Infrastructure Coverage

### 009-database-infrastructure
**Tables Defined**: users, user_metrics, user_vice_preferences, conversations, score_history, daily_summaries, pending_responses, job_history
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
- `apply-daily-decay` (005)
- `deliver-responses` (002)
- `generate-daily-summaries` (008)
**Used By**: 002, 005, 008

---

## Cross-Reference Validation

### Feature → Infrastructure Mapping

| Feature | 009 DB | 010 API | 011 Tasks |
|---------|--------|---------|-----------|
| 002-telegram | ✅ UserRepo, ConvRepo | ✅ /telegram/* | ✅ deliver-responses |
| 003-scoring | ✅ UserRepo, ScoreHistRepo | - | - |
| 004-chapter | ✅ UserRepo | - | - |
| 005-decay | ✅ UserRepo | - | ✅ apply-decay |
| 006-vice | ✅ VicePreferenceRepo | - | - |
| 007-voice | ✅ ConvRepo, UserRepo | ✅ /voice/* | - |
| 008-portal | ✅ All repos | ✅ /portal/* | ✅ generate-summaries |

---

## Verification Checklist

- [x] All 11 specs have spec.md
- [x] Infrastructure specs (009-011) have Dependencies section
- [x] Feature specs (002-008) have Infrastructure Dependencies section
- [x] All database tables referenced in feature specs are defined in 009
- [x] All API endpoints referenced in feature specs are defined in 010
- [x] All background tasks referenced in feature specs are defined in 011
- [x] Implementation order respects dependency graph

---

## Next Steps (SDD Workflow)

For each spec in implementation order:
1. `/plan {spec}/spec.md` → Generate implementation plan
2. `/tasks {spec}/plan.md` → Generate task breakdown
3. `/audit {spec}` → Validate consistency

**Ready for Phase A**: Infrastructure implementation can begin.
