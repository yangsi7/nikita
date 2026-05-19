# 010: API Infrastructure

## Overview

Cross-cutting infrastructure specification defining the FastAPI application layer, authentication middleware, rate limiting, and route organization for all Nikita platform integrations.

**Type**: Infrastructure
**Blocks**: 002-telegram-integration, 007-voice-agent, 008-player-portal
**References**: `memory/backend.md#api-endpoints`

---

## Functional Requirements

### FR-001: FastAPI Application Structure

The system SHALL organize API routes by domain with consistent patterns.

**Acceptance Criteria**:
- AC-001.1: Routes organized under `/api/v1/{domain}/`
- AC-001.2: Each domain has dedicated router module
- AC-001.3: OpenAPI documentation auto-generated at `/docs`
- AC-001.4: Health check endpoint at `/health`

**Route Organization**:
```
/api/v1/
├── telegram/           # Webhook handlers (002)
│   ├── POST /webhook   # Incoming updates
│   └── POST /set-webhook
├── voice/              # ElevenLabs callbacks (007)
│   ├── POST /server-tool
│   └── POST /callback
├── portal/             # Player stats (008)
│   ├── GET /stats/{user_id}
│   ├── GET /conversations/{user_id}
│   └── GET /daily-summary/{user_id}/{date}
└── admin/              # Internal operations
    ├── GET /users
    └── POST /trigger-decay
```

### FR-002: Authentication Middleware

The system SHALL authenticate requests using Supabase JWT tokens.

**Acceptance Criteria**:
- AC-002.1: Portal endpoints require valid Supabase JWT
- AC-002.2: JWT verified against Supabase public key
- AC-002.3: User ID extracted and attached to request state
- AC-002.4: 401 returned for missing/invalid tokens
- AC-002.5: Telegram/Voice webhooks use secret-based auth

**Auth Patterns**:
| Endpoint | Auth Method | Validation |
|----------|-------------|------------|
| `/portal/*` | Supabase JWT | Bearer token in header |
| `/telegram/webhook` | Telegram Secret | X-Telegram-Bot-Api-Secret-Token |
| `/voice/*` | ElevenLabs Secret | Custom header verification |
| `/admin/*` | Service Role | Internal API key |

### FR-003: Rate Limiting

The system SHALL enforce rate limits to prevent abuse.

**Acceptance Criteria**:
- AC-003.1: Rate limits per user ID or IP
- AC-003.2: Configurable limits per endpoint type
- AC-003.3: 429 response with Retry-After header
- AC-003.4: Redis-backed for distributed deployment

**Rate Limits**:
| Endpoint Type | Limit | Window |
|---------------|-------|--------|
| Telegram webhook | 10 req/min | per user |
| Voice callback | 5 req/min | per user |
| Portal API | 100 req/min | per user |
| Admin | 30 req/min | per IP |

### FR-004: Request/Response Schemas

The system SHALL use Pydantic models for all API contracts.

**Acceptance Criteria**:
- AC-004.1: Request bodies validated via Pydantic
- AC-004.2: Response models define structure
- AC-004.3: Validation errors return 422 with details
- AC-004.4: Nullable fields explicitly typed

**Core Schemas**:
```python
# Portal Responses
class StatsResponse(BaseModel):
    current_score: Decimal
    chapter: int
    chapter_name: str
    days_played: int
    boss_attempts: int
    game_status: str
    score_history: list[ScorePoint]

class ConversationListResponse(BaseModel):
    conversations: list[ConversationSummary]
    total: int
    limit: int
    offset: int

# Webhook Payloads
class TelegramUpdate(BaseModel):
    update_id: int
    message: Optional[TelegramMessage]
    callback_query: Optional[CallbackQuery]

class ElevenLabsToolRequest(BaseModel):
    tool_name: str
    parameters: dict
    session_id: str
```

### FR-005: Error Handling

The system SHALL return consistent error responses.

**Acceptance Criteria**:
- AC-005.1: All errors follow RFC 7807 Problem Details
- AC-005.2: Game-specific errors (game_over, boss_fail) return 200 with status
- AC-005.3: Unhandled exceptions return 500 with correlation ID
- AC-005.4: Validation errors list all field issues

