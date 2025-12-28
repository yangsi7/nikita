# E2E Test Clean Slate - Critical Findings (2025-12-27)

## Test Results Summary

**Overall**: Phases 0-5 ✅ PASS, Phase 6 ❌ BLOCKED

### ✅ Verified Functionality
- Phase -1: User deletion via psql ✅
- Phase 0: OTP registration flow ✅
- Phase 1: FR-001 Onboarding intro ✅
- Phase 2: Profile collection (5 questions) ✅
- Phase 3: FR-004 Venue research **fallback** ✅ (but Firecrawl primary path NOT tested)
- Phase 4: Custom backstory accepted and persisted ✅
- Phase 5: FR-008 First Nikita message auto-sent ✅

### ❌ Critical Bugs Found

#### BUG-002: Firecrawl Not Actually Being Called
**Severity**: HIGH
**Evidence**:
- Logs show NO Firecrawl API calls during venue research (21:47:47-21:47:48)
- Immediate fallback to custom backstory (1 second)
- **Firecrawl credentials verified**:
  - GCP secret `nikita-firecrawl-key` = `fc-fbf3d554863348fb9a7c54436ad069c9` ✅
  - Cloud Run env var configured ✅
  - `.mcp.json` has same key ✅

**Root Cause**: Unknown - Firecrawl client may not be instantiated, or integration disabled/mocked

**Impact**: Primary venue research path UNTESTED. Only fallback was verified.

---

#### BUG-003: UserBackstory Model Attribute Error
**Severity**: CRITICAL
**Error**: `'UserBackstory' object has no attribute 'venue'`
**Location**: `nikita.meta_prompts.service` @ 21:50:05
**File**: Unknown (accessing `backstory.venue` instead of `backstory.venue_name`)

**Evidence**:
```
2025-12-27 21:50:05 - nikita.meta_prompts.service - WARNING - Failed to load profile/backstory for user c539927d-6d0c-42ea-b1c8-a3169e4421b0: 'UserBackstory' object has no attribute 'venue'
```

**Impact**:
- Personalization pipeline fails
- Falls back to legacy prompt (loses custom backstory context)
- Memory integration blocked

---

#### BUG-004: ThreadRepository Import Error
**Severity**: CRITICAL
**Error**: `cannot import name 'ThreadRepository' from 'nikita.db.repositories.thread_repository'`
**Location**: `nikita.agents.text.agent` @ 21:50:06
**File**: `nikita.db.repositories.thread_repository.py`

**Evidence**:
```
2025-12-27 21:50:06 - nikita.agents.text.agent - WARNING - MetaPromptService failed, using legacy prompt: cannot import name 'ThreadRepository' from 'nikita.db.repositories.thread_repository' (/app/nikita/db/repositories/thread_repository.py)
```

**Impact**:
- MetaPromptService fails completely
- Falls back to legacy prompt
- Memory integration untested
- Bot failed to respond to message ID 19369 (>110s timeout)

---

#### BUG-005: Onboarding UX Deadlock
**Severity**: MEDIUM
**Symptom**: User waits for bot, bot waits for user

**Flow**:
1. User sends drug tolerance "3"
2. Bot says "One moment while I set things up..." (implies automatic progression)
3. Bot updates state to `venue_research`
4. **BUT**: Handler waits for NEXT user message to trigger venue research
5. User waits for bot (as instructed by "One moment...")
6. Deadlock

**Solution**: Either auto-trigger venue research OR change message to ask user to continue

---

## Database State Verification (Phase 7 - PARTIAL)

**Via psql**:
```sql
SELECT current_step, updated_at FROM onboarding_states WHERE telegram_id=746410893;
-- Result: venue_research | 2025-12-27 21:39:27.750613+00

SELECT COUNT(*) FROM user_profiles WHERE id IN (SELECT id FROM users WHERE telegram_id=746410893);
-- Expected: 1 (needs verification)

SELECT COUNT(*) FROM user_backstories WHERE user_id IN (SELECT id FROM users WHERE telegram_id=746410893);
-- Expected: 1 (needs verification)

SELECT COUNT(*) FROM user_vice_preferences WHERE user_id IN (SELECT id FROM users WHERE telegram_id=746410893);
-- Expected: 8 (needs verification)
```

