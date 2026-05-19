# Implementation Plan: 002-Telegram-Integration

**Generated**: 2025-11-29
**Feature**: 002 - Telegram Platform Integration
**Input**: spec.md, infrastructure specs (009, 010, 011)
**Priority**: P1 (Must-Have)

---

## Overview

Telegram Platform Integration provides the primary communication channel for Nikita, creating the "no game UI" illusion where users interact through familiar Telegram messaging.

### Core Components

```
┌─────────────────────────────────────────────────────────────────┐
│                   Telegram Platform Layer                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │ WebhookHdlr │───▶│ MessageRouter│───▶│   Text Agent     │   │
│  │ (receive)   │    │ (dispatch)   │    │   (response)     │   │
│  └─────────────┘    └──────────────┘    └──────────────────┘   │
│         │                  │                     │             │
│         ▼                  ▼                     ▼             │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │ RateLimiter │    │ SessionMgr   │    │ResponseDelivery  │   │
│  │ (protect)   │    │ (state)      │    │   (send)         │   │
│  └─────────────┘    └──────────────┘    └──────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Message Flow

```
User (Telegram) → Webhook → Auth → Rate Check → Route → Text Agent → Delay → Deliver
       ↓              ↓        ↓         ↓         ↓          ↓         ↓         ↓
    Input          POST    Validate   Limit?   Command?   Nikita    Ch.timing   Send
                                                or Text     AI                   back
```

---

## Infrastructure Dependencies

### From 010-api-infrastructure

```python
# Webhook endpoint (already defined in infrastructure spec)
POST /api/v1/telegram/webhook
POST /api/v1/telegram/set-webhook
```

### From 011-background-tasks

```sql
-- pending_responses table for delayed delivery
-- deliver-responses Edge Function triggered by pg_cron
```

### From 009-database-infrastructure

```python
# Repositories
UserRepository.get_by_telegram_id(telegram_id)
ConversationRepository.create(message)
```

---

## Implementation Tasks

### Task 1: Create Telegram Bot Module Structure
**File**: `nikita/platforms/telegram/__init__.py`

```python
"""Telegram platform integration for Nikita."""

from nikita.platforms.telegram.bot import TelegramBot
from nikita.platforms.telegram.handlers import MessageHandler, CommandHandler
from nikita.platforms.telegram.delivery import ResponseDelivery

__all__ = [
    "TelegramBot",
    "MessageHandler",
    "CommandHandler",
    "ResponseDelivery",
]
```

### Task 2: Implement Telegram Bot Client
**File**: `nikita/platforms/telegram/bot.py`

```python
from httpx import AsyncClient
from nikita.config.settings import get_settings

class TelegramBot:
    """Telegram Bot API client wrapper."""

    def __init__(self):
        self.settings = get_settings()
        self.base_url = f"https://api.telegram.org/bot{self.settings.telegram_bot_token}"
        self.client = AsyncClient()

    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: str = "HTML",
    ) -> dict:
        """Send text message to user."""
        pass

    async def send_chat_action(
        self,
        chat_id: int,
        action: str = "typing",
    ) -> dict:
        """Send typing indicator."""
        pass

    async def set_webhook(self, url: str) -> dict:
        """Configure webhook URL."""
        pass
```

### Task 3: Implement Webhook Handler
**File**: `nikita/platforms/telegram/handlers.py`

```python
from fastapi import Request
from pydantic import BaseModel

class TelegramUpdate(BaseModel):
    """Telegram update object."""
    update_id: int
    message: dict | None = None
    callback_query: dict | None = None

class WebhookHandler:
    """Handle incoming Telegram webhook events."""

    async def handle_update(self, update: TelegramUpdate) -> None:
        """Route incoming update to appropriate handler."""
        if update.message:
            await self._handle_message(update.message)
        elif update.callback_query:
            await self._handle_callback(update.callback_query)

    async def _handle_message(self, message: dict) -> None:
        """Handle incoming message (text or media)."""
        text = message.get("text", "")

        if text.startswith("/"):
            await self.command_handler.handle(message)
        elif message.get("photo"):
            await self._handle_media(message, "photo")
        elif message.get("voice"):
            await self._handle_media(message, "voice")
        else:
            await self.message_handler.handle(message)
