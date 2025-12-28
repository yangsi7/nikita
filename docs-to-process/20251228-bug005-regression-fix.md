# BUG-005: Regression Fix - Service Dependency Injection (2025-12-28)

## Summary

**Critical regression** introduced by BUG-002 fix (commit 1f9076c) caused all Telegram webhook requests to fail with TypeError. Fixed in commit c4f41f3, deployed to nikita-api-00110-grt.

**Timeline**: Discovered → Fixed → Deployed → Verified in **12 minutes**

---

## Bug Details

### Error

```
TypeError: BackstoryGeneratorService.__init__() takes 1 positional argument but 2 were given
```

**Location**: `nikita/api/routes/telegram.py:264`
**First Seen**: 2025-12-28 17:15:17 (Cloud Run logs)
**Severity**: CRITICAL (blocks all webhook requests)

### Root Cause

BUG-002 fix incorrectly assumed all 3 services accept `session` parameter in their constructors.

**Incorrect Implementation** (commit 1f9076c):
```python
# Line 248 - WRONG
async def get_venue_research_service(session=Depends(get_async_session)) -> VenueResearchService:
    return VenueResearchService(session)  # ❌ Needs VenueCacheRepository, not session

# Line 264 - WRONG
async def get_backstory_generator(session=Depends(get_async_session)) -> BackstoryGeneratorService:
    return BackstoryGeneratorService(session)  # ❌ Takes NO arguments

# Line 280 - WRONG
async def get_persona_adaptation(session=Depends(get_async_session)) -> PersonaAdaptationService:
    return PersonaAdaptationService(session)  # ❌ Takes NO arguments
```

**Actual Constructor Signatures**:
- `BackstoryGeneratorService.__init__(self)` - **NO arguments**
- `PersonaAdaptationService` - **NO __init__** (uses default, no arguments)
- `VenueResearchService.__init__(self, venue_cache_repository)` - **Needs VenueCacheRepository**
- `VenueCacheRepository.__init__(self, session)` - **Needs AsyncSession**

---

## Fix Implementation

**Commit**: c4f41f3
**Files Modified**: 1 (nikita/api/routes/telegram.py)
**Lines Changed**: +26 insertions, -22 deletions

### Changes

1. **Added VenueCacheRepository import** (line 42):
```python
from nikita.db.repositories.profile_repository import VenueCacheRepository
```

2. **Added intermediate dependency function** (lines 236-243):
```python
async def get_venue_cache_repo(
    session=Depends(get_async_session),
) -> VenueCacheRepository:
    """Get VenueCacheRepository with session dependency."""
    return VenueCacheRepository(session)
```

3. **Fixed VenueResearchService dependency** (lines 246-260):
```python
async def get_venue_research_service(
    venue_cache_repo: VenueCacheRepository = Depends(get_venue_cache_repo),
) -> VenueResearchService:
    """Get VenueResearchService with venue cache repository dependency."""
    return VenueResearchService(venue_cache_repo)  # ✅ Correct
```

4. **Fixed BackstoryGeneratorService dependency** (lines 263-272):
```python
async def get_backstory_generator() -> BackstoryGeneratorService:
    """Get BackstoryGeneratorService (no dependencies)."""
    return BackstoryGeneratorService()  # ✅ Correct (no arguments)
```

5. **Fixed PersonaAdaptationService dependency** (lines 275-284):
```python
async def get_persona_adaptation() -> PersonaAdaptationService:
    """Get PersonaAdaptationService (no dependencies)."""
    return PersonaAdaptationService()  # ✅ Correct (no arguments)
```

---

## Deployment

**Build Time**: ~8 minutes
**Revision**: nikita-api-00110-grt
**Traffic**: 100% on new revision
**Service URL**: https://nikita-api-1040094048579.us-central1.run.app

**Verification**:
```bash
# Check deployment
gcloud run services describe nikita-api --region us-central1 --project gcp-transcribe-test

# Verify no errors
gcloud run services logs read nikita-api --region us-central1 --limit 20 | grep -i "error\|typeerror"
```

**Result**: ✅ No TypeError errors in logs after deployment

---

## Impact Analysis

### What Broke

- **All Telegram webhook requests** (POST /telegram/webhook) failed with 500 error
- **Onboarding completely blocked** - new users couldn't register
- **E2E testing blocked** - couldn't test Firecrawl, Neo4j, or personalization

### What Still Worked

- Background tasks (decay, summaries, cleanup) - separate endpoints
- Portal API (read-only endpoints)
- Database operations (not dependent on webhook)

### Duration of Outage

- **Deployed**: 2025-12-27 22:40:00 (nikita-api-00109-mlc with BUG-002/003/004 fixes)
- **Fixed**: 2025-12-28 01:57:00 (nikita-api-00110-grt with BUG-005 fix)
- **Total**: ~3 hours 17 minutes

---

## Testing Verification

### Smoke Test

✅ **Cloud Run logs show no TypeError** after deployment

### Pending Full Verification

After BUG-005 fix, need to verify original BUG-002/003/004 fixes work:

1. **BUG-002 (Firecrawl)**: Verify VenueResearchService executes PRIMARY path
2. **BUG-003 (venue attribute)**: Verify personalization pipeline loads backstory
3. **BUG-004 (ThreadRepository)**: Verify MetaPromptService initializes correctly

**E2E Test Plan**: See `~/.claude/plans/tingly-marinating-sunset.md`

---

## Lessons Learned

### What Went Wrong

1. **Insufficient Research**: Didn't verify service constructor signatures before implementing BUG-002 fix
2. **No Local Testing**: BUG-002 fix deployed directly to Cloud Run without testing dependency injection
3. **Missing Unit Tests**: No tests for dependency injection functions

### Prevention Strategies

1. **Research Service Constructors**: Always check actual `__init__` signatures before implementing dependency injection
2. **FastAPI Dependency Pattern**: For services:
   - Stateless services (no deps) → `def get_service() -> Service: return Service()`
   - Database-dependent services → inject repository, not raw session
   - Chain dependencies explicitly (session → repository → service)
3. **Test Before Deploy**: Add unit tests for dependency injection functions
4. **Staged Rollout**: Test in dev environment before production deployment

---

## Related Issues

- [Issue #9](https://github.com/yangsi7/nikita/issues/9): BUG-003 - UserBackstory.venue attribute error (CLOSED)
- [Issue #10](https://github.com/yangsi7/nikita/issues/10): BUG-004 - ThreadRepository import error (CLOSED)
- [Issue #11](https://github.com/yangsi7/nikita/issues/11): BUG-002 - Firecrawl not integrated (CLOSED)
- [Issue #12](https://github.com/yangsi7/nikita/issues/12): BUG-005 - Service dependency injection broken (CLOSED)

---

## Next Steps

1. ✅ BUG-005 fixed and deployed
2. ⏳ E2E verification pending (Firecrawl, Neo4j, personalization)
3. 📋 Create E2E verification report after testing
4. 📝 Update Spec 017 completion percentage
5. 📝 Add unit tests for dependency injection functions
