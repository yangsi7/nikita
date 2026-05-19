# 015-onboarding-fix: Implementation Plan (v2.0 - OTP)

## Overview

Implement OTP code entry flow for Telegram registration, replacing magic link redirect approach.

## Architecture Decision

### Selected Approach: OTP State Machine Pattern

**Why this approach**:
- User stays in Telegram throughout (no context switch)
- Simple state machine (pending → code_sent → verified)
- Uses Supabase OTP natively (no custom token generation)
- Minimal code changes to existing flow

**Alternatives considered**:
1. **Magic link with notification** - Still requires context switch, complex
2. **Telegram OAuth** - Requires bot setup, different auth flow
3. **Phone OTP** - Requires Twilio, adds cost

## Component Breakdown

### Component 1: Database Migration

**Purpose**: Add state tracking columns to pending_registrations

**Migration**: `add_chat_id_and_otp_state`
```sql
ALTER TABLE pending_registrations
  ADD COLUMN chat_id BIGINT,
  ADD COLUMN otp_state VARCHAR(20) DEFAULT 'pending';
```

**Model Update**: `nikita/db/models/pending_registration.py`
```python
class PendingRegistration(Base):
    # Existing columns...
    chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    otp_state: Mapped[str] = mapped_column(String(20), default="pending")
```

**Dependencies**: None
**Risks**: Low (additive change)

### Component 2: Auth Service - OTP Methods

**Purpose**: Send and verify OTP codes via Supabase

**File**: `nikita/platforms/telegram/auth.py`

**Method 1: send_otp_code()**
```python
async def send_otp_code(
    self, telegram_id: int, chat_id: int, email: str
) -> dict[str, str]:
    """Send 6-digit OTP code to email (no magic link redirect)."""
    # Validate email format
    if not self._is_valid_email(email):
        raise ValueError("Invalid email format")

    # Call Supabase WITHOUT emailRedirectTo = code-only mode
    response = await self.supabase.auth.sign_in_with_otp({
        "email": email,
        "options": {"should_create_user": True}
    })

    # Store pending with chat_id and state
    await self.pending_repo.store(
        telegram_id=telegram_id,
        email=email,
        chat_id=chat_id,
        otp_state="code_sent"
    )

    return {"status": "code_sent", "email": email}
```

**Method 2: verify_otp_code()**
```python
async def verify_otp_code(self, telegram_id: int, code: str) -> User:
    """Verify 6-digit code and complete registration."""
    # Get pending registration
    pending = await self.pending_repo.get(telegram_id)
    if not pending:
        raise ValueError("No pending registration found")

    if pending.otp_state != "code_sent":
        raise ValueError(f"Invalid state: {pending.otp_state}")

    # Verify with Supabase - CRITICAL: type="email" not "magiclink"
    response = await self.supabase.auth.verify_otp({
        "email": pending.email,
        "token": code,
        "type": "email",
    })

    supabase_user_id = UUID(response.user.id)

    # Create or link user
    existing = await self.user_repo.get(supabase_user_id)
    if existing:
        if existing.telegram_id is None:
            existing.telegram_id = telegram_id
            await self.user_repo.update(existing)
        user = existing
    else:
        user = await self.user_repo.create_with_metrics(
            user_id=supabase_user_id,
            telegram_id=telegram_id,
        )

    # Cleanup
    await self.pending_repo.delete(telegram_id)

    return user
```

**Dependencies**: PendingRegistrationRepository, UserRepository, Supabase client
**Risks**: Medium (Supabase API - verified from docs)

### Component 3: OTP Verification Handler

**Purpose**: Handle OTP code entry in Telegram chat

**New File**: `nikita/platforms/telegram/otp_handler.py`

```python
class OTPVerificationHandler:
    """Handle OTP code verification in Telegram chat."""

    def __init__(
        self,
        telegram_auth: TelegramAuth,
        bot: AsyncTeleBot,
        logger: Logger,
    ):
        self.telegram_auth = telegram_auth
        self.bot = bot
        self.logger = logger

    async def handle(self, telegram_id: int, chat_id: int, code: str) -> None:
        """Verify OTP code and send appropriate response."""
        try:
            user = await self.telegram_auth.verify_otp_code(telegram_id, code)

            self.logger.info(
                f"OTP verification successful: telegram_id={telegram_id}"
            )

            await self.bot.send_message(
                chat_id=chat_id,
                text="Perfect! You're all set up now. 💕\n\nSo... what's on your mind?"
            )

        except Exception as e:
            error_msg = str(e).lower()

            if "invalid" in error_msg or "expired" in error_msg:
                self.logger.warning(
                    f"OTP verification failed: telegram_id={telegram_id}, error={e}"
                )
                await self.bot.send_message(
                    chat_id=chat_id,
                    text="Hmm, that code doesn't look right. Check your email again? 🤔"
                )
            else:
                self.logger.error(
                    f"OTP verification error: telegram_id={telegram_id}, error={e}"
                )
                await self.bot.send_message(
                    chat_id=chat_id,
                    text="Something went wrong. Try /start again?"
                )
```

