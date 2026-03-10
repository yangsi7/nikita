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
├── routes/
│   ├── telegram.py      # POST /telegram/webhook
│   ├── voice.py         # POST /voice/elevenlabs/*
│   ├── portal.py        # GET /portal/stats/*
│   └── admin.py         # Admin endpoints
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

### Portal
```python
GET /portal/stats/{user_id}
└─ Auth: Supabase JWT → Returns: score, chapter, history

GET /portal/conversations/{user_id}
└─ Returns: List of past conversations

GET /portal/daily-summary/{user_id}/{date}
└─ Returns: Nikita's daily recap
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
