# Tasks: 010-API-Infrastructure

## Overview

User-story-organized task list for API infrastructure implementation.

**Spec**: `spec.md`
**Plan**: `plan.md`
**Total Tasks**: 12

---

## US-001: Portal Authentication (P1)

### T1.1: Create Supabase JWT Verification Module
- **Status**: [ ] Pending
- **File**: `nikita/api/middleware/auth.py`
- **Dependencies**: None
- **ACs**:
  - [ ] AC-T1.1.1: `verify_supabase_jwt(token: str)` function decodes and validates JWT
  - [ ] AC-T1.1.2: JWT validated against SUPABASE_JWT_SECRET from settings
  - [ ] AC-T1.1.3: Returns decoded payload with `sub` (user_id) claim
  - [ ] AC-T1.1.4: Raises `HTTPException(401)` for invalid/expired tokens

### T1.2: Create get_current_user Dependency
- **Status**: [ ] Pending
- **File**: `nikita/api/middleware/auth.py`
- **Dependencies**: T1.1
- **ACs**:
  - [ ] AC-T1.2.1: FastAPI `Depends()` compatible async function
  - [ ] AC-T1.2.2: Extracts Bearer token from Authorization header
  - [ ] AC-T1.2.3: Returns `User` model from repository
  - [ ] AC-T1.2.4: Returns 401 if user not found in database

### T1.3: Create Portal Router with Protected Routes
- **Status**: [ ] Pending
- **File**: `nikita/api/routes/portal.py`
- **Dependencies**: T1.2
- **ACs**:
  - [ ] AC-T1.3.1: Router mounted at `/api/v1/portal`
  - [ ] AC-T1.3.2: `GET /stats/{user_id}` returns StatsResponse
  - [ ] AC-T1.3.3: `GET /conversations/{user_id}` returns ConversationListResponse
  - [ ] AC-T1.3.4: All routes use `Depends(get_current_user)`
  - [ ] AC-T1.3.5: Returns 403 if user_id != current_user.id

### T1.4: Update main.py with API v1 Prefix
- **Status**: [ ] Pending
- **File**: `nikita/api/main.py`
- **Dependencies**: T1.3, T2.2, T2.3, T2.4
- **ACs**:
  - [ ] AC-T1.4.1: Portal router included with `/api/v1/portal` prefix
  - [ ] AC-T1.4.2: OpenAPI docs available at `/docs`
  - [ ] AC-T1.4.3: API version visible in OpenAPI schema

---

## US-002: Webhook Security (P1)

### T2.1: Create Webhook Auth Dependencies
- **Status**: [ ] Pending
- **File**: `nikita/api/middleware/auth.py`
- **Dependencies**: None
- **ACs**:
  - [ ] AC-T2.1.1: `verify_telegram_secret` checks X-Telegram-Bot-Api-Secret-Token header
  - [ ] AC-T2.1.2: `verify_elevenlabs_secret` checks custom header
  - [ ] AC-T2.1.3: Both raise HTTPException(403) for mismatched secrets
  - [ ] AC-T2.1.4: Secrets read from settings (rotatable via env vars)

### T2.2: Create Telegram Router Stub
- **Status**: [ ] Pending
- **File**: `nikita/api/routes/telegram.py`
- **Dependencies**: T2.1
- **ACs**:
  - [ ] AC-T2.2.1: Router mounted at `/api/v1/telegram`
  - [ ] AC-T2.2.2: `POST /webhook` endpoint defined (body processed in 002 spec)
  - [ ] AC-T2.2.3: Uses `Depends(verify_telegram_secret)`
  - [ ] AC-T2.2.4: Returns 200 OK for valid requests (placeholder)

### T2.3: Create Voice Router Stub
- **Status**: [ ] Pending
- **File**: `nikita/api/routes/voice.py`
- **Dependencies**: T2.1
- **ACs**:
  - [ ] AC-T2.3.1: Router mounted at `/api/v1/voice`
  - [ ] AC-T2.3.2: `POST /server-tool` endpoint defined (body processed in 007 spec)
  - [ ] AC-T2.3.3: Uses `Depends(verify_elevenlabs_secret)`
  - [ ] AC-T2.3.4: Returns 200 OK for valid requests (placeholder)