**Error Response Format**:
```json
{
  "type": "https://nikita.game/errors/game-over",
  "title": "Game Over",
  "status": 200,
  "detail": "Nikita dumped you. Your score reached 0%.",
  "instance": "/api/v1/telegram/webhook",
  "correlation_id": "abc-123"
}
```

### FR-006: CORS Configuration

The system SHALL enable CORS for portal frontend.

**Acceptance Criteria**:
- AC-006.1: Portal domain whitelisted for CORS
- AC-006.2: Credentials allowed for JWT auth
- AC-006.3: Preflight caching: 3600 seconds
- AC-006.4: Only GET/POST methods for portal

---

## Non-Functional Requirements

### NFR-001: Performance

- API response time <200ms (p95) excluding LLM calls
- Webhook processing <500ms (p95)
- Connection keep-alive enabled

### NFR-002: Reliability

- Graceful shutdown (finish in-flight requests)
- Circuit breaker for downstream services
- Retry logic for transient failures

### NFR-003: Security

- HTTPS only in production
- No secrets in logs or responses
- Input sanitization for all user content
- CSRF protection for portal mutations

### NFR-004: Observability

- Request ID in all logs
- Timing metrics per endpoint
- Error rates tracked
- Webhook delivery success rate

---

## Middleware Stack

```python
# Order matters - applied bottom-to-top
app = FastAPI()

# 1. CORS (outermost)
app.add_middleware(CORSMiddleware, ...)

# 2. Request ID injection
app.add_middleware(RequestIdMiddleware)

# 3. Rate limiting
app.add_middleware(RateLimitMiddleware)

# 4. Authentication (per-route)
# Applied via Depends() on routes

# 5. Error handling (exception handlers)
@app.exception_handler(GameOverError)
@app.exception_handler(ValidationError)
```

---

## User Stories

### US-001: Portal Authentication

**As a** portal user
**I want** my requests authenticated via Supabase
**So that** only I can access my game data

**Acceptance Criteria**:
- [ ] AC-US001.1: Login redirects to Supabase Auth
- [ ] AC-US001.2: JWT attached to all portal requests
- [ ] AC-US001.3: Expired tokens return 401
- [ ] AC-US001.4: Refresh flow works automatically

### US-002: Webhook Security

**As a** system operator
**I want** webhooks verified against secrets
**So that** only legitimate services can trigger them

**Acceptance Criteria**:
- [ ] AC-US002.1: Telegram webhook validates secret token
- [ ] AC-US002.2: ElevenLabs callback verified
- [ ] AC-US002.3: Invalid secrets return 403
- [ ] AC-US002.4: Secrets rotatable without downtime

### US-003: Rate Limit Transparency

**As an** API consumer
**I want** clear rate limit headers
**So that** I can implement proper backoff

**Acceptance Criteria**:
- [ ] AC-US003.1: X-RateLimit-Limit header present
- [ ] AC-US003.2: X-RateLimit-Remaining header present
- [ ] AC-US003.3: 429 includes Retry-After
- [ ] AC-US003.4: Rate limits documented in OpenAPI

---

## Dependencies

### Upstream (this spec depends on)
- 009-database-infrastructure (repository injection)
- Supabase Auth configured
- Redis for rate limiting (optional, fallback to in-memory)

### Downstream (depends on this spec)
- 002-telegram-integration (POST /telegram/webhook)
- 007-voice-agent (POST /voice/*)
- 008-player-portal (GET /portal/*)

---

## Implementation Notes

**Pattern Reference**: `memory/backend.md#dependency-injection-pattern`

```python
# Auth middleware example
async def get_current_user(
    authorization: str = Header(...),
    user_repo: UserRepository = Depends(get_user_repo),
) -> User:
    token = authorization.replace("Bearer ", "")
    payload = verify_supabase_jwt(token)
    user = await user_repo.get(UUID(payload["sub"]))
    if not user:
        raise HTTPException(401, "User not found")
    return user

# Protected route
@router.get("/stats/{user_id}")
async def get_stats(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    repo: UserRepository = Depends(get_user_repo),
):
    if current_user.id != user_id:
        raise HTTPException(403, "Access denied")
    return await repo.get_stats(user_id)
```

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| JWT validation overhead | Medium | Cache public keys, use async verify |
| Rate limit bypass | Medium | User ID + IP combination |
| Webhook replay attacks | High | Timestamp validation, nonce tracking |
| CORS misconfiguration | High | Strict origin allowlist, no wildcards |