**Dependencies**: TelegramAuth, AsyncTeleBot
**Risks**: Low (simple handler)

### Component 4: Webhook State Detection

**Purpose**: Intercept 6-digit codes when awaiting OTP

**File**: `nikita/api/routes/telegram.py` (receive_webhook function)

**Add before existing message handling**:
```python
# Check if user is awaiting OTP code
pending = await pending_repo.get(telegram_id)
if pending and pending.otp_state == "code_sent":
    text = message.text.strip() if message.text else ""

    if text.isdigit() and len(text) == 6:
        # Looks like an OTP code - verify it
        await otp_handler.handle(telegram_id, chat_id, text)
    else:
        # Not a code - remind user
        await bot.send_message(
            chat_id=chat_id,
            text="I'm still waiting for that 6-digit code from your email! 📧"
        )
    return WebhookResponse()
```

**Dependencies**: PendingRegistrationRepository, OTPVerificationHandler
**Risks**: Low (simple condition check)

### Component 5: Registration Handler Update

**Purpose**: Use OTP flow instead of magic link

**File**: `nikita/platforms/telegram/registration_handler.py`

**Update handle_email_input()**:
```python
async def handle_email_input(
    self, telegram_id: int, chat_id: int, email: str
) -> None:
    """Handle email input and send OTP code."""
    try:
        result = await self.telegram_auth.send_otp_code(
            telegram_id=telegram_id,
            chat_id=chat_id,
            email=email
        )

        if result["status"] == "code_sent":
            await self.bot.send_message(
                chat_id=chat_id,
                text="I sent a 6-digit code to your email. Enter it here! 📧"
            )

    except Exception as e:
        self.logger.error(f"OTP send failed: {e}")
        await self.bot.send_message(
            chat_id=chat_id,
            text="Something went wrong sending the code. Try again?"
        )
```

**Dependencies**: TelegramAuth
**Risks**: Low (simple method update)

## Implementation Sequence

```
Phase 1: Database (10 min)
├── Create migration file
├── Update PendingRegistration model
└── Update store() method signature

Phase 2: Auth Service (30 min)
├── Add send_otp_code() method
├── Add verify_otp_code() method
└── Add unit tests

Phase 3: OTP Handler (20 min)
├── Create otp_handler.py
├── Implement handle() method
└── Add unit tests

Phase 4: Webhook Update (15 min)
├── Add OTP state detection
├── Integrate OTP handler
└── Add integration tests

Phase 5: Registration Handler (10 min)
├── Update handle_email_input()
└── Update message text

Phase 6: Tests & Cleanup (30 min)
├── Run all tests
├── Fix any failures
└── Mark auth_confirm as deprecated
```

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ USER SENDS EMAIL                                                 │
│ POST /webhook {"message": {"text": "user@example.com"}}         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ RegistrationHandler.handle_email_input()                         │
│ → TelegramAuth.send_otp_code(telegram_id, chat_id, email)       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Supabase: sign_in_with_otp({email, options})                    │
│ → Sends email with 6-digit code                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Database: pending_registrations.store(                           │
│   telegram_id, email, chat_id, otp_state="code_sent"            │
│ )                                                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Bot: "I sent a 6-digit code to your email. Enter it here! 📧"  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ USER ENTERS CODE                                                 │
│ POST /webhook {"message": {"text": "847291"}}                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Webhook: pending.otp_state == "code_sent" && len(text) == 6    │
│ → OTPVerificationHandler.handle(telegram_id, chat_id, code)     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ TelegramAuth.verify_otp_code(telegram_id, code)                  │
│ → Supabase: verify_otp({email, token, type: "email"})           │
│ → Returns: {user: {id: UUID}}                                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Database: users.create_with_metrics(user_id, telegram_id)        │
│ Database: pending_registrations.delete(telegram_id)              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Bot: "Perfect! You're all set up now. 💕"                       │
│ [CONVERSATION BEGINS]                                            │
└─────────────────────────────────────────────────────────────────┘
```

## Error Handling Matrix

| Error Condition | Detection | User Message | Log Level |
|-----------------|-----------|--------------|-----------|
| Invalid email format | Regex validation | "That doesn't look like an email" | WARNING |
| Supabase rate limit | 429 response | "Too many attempts. Wait a minute?" | WARNING |
| Invalid OTP code | `AuthApiError.code == "invalid_credentials"` | "That code doesn't look right" | WARNING |
| Expired OTP code | `AuthApiError.code == "otp_expired"` | "That code expired" | INFO |
| No pending registration | pending is None | "Something went wrong. Try /start" | WARNING |
| Database error | SQLAlchemy exception | "Something went wrong" | ERROR |
| Supabase API error | httpx exception | "Something went wrong" | ERROR |
| Max attempts exceeded | attempts >= 3 | "Too many failed attempts. Type /start" | WARNING |
| Tracking failure | pending_repo error | "Something went wrong" (fail-closed) | ERROR |

## Security Hardening (Implemented Dec 2025)

| Issue | Fix | File |
|-------|-----|------|
| **TOCTOU race condition** | Atomic SQL increment `.values(column=Column + 1)` | `pending_registration_repository.py` |
| **Unlimited retry bypass** | Fail-closed when tracking fails | `otp_handler.py` |
| **Limbo state** | Delete pending BEFORE user creation | `auth.py` |
| **Fragile error detection** | Use `AuthApiError.code` not string matching | `auth.py` |

### Atomic SQL Increment

Prevents race condition where concurrent OTP requests bypass MAX_ATTEMPTS:

```python
# BEFORE (vulnerable to race):
pending = await self.pending_repo.get(telegram_id)
pending.otp_attempts += 1  # TOCTOU: two requests read 0, both write 1
await session.commit()

