# Auth Validation Report: Spec 042 - Unified Pipeline Refactor

**Spec**: `/Users/yangsim/Nanoleq/sideProjects/nikita/specs/042-unified-pipeline/spec.md`
**Status**: **FAIL** — CRITICAL + HIGH issues found
**Timestamp**: 2026-02-06T00:00:00Z

---

## Summary

| Severity | Count | Items |
|----------|-------|-------|
| CRITICAL | 3 | RLS policies missing, feature flag undefined, API key handling unspecified |
| HIGH | 3 | No admin endpoint protection spec, pipeline security unclear, data isolation not verified |
| MEDIUM | 3 | RLS tests missing, feature flag rollout undefined, fallback generation rate limiting absent |
| LOW | 2 | No deprecation warnings on old pipeline, test coverage unspecified |

**Fail Criteria**: 3 CRITICAL findings = FAIL. Specification requires revision before implementation.

---

## Findings

### 1. CRITICAL: RLS Policies Undefined for New Tables

| Severity | Category | Issue | Location | Recommendation |
|----------|----------|-------|----------|----------------|
| **CRITICAL** | Data Access Control | `memory_facts` table created without RLS policy specification | spec.md:307-328 (6.1) | Add migration SQL to Phase 0 (T0.1) that includes RLS enable + policy creation |
| **CRITICAL** | Data Access Control | `ready_prompts` table created without RLS policy specification | spec.md:330-349 (6.2) | Add migration SQL to Phase 0 (T0.1) that includes RLS enable + policy creation |
| **CRITICAL** | Data Access Control | No acceptance criteria requiring RLS verification tests | tasks.md:T0.1-T0.6 (Phase 0) | Add AC: RLS enabled on both tables with user_id isolation policy |

**Details**:

The spec defines `memory_facts` and `ready_prompts` SQL schema but does NOT define Row-Level Security policies. This violates the project's auth model which uses `auth.uid() = user_id` checks on ALL user-data tables.

**Current project pattern** (from `nikita/db/migrations/versions/20251128_0002_rls_policies.py`):
```sql
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
CREATE POLICY "users_own_data" ON users
    FOR ALL USING (auth.uid() = id) WITH CHECK (auth.uid() = id);
```

**Required for new tables**:
```sql
-- memory_facts: User can only see/modify their own facts
ALTER TABLE memory_facts ENABLE ROW LEVEL SECURITY;
CREATE POLICY "memory_facts_own_data" ON memory_facts
    FOR ALL USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());

-- ready_prompts: User can only see/modify their own prompts
ALTER TABLE ready_prompts ENABLE ROW LEVEL SECURITY;
CREATE POLICY "ready_prompts_own_data" ON ready_prompts
    FOR ALL USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
```

**Impact**: Without RLS, users could access other users' memory facts and prompts via direct Supabase queries, violating OWASP Broken Access Control (A01:2021).

**Fix**: Update T0.1 migration to include `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` + policy creation for both tables.

---

### 2. CRITICAL: Feature Flag `UNIFIED_PIPELINE_ENABLED` Not Defined in Settings

| Severity | Category | Issue | Location | Recommendation |
|----------|----------|-------|----------|----------------|
| **CRITICAL** | Feature Control | Feature flag `UNIFIED_PIPELINE_ENABLED` referenced in spec but not defined in Settings | plan.md:239-248 + tasks.md:T4.4 | Add `unified_pipeline_enabled: bool = False` field to `nikita/config/settings.py` |
| **CRITICAL** | Feature Control | No rollout mechanism specified (10% → 50% → 100% mentioned in plan but no implementation details) | plan.md:251-255 | Add acceptance criteria for gradual rollout: user sampling via hash of user_id, or explicit allowlist |

**Details**:

