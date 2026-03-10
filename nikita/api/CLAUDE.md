# api/ - FastAPI Application

## Purpose

REST API gateway for Nikita game, handling Telegram webhooks, voice callbacks, and portal stats.

## Current State

**Status**: ✅ Complete — Full API deployed to Cloud Run
- `main.py`: FastAPI app with lifespan, DI, CORS, exception handlers
- `routes/telegram.py`: Webhook endpoint with signature validation
- `routes/tasks.py`: pg_cron task endpoints (decay, summaries, cleanup)
- `schemas/`: Pydantic request/response models

## Architecture

```
api/
├── main.py              # FastAPI app, CORS, exception handlers
├── dependencies/
│   └── auth.py          # _decode_jwt, get_current_user_id, get_authenticated_user, get_current_admin_user
├── routes/
│   ├── telegram.py      # POST /telegram/webhook
│   ├── voice.py         # POST /voice/elevenlabs/*
│   ├── portal.py        # GET/PUT /portal/* (JWT auth, no user_id in URL)
│   ├── tasks.py         # POST /tasks/* (pg_cron endpoints: decay, summaries, cleanup)
│   └── admin.py         # Admin endpoints (requires admin role)
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

### Admin (requires `raw_user_meta_data.role = "admin"` + `settings.admin_emails`)
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
| `get_current_admin_user` | `UUID` | Admin endpoints (validates admin email) |

Helper: `_is_admin_email(email)` — checks `@silent-agents.com` domain OR `settings.admin_emails` allowlist.

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

## Documentation

- [Backend Architecture](../../memory/backend.md)
- [API Schemas](../../memory/backend.md#pydantic-schema-pattern)