# AFTER (atomic):
stmt = (
    update(PendingRegistration)
    .where(PendingRegistration.telegram_id == telegram_id)
    .values(otp_attempts=PendingRegistration.otp_attempts + 1)
    .returning(PendingRegistration.otp_attempts)
)
```

### Fail-Closed Security

If attempt tracking fails for any reason, deny access rather than allow through:

```python
if self.pending_repo is None:
    # SECURITY: Fail closed - force restart
    await self.bot.send_message(chat_id, "Something went wrong. Type /start")
    return False

try:
    new_attempts = await self.pending_repo.increment_attempts(telegram_id)
except Exception:
    # SECURITY: Fail closed on any tracking error
    await self.pending_repo.delete(telegram_id)  # Best effort cleanup
    await self.bot.send_message(chat_id, "Something went wrong. Type /start")
    return False
```

### Limbo State Prevention

Delete pending registration BEFORE user creation to ensure user can restart if creation fails:

```python
# Supabase verification succeeded
supabase_user_id = UUID(response.user.id)

# Delete BEFORE user creation - if next step fails, user can /start again
await self.pending_repo.delete(telegram_id)

# Now create user (if this fails, Supabase auth is verified, user can retry)
user = await self.user_repo.create_with_metrics(user_id, telegram_id)
```

### Error Code Detection

Use `AuthApiError.code` instead of fragile string matching per Supabase best practices:

```python
from supabase_auth.errors import AuthApiError

except AuthApiError as e:
    if e.code == "otp_expired":
        raise ValueError("OTP code has expired...")
    elif e.code == "invalid_credentials":
        raise ValueError("Invalid OTP code...")
```

## Rollback Plan

If issues are discovered after deployment:
1. Set feature flag `ENABLE_OTP_REGISTRATION=false` to revert to magic link
2. Database migration is additive - no rollback needed
3. Old magic links continue to work via `auth_confirm` endpoint
4. Can redeploy previous version instantly via Cloud Run revisions

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| OTP send success rate | >99% | Logs: send_otp_code success/failure |
| OTP verify success rate | >90% | Logs: verify_otp_code success/failure |
| Registration completion rate | >80% | OTP sent → user created |
| Time to registration | <60 seconds | User experience |

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-12 | Claude | Initial plan (magic link approach) |
| 2.0 | 2025-12-14 | Claude | Redesigned for OTP state machine |
| 2.1 | 2025-12-19 | Claude | Added OTP retry limit + otp_attempts field |
| 2.2 | 2025-12-20 | Claude | Security hardening: atomic SQL, fail-closed, limbo prevention, error codes |
