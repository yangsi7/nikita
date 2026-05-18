# api/ - FastAPI Application

## Purpose

REST API gateway for Nikita game, handling Telegram webhooks, voice callbacks, and portal stats.

## Architecture

```
api/
├── main.py              # FastAPI app, CORS, exception handlers
├── dependencies/
│   └── auth.py          # _decode_jwt, get_current_user_id, get_authenticated_user, get_current_admin_user
├── routes/
│   ├── telegram.py           # POST /telegram/webhook
│   ├── voice.py              # POST /voice/elevenlabs/*
│   ├── portal.py             # GET/PUT /portal/* (JWT auth, no user_id in URL)
│   ├── portal_onboarding_v2.py  # POST /portal/onboarding/* (v2 wizard, Spec 218)
│   ├── portal_auth.py        # POST /auth/* (autobind, dashboard-bridge, auth flows)
│   ├── auth_bridge.py        # Auth bridge utilities
│   ├── admin_debug.py        # Admin debug endpoints
│   ├── tasks.py              # POST /tasks/* (pg_cron endpoints: decay, summaries, cleanup)
│   └── admin.py              # Admin endpoints (requires admin role)
├── schemas/
│   ├── user.py          # UserResponse, StatsResponse
│   ├── conversation.py  # ConversationResponse
│   └── game.py          # ScorePoint, BossEncounter
└── middleware/
    ├── auth.py          # Supabase JWT verification
    └── rate_limit.py    # Rate limiting
```

## Key Endpoints

### Telegram
```python
POST /telegram/webhook
└─ Body: TelegramUpdate → Process → Reply via bot
```

### Voice
```python
POST /voice/elevenlabs/server-tool
├─ Tools: get_context, get_memory, score_turn, update_memory
└─ Returns: Tool-specific JSON
```

### Portal (JWT auth — no user_id in URL)
```python
GET  /portal/stats          # Score, chapter, history
GET  /portal/settings       # User settings (email, timezone, telegram)
PUT  /portal/settings       # Update settings (session.refresh after commit)
GET  /portal/conversations  # List past conversations
GET  /portal/engagement     # Engagement state, multiplier, transitions
GET  /portal/vices          # Vice preferences and scores
```

### Portal Onboarding (v2 wizard, JWT auth)
```python
POST /api/v1/portal/onboarding/answer     # Submit wizard slot answer
POST /api/v1/portal/onboarding/complete   # Finalize wizard, bootstrap ready_prompts
GET  /api/v1/portal/onboarding/state      # Current wizard state + progress_pct
```

### Auth (`/api/v1/auth/*`)
```python
POST /api/v1/auth/request-otp             # Send magic-link / OTP email
POST /api/v1/auth/autobind-telegram       # Bind telegram_id on magic-link confirm
POST /api/v1/auth/dashboard-bridge        # Mint ?start=<code> deep-link for unbound users
```

### Admin (requires JWT `app_metadata.role == "admin"`; service-role-only claim)
```python
GET  /admin/users           # User list with game state
GET  /admin/conversations   # Conversation inspector
GET  /admin/pipeline-health # Pipeline stage stats, circuit breakers
```

## Auth Dependencies (`dependencies/auth.py`)

All auth deps share `_decode_jwt(credentials)` — single JWT decode+error-handling path.

| Dependency | Returns | Use Case |
|---|---|---|
| `_decode_jwt(creds)` | `dict` (raw payload) | Internal helper — not a FastAPI dep |
| `get_current_user_id` | `UUID` | Most endpoints (no email needed) |
| `get_authenticated_user` | `AuthenticatedUser(id, email)` | Settings endpoints (email from JWT) |
| `get_current_admin_user` | `UUID` | Admin endpoints (validates JWT admin claim) |

Helper: `_is_admin_claim(claims)` — returns `claims["app_metadata"]["role"] == "admin"`. Admin is gated on the JWT `app_metadata.role` claim (service-role-only, not client-writable). `user_metadata` is DELIBERATELY NEVER consulted — it is writable from the browser and would enable self-escalation.

## Patterns

### Dependency Injection
```python
from nikita.db.repositories.user_repository import UserRepository

async def get_user_repo(session = Depends(get_async_session)):
    return UserRepository(session)

@router.get("/stats/{user_id}")
async def get_stats(
    user_id: UUID,
    repo: UserRepository = Depends(get_user_repo),
):
    user = await repo.get(user_id)
    return {"score": user.relationship_score}
```

### Error Handling
```python
class GameOverError(Exception):
    pass

@app.exception_handler(GameOverError)
async def game_over_handler(request, exc):
    return JSONResponse(
        status_code=200,
        content={"status": "game_over", "message": "Nikita dumped you."},
    )
```

## Callers

- `nikita/api/main.py` — FastAPI app entry; assembles all routers under `/api/v1/*`.
- Cloud Run service `nikita-api` (project `gcp-transcribe-test`, region `us-central1`) — receives all inbound HTTP traffic.
- pg_cron jobs in `supabase/migrations/20260418141500_cron_heartbeat_engine.sql:56,68,80` — POST to `/api/v1/tasks/{heartbeat,generate-daily-arcs,touchpoints}` on schedule.
- ElevenLabs platform — POST `/api/v1/voice/server-tool` callbacks during voice conversations.
- Telegram webhook — POST `/api/v1/telegram/webhook` on every bot message.

## Gotchas

- **Hardcoded TASK_AUTH_SECRET in cron migration SQL**: `S7fBvwplxGNuzX39hG2osZwdeixLzuBx3dWOik6N3b0` literally in `cron_heartbeat_engine.sql:63,75,87`. Rotation requires `cron.alter_job` for each of the HTTP cron jobs (W4 audit + CLAUDE.md gotcha).
- **Dev-mode auth bypass**: `tasks.py:65-70 verify_task_secret` allows unauthenticated POSTs when `TASK_AUTH_SECRET` is unset (warning only, does NOT reject). Production must always set the secret.
- **`--allow-unauthenticated` on Cloud Run is intentional** — app-layer JWT auth handles authorization. Do NOT switch to IAM-restricted Cloud Run; the auth model assumes public ingress.
- **Pipeline invocation sites = 5**: `admin.py:628`, `tasks.py:788`, `tasks.py:962`, `voice.py:801`, `onboarding/handoff.py:705`. Telegram `message_handler.py` does NOT invoke directly.
- **CORS allowlist must match canonical domain post-redirect**: per `.claude/rules/vercel-cors-canonical.md`. Apex `nikita-mygirl.com` is canonical (no redirect); www → 308 → apex.
- **Background-task scheduling at `telegram.py:796`**: handler dispatch runs inside FastAPI background tasks, not directly. Avoid blocking on long ops; queue them.

## Navigation

- Backend module map: [`../CLAUDE.md`](../CLAUDE.md)
- Backend canonical: [`../../memory/backend.md`](../../memory/backend.md)
- Integration recipes (Supabase, ElevenLabs, Telegram): [`../../memory/integrations.md`](../../memory/integrations.md)
- Deployment: [`../../docs/deployment.md`](../../docs/deployment.md)

Last verified: 2026-05-18