Spec mentions feature flag in multiple places:
- plan.md:239-248: "Feature Flag Logic" showing `settings.UNIFIED_PIPELINE_ENABLED`
- plan.md:251-255: "Rollout Plan" with 10% → 50% → 100% canary rollout
- tasks.md:T4.4: Task to add flag to Settings
- tasks.md:T4.1/T4.2/T4.4: References to using the flag in agents

However, the `nikita/config/settings.py` file (verified 2026-02-06) has NO `UNIFIED_PIPELINE_ENABLED` field. Project does have other feature flags (`enable_post_processing_pipeline`), so pattern exists.

**Impact**: Implementation cannot proceed without flag defined. Rollback cannot be executed.

**Fix**:
1. Add to Settings:
```python
unified_pipeline_enabled: bool = Field(
    default=False,
    description="Enable unified pipeline (Spec 042) with gradual rollout",
)
```

2. Define rollout strategy in plan.md AC-4.4.2:
```python
# Option 1: User sampling (deterministic, reversible)
def should_use_unified_pipeline(user_id: UUID) -> bool:
    # Hash user_id, take modulo 100, compare to percentage
    hash_value = int(hashlib.md5(str(user_id).encode()).hexdigest(), 16)
    percentage = settings.unified_pipeline_rollout_percentage  # 10, 50, 100
    return (hash_value % 100) < percentage
```

---

### 3. CRITICAL: OpenAI API Key Handling Unspecified in Spec

| Severity | Category | Issue | Location | Recommendation |
|----------|----------|-------|----------|----------------|
| **CRITICAL** | Secret Management | Spec assumes OpenAI `text-embedding-3-small` embeddings but never mentions how API key is accessed | plan.md:103 + spec.md:43 (FR-001) | Add to Phase 1 AC-1.3: "SupabaseMemory reads openai_api_key from settings" + verify key is required for operation |
| **CRITICAL** | Secret Management | No error handling specified if OpenAI key is missing at runtime | tasks.md:T1.3 | Add AC-1.3.3: "If openai_api_key is None, log error and skip embedding generation, store NULL in embedding column" |

**Details**:

The spec defines embedding requirements:
- spec.md:43 (FR-001): "pgVector embeddings (1536 dimensions via `text-embedding-3-small`)"
- plan.md:103: "OpenAI `text-embedding-3-small` (1536 dims, already in settings)"
- tasks.md:T1.3: Create embedding generation with OpenAI client

However:
- No explicit AC requiring API key validation
- No error handling if key is missing (API calls will fail at runtime)
- No fallback strategy if embedding API is rate-limited/down

**Current project state**: `openai_api_key` field EXISTS in Settings (nikita/config/settings.py:50), so infrastructure is ready. But spec should document this clearly.

**Impact**:
- Embedding generation will fail silently if key is missing, causing `NULL` embeddings and broken semantic search
- Memory deduplication (AC-1.2.2) will fail because `find_similar()` needs embeddings

**Fix**: Add to T1.3 acceptance criteria:
- AC-1.3.4: "If openai_api_key missing, SupabaseMemory.add_fact() logs warning and continues (embedding=NULL)"
- AC-1.3.5: "Semantic search falls back to text-based matching if embedding is NULL"

---

### 4. HIGH: No Admin Endpoint Protection Specified

| Severity | Category | Issue | Location | Recommendation |
|----------|----------|-------|----------|----------------|
| **HIGH** | Admin Access | If new admin endpoints are added (e.g., GET /admin/ready-prompts, GET /admin/memory-facts), spec doesn't mention JWT protection | tasks.md:T4.5 (WirelinesPipelineTriggers) | Add AC-4.5.4: "If admin endpoints created, protect with get_current_admin_user() dependency from nikita/api/dependencies/auth.py" |

**Details**:

Project pattern (verified in `nikita/api/routes/admin.py`):
```python
@router.get("/admin/users")
async def list_users(admin_user_id: UUID = Depends(get_current_admin_user)):
    """Requires admin email (@silent-agents.com or allowlist)"""
```