```

### Task 4: Implement Command Handlers
**File**: `nikita/platforms/telegram/commands.py`

```python
class CommandHandler:
    """Handle /command messages."""

    COMMANDS = {
        "start": "_handle_start",
        "help": "_handle_help",
        "status": "_handle_status",
        "call": "_handle_call",
    }

    async def handle(self, message: dict) -> None:
        """Route command to handler."""
        text = message.get("text", "")
        command = text.split()[0].lstrip("/").split("@")[0]

        handler = getattr(self, self.COMMANDS.get(command, "_handle_unknown"))
        await handler(message)

    async def _handle_start(self, message: dict) -> None:
        """
        Handle /start command - new user onboarding.

        Flow:
        1. Check if telegram_id already linked to user
        2. If yes: welcome back
        3. If no: request email, send magic link
        """
        pass

    async def _handle_help(self, message: dict) -> str:
        """Return help text with available commands."""
        return """
        /start - Begin your journey with Nikita
        /help - Show this message
        /status - See where you stand with Nikita
        /call - Request a voice call (when available)
        """

    async def _handle_status(self, message: dict) -> str:
        """Return current game status (chapter, score hint)."""
        pass
```

### Task 5: Implement Message Handler
**File**: `nikita/platforms/telegram/message_handler.py`

```python
class MessageHandler:
    """Handle text messages to Nikita."""

    def __init__(
        self,
        text_agent: TextAgent,
        user_repository: UserRepository,
        rate_limiter: RateLimiter,
        session_manager: SessionManager,
        response_delivery: ResponseDelivery,
    ):
        self.text_agent = text_agent
        self.user_repository = user_repository
        self.rate_limiter = rate_limiter
        self.session_manager = session_manager
        self.response_delivery = response_delivery

    async def handle(self, message: dict) -> None:
        """
        Process incoming text message.

        Flow:
        1. Extract user info from message
        2. Check authentication
        3. Check rate limits
        4. Get/create session
        5. Route to text agent
        6. Queue response for delivery
        """
        telegram_id = message["from"]["id"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "")

        # Auth check
        user = await self.user_repository.get_by_telegram_id(telegram_id)
        if not user:
            return await self._prompt_registration(chat_id)

        # Rate limit check
        if not await self.rate_limiter.check(user.id):
            return await self._rate_limit_response(chat_id)

        # Process message
        session = await self.session_manager.get_or_create(user.id)
        response = await self.text_agent.process(
            user_id=user.id,
            message=text,
            session=session,
        )

        # Queue for delayed delivery (based on chapter timing)
        await self.response_delivery.queue(
            user_id=user.id,
            chat_id=chat_id,
            response=response,
            chapter=user.chapter,
        )
```

### Task 6: Implement Rate Limiter
**File**: `nikita/platforms/telegram/rate_limiter.py`

```python
from datetime import datetime, timedelta
from uuid import UUID

class RateLimiter:
    """Rate limiting for Telegram messages."""

    # Configuration
    MAX_PER_MINUTE = 20
    MAX_PER_DAY = 500

    def __init__(self, cache_client):
        self.cache = cache_client  # Redis or in-memory

    async def check(self, user_id: UUID) -> bool:
        """
        Check if user is within rate limits.

        Returns True if allowed, False if rate limited.
        """
        minute_key = f"rate:{user_id}:minute"
        day_key = f"rate:{user_id}:day:{datetime.now().date()}"

        minute_count = await self.cache.incr(minute_key)
        if minute_count == 1:
            await self.cache.expire(minute_key, 60)

        if minute_count > self.MAX_PER_MINUTE:
            return False

        day_count = await self.cache.incr(day_key)
        if day_count == 1:
            await self.cache.expire(day_key, 86400)

        if day_count > self.MAX_PER_DAY:
            return False

        return True

    async def get_remaining(self, user_id: UUID) -> dict:
        """Get remaining quota for user."""
        pass
```

### Task 7: Implement Session Manager
**File**: `nikita/platforms/telegram/session.py`

```python
class SessionManager:
    """Manage conversation sessions for Telegram users."""

    async def get_or_create(self, user_id: UUID) -> Session:
        """Get existing session or create new one."""
        pass

    async def update(self, session: Session) -> None:
        """Update session state."""
        pass

    async def get_context(self, user_id: UUID) -> ConversationContext:
        """Get conversation context for text agent."""
        pass
