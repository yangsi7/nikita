# Implementation Plan: 010-API-Infrastructure

## Overview

Implementation plan for FastAPI infrastructure layer including authentication, rate limiting, route organization, and error handling.

**Spec Reference**: `spec.md`
**Priority**: P0 (blocks 002-telegram, 007-voice, 008-portal)
**Estimated Tasks**: 12 tasks across 3 user stories

---

## Dependency Analysis

```
┌─────────────────────────────────────────────────────────────┐
│                    010-API-Infrastructure                    │
├─────────────────────────────────────────────────────────────┤
│  UPSTREAM (depends on)                                      │
│  ├── 009-database-infrastructure (repositories) ✅ Done     │
│  ├── Supabase Auth configured ✅ Done                       │
│  └── In-memory rate limiting (no Redis needed)              │
├─────────────────────────────────────────────────────────────┤
│  DOWNSTREAM (blocks)                                        │
│  ├── 002-telegram-integration                               │
│  ├── 007-voice-agent                                        │
│  └── 008-player-portal                                      │
└─────────────────────────────────────────────────────────────┘
```

---

## Existing Code Analysis

| File | Status | Reuse |
|------|--------|-------|
| `nikita/api/main.py` | Skeleton | Extend (CORS, health present) |
| `nikita/api/schemas/user.py` | Partial | Reuse (UserStatsResponse exists) |
| `nikita/api/routes/` | Empty stubs | Create routers |
| `nikita/api/middleware/` | Empty stubs | Create auth, rate limit |

---

## User Story Tasks

### US-001: Portal Authentication (P1)

**As a** portal user **I want** my requests authenticated via Supabase **So that** only I can access my game data

#### T1.1: Create Supabase JWT Verification Module

**Implements**: FR-002 (AC-002.1, AC-002.2, AC-002.3)
**File**: `nikita/api/middleware/auth.py`

**Acceptance Criteria**:
- [ ] AC-T1.1.1: `verify_supabase_jwt(token: str)` function decodes and validates JWT
- [ ] AC-T1.1.2: JWT validated against SUPABASE_JWT_SECRET from settings
- [ ] AC-T1.1.3: Returns decoded payload with `sub` (user_id) claim
- [ ] AC-T1.1.4: Raises `HTTPException(401)` for invalid/expired tokens

**Implementation**:
```python
from jose import jwt, JWTError
from nikita.config.settings import get_settings

def verify_supabase_jwt(token: str) -> dict:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated"
        )
        return payload
    except JWTError as e:
        raise HTTPException(401, f"Invalid token: {e}")
```

#### T1.2: Create get_current_user Dependency

**Implements**: FR-002 (AC-002.3, AC-002.4)
**File**: `nikita/api/middleware/auth.py`

**Acceptance Criteria**:
- [ ] AC-T1.2.1: FastAPI `Depends()` compatible async function
- [ ] AC-T1.2.2: Extracts Bearer token from Authorization header
- [ ] AC-T1.2.3: Returns `User` model from repository
- [ ] AC-T1.2.4: Returns 401 if user not found in database

**Implementation**:
```python
async def get_current_user(
    authorization: str = Header(...),
    user_repo: UserRepository = Depends(get_user_repo),
) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Invalid auth header format")
    token = authorization.replace("Bearer ", "")
    payload = verify_supabase_jwt(token)
    user = await user_repo.get(UUID(payload["sub"]))
    if not user:
        raise HTTPException(401, "User not found")
    return user
```

#### T1.3: Create Portal Router with Protected Routes

**Implements**: FR-001 (AC-001.1, AC-001.2), US-001 (AC-US001.2, AC-US001.3)
**File**: `nikita/api/routes/portal.py`

**Acceptance Criteria**:
- [ ] AC-T1.3.1: Router mounted at `/api/v1/portal`
- [ ] AC-T1.3.2: `GET /stats/{user_id}` returns StatsResponse
- [ ] AC-T1.3.3: `GET /conversations/{user_id}` returns ConversationListResponse
- [ ] AC-T1.3.4: All routes use `Depends(get_current_user)`
- [ ] AC-T1.3.5: Returns 403 if user_id != current_user.id

#### T1.4: Update main.py with API v1 Prefix

**Implements**: FR-001 (AC-001.1, AC-001.3)
**File**: `nikita/api/main.py`