Spec doesn't mention new admin endpoints, but Phase 4 mentions "Wire Pipeline Triggers" without specifying if debugging endpoints are needed.

**Impact**: If developers add GET /admin/ready-prompts for debugging, they might forget to add JWT protection, exposing all users' prompts.

**Fix**: Add note in plan.md § 4.6:
```markdown
### Admin Endpoint Pattern
If new endpoints added, use:
```python
async def endpoint(..., admin_id: UUID = Depends(get_current_admin_user)):
```

---

### 5. HIGH: Pipeline Trigger Security Unclear

| Severity | Category | Issue | Location | Recommendation |
|----------|----------|-------|----------|----------------|
| **HIGH** | API Security | POST /tasks/process-conversations currently uses Bearer token with telegram_webhook_secret; spec doesn't clarify if UNIFIED_PIPELINE_ENABLED flag should create new auth path | tasks.md:T4.5 | Add AC-4.5.1: "Both old and new pipelines use same auth mechanism (Bearer token with telegram_webhook_secret or JWT service account)" |
| **HIGH** | API Security | Voice webhook (call.ended) trigger auth not specified | spec.md:81 (FR-013) | Add AC to specify: ElevenLabs webhook signature validation per existing pattern in nikita/agents/voice/inbound.py |

**Details**:

Current `/tasks/` endpoints (verified in nikita/api/routes/tasks.py:33-55):
```python
async def verify_task_secret(
    authorization: str | None = Header(None),
) -> None:
    """Uses Bearer {telegram_webhook_secret}"""
    if authorization != f"Bearer {secret}":
        raise HTTPException(status_code=401)
```

This is a shared secret pattern. For Spec 042:
- Text agent trigger: pg_cron calls POST /tasks/process-conversations with Bearer token
- Voice webhook: ElevenLabs calls webhook with HMAC signature

**Impact**: If Bearer token is weak or shared across services, compromised service could trigger pipeline for any user.

**Fix**: Clarify in T4.5:
```python
# AC-4.5.1: pg_cron path uses Bearer {telegram_webhook_secret}
# AC-4.5.2: Voice webhook validated via ElevenLabs HMAC signature (existing pattern)
# Both paths call PipelineOrchestrator.process(conversation_id)
```

---

### 6. HIGH: No Data Access Pattern Verification

| Severity | Category | Issue | Location | Recommendation |
|----------|----------|-------|----------|----------------|
| **HIGH** | Broken Access Control | SupabaseMemory.search() doesn't specify user_id filtering; assumes caller passes it but no enforcement | plan.md:98 + tasks.md:T1.1.3 | Add AC-1.1.4: "SupabaseMemory methods ALWAYS filter by user_id; no method returns cross-user data" |
| **HIGH** | Broken Access Control | ReadyPromptRepository.get_current(user_id, platform) requires caller to pass correct user_id; no validation | tasks.md:T0.6.1 | Add AC-0.6.4: "get_current() validates user_id parameter matches request context (if JWT-based)" |

**Details**:

Spec doesn't show implementation, but memory/ready_prompts access must be isolated:
- `SupabaseMemory.search(user_id, query)` - returns facts for user_id only
- `ReadyPromptRepository.get_current(user_id, platform)` - returns prompts for user_id only

**Risk**: If agent code calls:
```python
# WRONG: Could expose user123's facts
prompt = await repo.get_current(user_id_from_url, 'text')