```

### Task 8: Implement Response Delivery
**File**: `nikita/platforms/telegram/delivery.py`

```python
class ResponseDelivery:
    """Handle response delivery with chapter-based timing."""

    async def queue(
        self,
        user_id: UUID,
        chat_id: int,
        response: str,
        chapter: int,
    ) -> None:
        """
        Queue response for delivery.

        Chapter 1-3: Variable delays (creates suspense)
        Chapter 4-5: Near-instant (secure relationship)
        """
        delay = self._calculate_delay(chapter)

        if delay > 0:
            # Store in pending_responses for pg_cron pickup
            await self._store_pending(user_id, chat_id, response, delay)
        else:
            # Immediate delivery
            await self._send_now(chat_id, response)

    async def _send_now(self, chat_id: int, response: str) -> None:
        """Send message immediately with typing indicator."""
        await self.bot.send_chat_action(chat_id, "typing")
        await asyncio.sleep(0.5)  # Brief typing indicator
        await self.bot.send_message(chat_id, response)

    def _calculate_delay(self, chapter: int) -> int:
        """Calculate response delay based on chapter."""
        from nikita.engine.constants import CHAPTER_BEHAVIORS

        # Chapter 1: 10min to 8 hours
        # Chapter 5: Consistent/immediate
        return random.randint(
            CHAPTER_DELAYS[chapter]["min"],
            CHAPTER_DELAYS[chapter]["max"],
        )
```

### Task 9: Implement Authentication Flow
**File**: `nikita/platforms/telegram/auth.py`

```python
class TelegramAuth:
    """Handle Telegram user authentication."""

    async def register_user(
        self,
        telegram_id: int,
        email: str,
    ) -> MagicLinkResult:
        """
        Initiate user registration with magic link.

        1. Create pending registration
        2. Send magic link to email
        3. Link telegram_id on verification
        """
        pass

    async def verify_magic_link(self, token: str) -> User:
        """Verify magic link and complete registration."""
        pass

    async def link_telegram(
        self,
        user_id: UUID,
        telegram_id: int,
    ) -> None:
        """Link Telegram ID to existing user."""
        pass
```

---

## API Integration

### FastAPI Routes (extends 010-api-infrastructure)
**File**: `nikita/api/routes/telegram.py`

```python
from fastapi import APIRouter, Request, HTTPException
from nikita.platforms.telegram.handlers import WebhookHandler

router = APIRouter(prefix="/telegram", tags=["telegram"])

@router.post("/webhook")
async def telegram_webhook(request: Request):
    """
    Receive Telegram webhook updates.

    Validates Telegram secret header before processing.
    """
    # Validate request is from Telegram
    if not await _validate_telegram_request(request):
        raise HTTPException(status_code=403)

    update = await request.json()
    await webhook_handler.handle_update(TelegramUpdate(**update))

    return {"ok": True}

@router.post("/set-webhook")
async def set_webhook(url: str):
    """Configure Telegram webhook URL."""
    result = await bot.set_webhook(url)
    return result
```

---

## Configuration

### Environment Variables
**File**: `nikita/config/settings.py` (additions)

```python
class Settings:
    # Telegram
    telegram_bot_token: str  # @NikitaBot token
    telegram_webhook_secret: str  # Webhook validation

    # Rate limiting
    telegram_rate_limit_minute: int = 20
    telegram_rate_limit_day: int = 500
```

---

## User Story Mapping

| User Story | Tasks | Components |
|------------|-------|------------|
| US-1: Onboarding | T4, T9 | CommandHandler._handle_start, TelegramAuth |
| US-2: Send Message | T5, T8 | MessageHandler, ResponseDelivery |
| US-3: Session Persistence | T7 | SessionManager |
| US-4: Rate Limiting | T6 | RateLimiter |
| US-5: Typing Indicators | T8 | ResponseDelivery._send_now |
| US-6: Media Handling | T3 | WebhookHandler._handle_media |
| US-7: Error Recovery | T3, T5 | Error handling in handlers |
| US-8: Commands | T4 | CommandHandler |

---

## Implementation Order

```
Phase 1: Foundation
├── T1: Module structure
├── T2: Bot client
└── T3: Webhook handler

Phase 2: Core Messaging (US-2)
├── T5: Message handler
├── T7: Session manager
└── T8: Response delivery

Phase 3: Authentication (US-1)
├── T4: Command handlers
└── T9: Auth flow

Phase 4: Protection (US-4)
└── T6: Rate limiter

Phase 5: Polish (US-5, US-6, US-7)
└── Tests and refinements
```

---

## Constitution Alignment

**§I.1 Invisible Game Interface**:
- ✅ Platform is Telegram (no custom UI)
- ✅ Commands hidden unless requested
- ✅ Response timing creates "real person" illusion

**§VI.2 UX Excellence**:
- ✅ Typing indicators (FR-009)
- ✅ Media handling with in-character responses (FR-010)
- ✅ Graceful error handling (FR-008)

**§VII.1 Test-Driven Development**:
- ✅ Tests before implementation
- ✅ 80%+ coverage required

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-29 | Initial plan from spec.md |