**Acceptance Criteria**:
- [ ] AC-T1.4.1: Portal router included with `/api/v1/portal` prefix
- [ ] AC-T1.4.2: OpenAPI docs available at `/docs`
- [ ] AC-T1.4.3: API version visible in OpenAPI schema

---

### US-002: Webhook Security (P1)

**As a** system operator **I want** webhooks verified against secrets **So that** only legitimate services can trigger them

#### T2.1: Create Webhook Auth Dependencies

**Implements**: FR-002 (AC-002.5)
**File**: `nikita/api/middleware/auth.py`

**Acceptance Criteria**:
- [ ] AC-T2.1.1: `verify_telegram_secret` checks X-Telegram-Bot-Api-Secret-Token header
- [ ] AC-T2.1.2: `verify_elevenlabs_secret` checks custom header
- [ ] AC-T2.1.3: Both raise HTTPException(403) for mismatched secrets
- [ ] AC-T2.1.4: Secrets read from settings (rotatable via env vars)

#### T2.2: Create Telegram Router Stub

**Implements**: FR-001 (AC-001.2), US-002 (AC-US002.1)
**File**: `nikita/api/routes/telegram.py`

**Acceptance Criteria**:
- [ ] AC-T2.2.1: Router mounted at `/api/v1/telegram`
- [ ] AC-T2.2.2: `POST /webhook` endpoint defined (body processed in 002 spec)
- [ ] AC-T2.2.3: Uses `Depends(verify_telegram_secret)`
- [ ] AC-T2.2.4: Returns 200 OK for valid requests (placeholder)

#### T2.3: Create Voice Router Stub

**Implements**: FR-001 (AC-001.2), US-002 (AC-US002.2)
**File**: `nikita/api/routes/voice.py`

**Acceptance Criteria**:
- [ ] AC-T2.3.1: Router mounted at `/api/v1/voice`
- [ ] AC-T2.3.2: `POST /server-tool` endpoint defined (body processed in 007 spec)
- [ ] AC-T2.3.3: Uses `Depends(verify_elevenlabs_secret)`
- [ ] AC-T2.3.4: Returns 200 OK for valid requests (placeholder)

#### T2.4: Create Admin Router with Service Auth

**Implements**: FR-001 (AC-001.2), FR-002 (AC-002.5)
**File**: `nikita/api/routes/admin.py`

**Acceptance Criteria**:
- [ ] AC-T2.4.1: Router mounted at `/api/v1/admin`
- [ ] AC-T2.4.2: `verify_service_key` dependency for internal API key
- [ ] AC-T2.4.3: `POST /trigger-decay` endpoint (placeholder)
- [ ] AC-T2.4.4: Returns 403 for invalid service key

---

### US-003: Rate Limit Transparency (P2)

**As an** API consumer **I want** clear rate limit headers **So that** I can implement proper backoff

#### T3.1: Create Rate Limiting Middleware

**Implements**: FR-003 (AC-003.1, AC-003.2, AC-003.3)
**File**: `nikita/api/middleware/rate_limit.py`

**Acceptance Criteria**:
- [ ] AC-T3.1.1: In-memory sliding window rate limiter (no Redis dependency)
- [ ] AC-T3.1.2: Configurable limits per endpoint type via settings
- [ ] AC-T3.1.3: Uses user_id (authenticated) or IP (anonymous) as key
- [ ] AC-T3.1.4: Returns 429 with Retry-After header when exceeded

**Rate Limits (from spec)**:
| Endpoint Type | Limit | Window |
|---------------|-------|--------|
| Telegram webhook | 10 req/min | per user |
| Voice callback | 5 req/min | per user |
| Portal API | 100 req/min | per user |
| Admin | 30 req/min | per IP |

#### T3.2: Add Rate Limit Response Headers

**Implements**: US-003 (AC-US003.1, AC-US003.2, AC-US003.3)
**File**: `nikita/api/middleware/rate_limit.py`

**Acceptance Criteria**:
- [ ] AC-T3.2.1: `X-RateLimit-Limit` header shows max requests
- [ ] AC-T3.2.2: `X-RateLimit-Remaining` header shows remaining
- [ ] AC-T3.2.3: `X-RateLimit-Reset` header shows window reset time
- [ ] AC-T3.2.4: Headers added to all responses (not just 429)

---