# RIGHT: Must validate user_id matches request context
current_user = await get_current_user_id(credentials)
prompt = await repo.get_current(current_user, 'text')
```

**Impact**: OWASP A01:2021 Broken Authentication - user can specify another user's ID in URL/query and access their data.

**Fix**: Add to specs Phase 4 (T4.1/T4.2):
- AC-4.1.4: "Text agent calls `repo.get_current(user_id=request.user_id, platform='text')` where user_id extracted from JWT"
- AC-4.2.2: "Voice context loads prompts filtered by user_id from conversation context"

---

### 7. MEDIUM: RLS Test Coverage Not Specified

| Severity | Category | Issue | Location | Recommendation |
|----------|----------|-------|----------|----------------|
| **MEDIUM** | Test Coverage | Phase 0 migration doesn't include acceptance criteria for RLS verification tests | tasks.md:T0.1-T0.6 | Add T0.7: "RLS Integration Tests" with ACs: verify users isolated, service role bypasses, anon blocked |

**Details**:

Project has `tests/db/integration/test_rls_policies.py` with 13 tests verifying:
- RLS enabled on each table
- Policies exist and reference auth.uid()
- Service role bypasses RLS
- Users cannot see other users' data

Spec 042 doesn't mention this test coverage for new tables.

**Fix**: Add Phase 0 task:
```markdown
### T0.7: RLS Policy Tests
- AC-0.7.1: Create tests/db/integration/test_memory_facts_rls.py
  - Verify RLS enabled
  - Verify policy uses user_id = auth.uid()
  - Service role can read all facts
  - Anon role blocked
- AC-0.7.2: Same for ready_prompts table
```

---

### 8. MEDIUM: Feature Flag Rollout Mechanism Undefined

| Severity | Category | Issue | Location | Recommendation |
|----------|----------|-------|----------|----------------|
| **MEDIUM** | Feature Control | "10% → 50% → 100% rollout" mentioned in plan but no implementation strategy | plan.md:251-255 | Add T4.4.2: Define rollout mechanism (user sampling, explicit allowlist, or percentage field) |
| **MEDIUM** | Feature Control | No monitoring/instrumentation for feature flag state | plan.md:251-255 | Add AC-4.4.3: "Log when unified_pipeline_enabled checked, include user_id and result for observability" |

**Details**:

Spec mentions gradual rollout but doesn't define HOW:
- Option 1: Hash-based sampling (deterministic, reversible)
- Option 2: Explicit allowlist (fine control)
- Option 3: Percentage field in Settings (requires redeployment)

```python
# Example: Hash-based (deterministic)
def should_use_unified_pipeline(user_id: UUID) -> bool:
    if not settings.unified_pipeline_enabled:
        return False

    # Rollout percentage (10, 50, 100)
    hash_val = int(hashlib.md5(str(user_id).encode()).hexdigest(), 16)
    return (hash_val % 100) < settings.unified_pipeline_rollout_percentage
```

**Impact**: Without definition, team will guess implementation, potentially breaking existing users.

**Fix**: Add to T4.4:
- AC-4.4.2: "Rollout uses hash-based sampling: hash(user_id) % 100 < rollout_percentage"
- AC-4.4.3: "Settings has unified_pipeline_rollout_percentage: 0-100 (default 0)"

---

### 9. MEDIUM: Fallback Prompt Generation Rate Limiting Absent

| Severity | Category | Issue | Location | Recommendation |
|----------|----------|-------|----------|----------------|
| **MEDIUM** | API Abuse Prevention | Fallback prompt generation (FR-014) can be triggered on every message if no ready_prompt exists; no rate limiting | plan.md:243 (FR-014) + tasks.md:T4.1.2 | Add AC-4.1.4: "Fallback generation logged with timestamp; if >1 per minute for user, return cached version instead of regenerating" |

**Details**:

Spec defines:
- AC-4.1.2 (tasks.md): "Falls back to on-the-fly generation if no prompt exists"
- FR-014 (spec.md:84): "If no pre-built prompt exists for a user, generate on-the-fly"

**Risk**: If ready_prompts lookup fails or record deleted, every message triggers Haiku generation:
```python
# VULNERABLE: Attacker sends 100 messages → 100 Haiku calls → $0.10 cost
if not prompt:
    prompt = await generate_fallback_prompt(user_id)  # Haiku API call!
