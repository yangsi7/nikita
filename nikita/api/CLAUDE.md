# api/ - FastAPI Application

## Purpose

REST API gateway for Nikita game, handling Telegram webhooks, voice callbacks, and portal stats.

## Current State

**Phase 2 ✅ 95%**: Full API deployed to Cloud Run
- `main.py`: FastAPI app with lifespan, DI, CORS, exception handlers
- `routes/telegram.py`: Webhook endpoint with signature validation (needs completion)
- `routes/tasks.py`: pg_cron task endpoints (decay, summaries, cleanup)
- `schemas/`: Pydantic request/response models
- All 97 API tests passing

## Target Architecture (Phase 2-5)

```
api/
├── main.py              # FastAPI app, CORS, exception handlers
├── routes/
│   ├── telegram.py      # POST /telegram/webhook (Phase 2)
│   ├── voice.py         # POST /voice/elevenlabs/* (Phase 4)
│   ├── portal.py        # GET /portal/stats/* (Phase 5)
│   └── admin.py         # Admin endpoints (Phase 5)
├── schemas/
│   ├── user.py          # UserResponse, StatsResponse
│   ├── conversation.py  # ConversationResponse
│   └── game.py          # ScorePoint, BossEncounter
└── middleware/
    ├── auth.py          # Supabase JWT verification (Phase 2)
    └── rate_limit.py    # Rate limiting (Phase 2)
```

## Key Endpoints (TODO)

### Telegram (Phase 2)
```python
POST /telegram/webhook
└─ Body: TelegramUpdate → Process → Reply via bot
```

### Voice (Phase 4)
```python
POST /voice/elevenlabs/server-tool
├─ Tools: get_context, get_memory, score_turn, update_memory
└─ Returns: Tool-specific JSON
```

### Portal (Phase 5)
```python
GET /portal/stats/{user_id}
└─ Auth: Supabase JWT → Returns: score, chapter, history

GET /portal/conversations/{user_id}
└─ Returns: List of past conversations

GET /portal/daily-summary/{user_id}/{date}
└─ Returns: Nikita's daily recap
```

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