### Cross-Cutting Tasks (P1)

#### T4.1: Create Pydantic Schema Updates

**Implements**: FR-004 (AC-004.1 to AC-004.4)
**Files**: `nikita/api/schemas/conversation.py`, `nikita/api/schemas/telegram.py`, `nikita/api/schemas/voice.py`

**Acceptance Criteria**:
- [ ] AC-T4.1.1: ConversationListResponse with pagination fields
- [ ] AC-T4.1.2: TelegramUpdate schema with Optional fields
- [ ] AC-T4.1.3: ElevenLabsToolRequest schema
- [ ] AC-T4.1.4: All nullable fields explicitly typed with `| None`

#### T4.2: Implement Error Handling

**Implements**: FR-005 (AC-005.1 to AC-005.4)
**File**: `nikita/api/main.py`

**Acceptance Criteria**:
- [ ] AC-T4.2.1: RFC 7807 ProblemDetail response model
- [ ] AC-T4.2.2: GameOverError exception handler returns 200 with game status
- [ ] AC-T4.2.3: ValidationError handler returns 422 with field details
- [ ] AC-T4.2.4: Generic exception handler returns 500 with correlation_id

#### T4.3: Refine CORS Configuration

**Implements**: FR-006 (AC-006.1 to AC-006.4)
**File**: `nikita/api/main.py`

**Acceptance Criteria**:
- [ ] AC-T4.3.1: Only portal domains in CORS_ORIGINS (no wildcards)
- [ ] AC-T4.3.2: `allow_credentials=True` for JWT auth
- [ ] AC-T4.3.3: `max_age=3600` for preflight caching
- [ ] AC-T4.3.4: Restrict methods to GET, POST, OPTIONS

---

## Task Dependency Graph

```
T1.1 (JWT verify)
    ↓
T1.2 (get_current_user) ─────┐
    ↓                        │
T1.3 (portal router) ────────┤
                             │
T2.1 (webhook auth) ─────────┤
    ↓                        │
T2.2 (telegram router) ──────┤
    ↓                        │
T2.3 (voice router) ─────────┼──→ T1.4 (main.py update)
    ↓                        │          ↓
T2.4 (admin router) ─────────┘     T4.2 (error handling)
                                        ↓
T3.1 (rate limiter) ────────────→ T4.3 (CORS refinement)
    ↓
T3.2 (rate limit headers)

T4.1 (schemas) ─ parallel, no dependencies
```

---

## Implementation Sequence

| Phase | Tasks | Est. Effort |
|-------|-------|-------------|
| 1. Auth Layer | T1.1, T1.2, T2.1 | 2-3 hours |
| 2. Routers | T1.3, T2.2, T2.3, T2.4, T1.4 | 2-3 hours |
| 3. Schemas | T4.1 | 1 hour |
| 4. Rate Limiting | T3.1, T3.2 | 2 hours |
| 5. Error Handling | T4.2, T4.3 | 1-2 hours |

**Total Estimated**: 8-11 hours

---

## Files Created/Modified

| File | Action | Purpose |
|------|--------|---------|
| `nikita/api/middleware/auth.py` | Create | JWT verify, dependencies |
| `nikita/api/middleware/rate_limit.py` | Create | Rate limiting middleware |
| `nikita/api/routes/portal.py` | Create | Portal stats endpoints |
| `nikita/api/routes/telegram.py` | Create | Telegram webhook stub |
| `nikita/api/routes/voice.py` | Create | Voice callback stub |
| `nikita/api/routes/admin.py` | Create | Admin endpoints |
| `nikita/api/schemas/telegram.py` | Create | TelegramUpdate schema |
| `nikita/api/schemas/voice.py` | Create | ElevenLabsToolRequest |
| `nikita/api/schemas/conversation.py` | Modify | Add pagination |
| `nikita/api/main.py` | Modify | Register routers, error handlers |

---

## Test Strategy

1. **Unit Tests**: JWT verification, rate limit algorithm
2. **Integration Tests**: Auth flow with mock Supabase JWT
3. **API Tests**: Endpoint responses, error formats
4. **Manual Tests**: Rate limit headers, CORS preflight

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| JWT secret not configured | Fail fast with clear error on startup |
| Rate limit memory bloat | LRU cache with max 10k entries |
| Schema validation gaps | Strict mode Pydantic, explicit types |