```

**Impact**: Cost explosion + DoS vector (attacker floods user with messages to inflate API costs).

**Fix**: Add to T4.1:
```markdown
- AC-4.1.4: "Fallback generation cached in-memory for 5 min per user to prevent API flooding"
- AC-4.1.5: "If fallback generated >3x in 1 hour for user, return warning + old prompt instead"
```

---

### 10. LOW: No Deprecation Warnings on Old Pipeline Cleanup

| Severity | Category | Issue | Location | Recommendation |
|----------|----------|-------|----------|----------------|
| **LOW** | Code Quality | Phase 5 cleanup deletes old pipeline but doesn't mention deprecation warnings during Phase 4 | plan.md:263-298 (Phase 5) | Add Phase 4 AC: "Old pipeline (ContextEngine) imported with deprecation warnings, directing to migration guide" |

**Details**:

Good practice: Add warnings BEFORE deletion to help users/developers.

```python
# nikita/context_engine/__init__.py
import warnings

def __getattr__(name):
    warnings.warn(
        "nikita.context_engine is deprecated (Spec 042). "
        "Use nikita.pipeline instead. "
        "See: /docs/guides/pipeline-migration.md",
        DeprecationWarning,
        stacklevel=2,
    )
    # Return stub...
```

---

### 11. LOW: Test Coverage Targets Not Specified

| Severity | Category | Issue | Location | Recommendation |
|----------|----------|-------|----------|----------------|
| **LOW** | Test Quality | Plan mentions "440 new tests" but doesn't specify coverage % or critical paths | plan.md:9 + verification-plan | Add target: "Memory functions 100%, pipeline stages 90%+, repositories 95%+" |

---

## Auth Flow Analysis

**Primary Method**: JWT (Supabase) + RLS
- User auth: Bearer token with HS256 (Supabase JWT)
- Admin auth: JWT with email domain check (@silent-agents.com)
- Service account: Bearer token (Supabase service role)
- Internal tasks: Bearer token with shared secret

**Session Type**: Stateless JWT (no server-side session store)

**Token Handling**:
- Decoded in `nikita/api/dependencies/auth.py`
- User ID extracted from `sub` claim
- Email extracted from `email` claim for admin check
- RLS filters at database level using `auth.uid()`

---

## Role & Permission Matrix

### New Tables (Spec 042)

| Entity | memory_facts | ready_prompts | Notes |
|--------|---------|---------------|-------|
| **User (own)** | ✓ Read/Write | ✓ Read/Write | Via RLS: user_id = auth.uid() |
| **User (other)** | ✗ Blocked | ✗ Blocked | RLS prevents all access |
| **Service Role** | ✓ Read/Write | ✓ Read/Write | Bypasses RLS (admin operations) |
| **Anon Role** | ✗ Blocked | ✗ Blocked | No policies, all ops denied |

### Admin Endpoints (if added)

| Endpoint | Requires | Protected By |
|----------|----------|--------------|
| GET /admin/ready-prompts | Admin email | `get_current_admin_user()` |
| GET /admin/memory-facts | Admin email | `get_current_admin_user()` |
| POST /tasks/process-conversations | Service account | Bearer token |
| POST /voice/webhook | ElevenLabs | HMAC signature |

---

## Protected Resources

| Resource | Auth Required | Allowed Roles | Notes |
|----------|--------|------------|-------|
| /memory_facts (DB read) | ✓ JWT | User (own) | RLS-protected at DB level |
| /ready_prompts (DB read) | ✓ JWT | User (own) | RLS-protected at DB level |
| /tasks/process-conversations | ✓ Bearer token | Service account | Internal only, pg_cron trigger |
| /voice/webhook (call.ended) | ✓ HMAC signature | ElevenLabs | External webhook |
| /admin/* | ✓ JWT (admin) | Admin (@silent-agents.com) | Admin portal endpoints |

---

## Security Checklist

- [✓] Row Level Security enabled - **FOR NEW TABLES**: NOT DEFINED
- [✓] Account lockout policy - N/A (OAuth via Supabase)
- [✓] Session invalidation on logout - JWT expiration (Supabase default)
- [✗] Rate limiting on memory operations - **MISSING for fallback generation**
- [✓] CSRF protection - N/A (REST API, no cookies)
- [✓] Security headers - Supabase handles (not app-level concern)
- [✓] Admin authentication - Domain + allowlist
- [✓] Webhook signature validation - Telegram + ElevenLabs (existing pattern)

---

## Recommendations

### Blocker Issues (Fix Before Implementation)

1. **CRITICAL [P0]**: Update T0.1 migration to include RLS enable + policy creation
   ```sql
   ALTER TABLE memory_facts ENABLE ROW LEVEL SECURITY;
   CREATE POLICY "memory_facts_own_data" ON memory_facts
       FOR ALL USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
   ```

2. **CRITICAL [P0]**: Add `unified_pipeline_enabled: bool` field to Settings with rollout_percentage
   ```python
   unified_pipeline_enabled: bool = Field(default=False, ...)
   unified_pipeline_rollout_percentage: int = Field(default=0, ge=0, le=100)
   ```

3. **CRITICAL [P0]**: Define feature flag rollout mechanism in plan.md (hash-based sampling recommended)

4. **CRITICAL [P0]**: Document OpenAI API key requirement + error handling in T1.3 ACs

### Must-Have Before Phase 0 Deployment

5. **HIGH [P1]**: Add RLS test coverage (T0.7 task)
   - Verify users isolated
   - Verify service role bypass
   - Verify anon blocked

6. **HIGH [P1]**: Clarify pipeline trigger auth in T4.5
   - pg_cron uses Bearer token
   - Voice webhook uses ElevenLabs HMAC
   - Both call unified orchestrator

7. **HIGH [P1]**: Add data access pattern validation in T1.1 + T0.6
   - All repository methods must filter by user_id
   - Caller must pass correct user_id from JWT context

### Before Phase 4 (Agent Integration)

8. **MEDIUM [P2]**: Define fallback prompt generation rate limiting in T4.1
   - Cache for 5 min per user
   - Alert if >3 fallbacks in 1 hour

9. **MEDIUM [P2]**: Add admin endpoint protection note to plan
   - Use `get_current_admin_user()` for any new debug endpoints

10. **LOW [P3]**: Add deprecation warnings to old pipeline in Phase 4
    - Help developers migrate existing code

---

## Conclusion

**Status**: **FAIL** — Specification has 3 CRITICAL findings that must be resolved:

1. ✗ RLS policies not defined for memory_facts, ready_prompts
2. ✗ Feature flag `UNIFIED_PIPELINE_ENABLED` not in Settings
3. ✗ OpenAI API key handling unspecified in spec

**Path to PASS**:

1. Update T0.1 migration to include RLS for both tables (spec.md § 6 → plan.md § Phase 0)
2. Add Settings fields for `unified_pipeline_enabled` + `unified_pipeline_rollout_percentage`
3. Define feature flag rollout mechanism (hash-based sampling) in plan.md
4. Add T1.3 ACs for OpenAI key validation + error handling
5. Re-run audit → Should PASS

**Estimated remediation time**: 2-3 hours (1h spec update + 1-2h implementation of Settings + RLS migration)

---

## Files to Update

1. `specs/042-unified-pipeline/spec.md` - Add RLS policy definitions to § 6
2. `specs/042-unified-pipeline/plan.md` - Clarify feature flag rollout, Phase 4 endpoint protection
3. `specs/042-unified-pipeline/tasks.md` - Add T0.7 (RLS tests), update T0.1/T1.3/T4.5 ACs
4. `nikita/config/settings.py` - Add `unified_pipeline_enabled` + `unified_pipeline_rollout_percentage` fields (Phase 4 task)