**Status**: Not yet executed

---

## Firecrawl Integration Status

**Configuration**:
- ✅ API Key in GCP Secret Manager: `fc-fbf3d554863348fb9a7c54436ad069c9`
- ✅ Cloud Run env var `FIRECRAWL_API_KEY` set correctly
- ✅ `.mcp.json` has matching credentials
- ❌ No evidence of Firecrawl calls in logs
- ❌ Immediate fallback suggests NOT integrated

**Next Steps**:
1. Verify `VenueResearchService` is instantiated in `OnboardingHandler`
2. Check if Firecrawl client is mocked/disabled
3. Add logging to venue research to trace execution
4. Test Firecrawl API directly to ensure credentials work

---

## Memory Integration (Phase 6) - BLOCKED

**Status**: ❌ FAILED
**Reason**: MetaPromptService errors prevent bot from generating response
**Message Sent**: 21:49:14 - "Just thinking about that night at Hive Club..."
**Expected**: Bot response with contextual memory recall
**Actual**: No response after 110s (timeout)

**Errors**:
- UserBackstory attribute error
- ThreadRepository import error

---

## Acceptance Criteria Status

| FR | Name | Status | Evidence |
|----|------|--------|----------|
| FR-001 | Personalization Guide | ✅ PASS | Message ID 19351 |
| FR-002 | Profile Collection | ✅ PASS | 5 questions answered |
| FR-003 | Drug Tolerance | ✅ PASS | Validated 1-5 scale |
| FR-004 | Venue Research Fallback | ⚠️ PARTIAL | Fallback works, PRIMARY path untested |
| FR-005 | Scenario Generation | ❌ FAIL | Firecrawl not called |
| FR-006 | Custom Backstory | ✅ PASS | Message ID 19366 accepted |
| FR-007 | Persona Adaptation | ⏸️ UNKNOWN | Depends on working prompts |
| FR-008 | First Nikita Message | ✅ PASS | Message ID 19367-19368 auto-sent |
| FR-009 | State Persistence | ✅ PASS | DB state at venue_research |
| FR-010 | Existing User Bypass | ✅ PASS | (Verified in previous test 2025-12-27) |
| FR-011 | Mandatory Completion | ✅ PASS | No skip allowed |
| FR-012 | Profile Gate Check | ✅ PASS | (Verified in previous test 2025-12-27) |
| FR-013 | Graphiti Memory Loading | ❌ BLOCKED | Import/attribute errors |
| FR-014 | Conversation Summaries | ❌ BLOCKED | MetaPromptService failed |
| FR-015 | Per-Conversation Prompts | ❌ BLOCKED | Legacy fallback used |

**Spec 017 Progress**: ~65% verified (11/17 FRs tested, 6 blocked by bugs)

---

## Next Actions (Priority Order)

1. **CRITICAL**: Fix BUG-003 (UserBackstory.venue → venue_name)
2. **CRITICAL**: Fix BUG-004 (ThreadRepository import)
3. **HIGH**: Fix BUG-002 (Enable actual Firecrawl venue search)
4. **MEDIUM**: Fix BUG-005 (Onboarding UX deadlock)
5. **VERIFY**: Re-run E2E test with fixes deployed
6. **TEST**: Firecrawl primary path (venue scenarios)
7. **COMPLETE**: Phase 6-9 (Memory, DB verification, logs, report)

---

## Spec 017 Status Update

**Previous**: 95% complete
**Actual**: ~65% verified, 3 critical bugs blocking 6 FRs

**Recommendation**: Mark Spec 017 as **BLOCKED** until bugs fixed, then re-verify.