### T2.4: Create Admin Router with Service Auth
- **Status**: [ ] Pending
- **File**: `nikita/api/routes/admin.py`
- **Dependencies**: T2.1
- **ACs**:
  - [ ] AC-T2.4.1: Router mounted at `/api/v1/admin`
  - [ ] AC-T2.4.2: `verify_service_key` dependency for internal API key
  - [ ] AC-T2.4.3: `POST /trigger-decay` endpoint (placeholder)
  - [ ] AC-T2.4.4: Returns 403 for invalid service key

---

## US-003: Rate Limit Transparency (P2)

### T3.1: Create Rate Limiting Middleware
- **Status**: [ ] Pending
- **File**: `nikita/api/middleware/rate_limit.py`
- **Dependencies**: None
- **ACs**:
  - [ ] AC-T3.1.1: In-memory sliding window rate limiter (no Redis dependency)
  - [ ] AC-T3.1.2: Configurable limits per endpoint type via settings
  - [ ] AC-T3.1.3: Uses user_id (authenticated) or IP (anonymous) as key
  - [ ] AC-T3.1.4: Returns 429 with Retry-After header when exceeded

### T3.2: Add Rate Limit Response Headers
- **Status**: [ ] Pending
- **File**: `nikita/api/middleware/rate_limit.py`
- **Dependencies**: T3.1
- **ACs**:
  - [ ] AC-T3.2.1: `X-RateLimit-Limit` header shows max requests
  - [ ] AC-T3.2.2: `X-RateLimit-Remaining` header shows remaining
  - [ ] AC-T3.2.3: `X-RateLimit-Reset` header shows window reset time
  - [ ] AC-T3.2.4: Headers added to all responses (not just 429)

---

## Cross-Cutting Tasks (P1)

### T4.1: Create Pydantic Schema Updates
- **Status**: [ ] Pending
- **Files**: `nikita/api/schemas/conversation.py`, `nikita/api/schemas/telegram.py`, `nikita/api/schemas/voice.py`
- **Dependencies**: None (parallel)
- **ACs**:
  - [ ] AC-T4.1.1: ConversationListResponse with pagination fields
  - [ ] AC-T4.1.2: TelegramUpdate schema with Optional fields
  - [ ] AC-T4.1.3: ElevenLabsToolRequest schema
  - [ ] AC-T4.1.4: All nullable fields explicitly typed with `| None`

### T4.2: Implement Error Handling
- **Status**: [ ] Pending
- **File**: `nikita/api/main.py`
- **Dependencies**: T1.4
- **ACs**:
  - [ ] AC-T4.2.1: RFC 7807 ProblemDetail response model
  - [ ] AC-T4.2.2: GameOverError exception handler returns 200 with game status
  - [ ] AC-T4.2.3: ValidationError handler returns 422 with field details
  - [ ] AC-T4.2.4: Generic exception handler returns 500 with correlation_id

### T4.3: Refine CORS Configuration
- **Status**: [ ] Pending
- **File**: `nikita/api/main.py`
- **Dependencies**: T4.2
- **ACs**:
  - [ ] AC-T4.3.1: Only portal domains in CORS_ORIGINS (no wildcards)
  - [ ] AC-T4.3.2: `allow_credentials=True` for JWT auth
  - [ ] AC-T4.3.3: `max_age=3600` for preflight caching
  - [ ] AC-T4.3.4: Restrict methods to GET, POST, OPTIONS

---

## Progress Summary

| User Story | Tasks | Completed | Status |
|------------|-------|-----------|--------|
| US-001: Portal Auth | 4 | 0 | Pending |
| US-002: Webhook Security | 4 | 0 | Pending |
| US-003: Rate Limits | 2 | 0 | Pending |
| Cross-Cutting | 2 | 0 | Pending |
| **Total** | **12** | **0** | **Not Started** |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-29 | Initial task generation from plan.md |
