# Authentication

```yaml
context_priority: high
audience: ai_agents
last_updated: 2026-02-03
related_docs:
  - ONBOARDING.md
  - INTEGRATIONS.md
  - DATABASE_SCHEMA.md
```

## Overview

Nikita uses multiple authentication mechanisms:
- **OTP (One-Time Password)** - Phone verification via Telegram
- **JWT (JSON Web Tokens)** - Session management via Supabase
- **Telegram Phone Linking** - Associate Telegram with phone number
- **Admin Authentication** - Domain-based admin access

---

## Authentication Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        AUTHENTICATION ARCHITECTURE                            │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────┐                        ┌─────────────────┐             │
│  │   New User      │                        │  Returning User │             │
│  │  (Telegram)     │                        │  (Telegram)     │             │
│  └────────┬────────┘                        └────────┬────────┘             │
│           │                                          │                       │
│           │ /start                                   │ message               │
│           ▼                                          ▼                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    Telegram Webhook Handler                          │   │
│  │                    @ telegram.py:20-80                               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│           │                                          │                       │
│           │ User not found                           │ User found            │
│           ▼                                          ▼                       │
│  ┌─────────────────┐                        ┌─────────────────┐             │
│  │  OTP Flow       │                        │  JWT Validation │             │
│  │  (Phone verify) │                        │  (if portal)    │             │
│  └────────┬────────┘                        └────────┬────────┘             │
│           │                                          │                       │
│           ▼                                          ▼                       │
│  ┌─────────────────┐                        ┌─────────────────┐             │
│  │  Create User +  │                        │  Load User      │             │
│  │  Link Telegram  │                        │  Context        │             │
│  └─────────────────┘                        └─────────────────┘             │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## OTP Verification

### Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           OTP VERIFICATION FLOW                               │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐                                                            │
│  │ User shares │                                                            │
│  │ phone number│                                                            │
│  │ via Telegram│                                                            │
│  └──────┬──────┘                                                            │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  1. Create pending_registration record                               │   │
│  │     @ otp_handler.py:30-60                                          │   │
│  │                                                                      │   │
│  │  - Generate 6-8 digit OTP                                           │   │
│  │  - Store with telegram_id, phone_number                             │   │
│  │  - Set expires_at = now + 10 minutes                                │   │
│  │  - Set attempts = 0                                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  2. Send OTP via Supabase Auth                                       │   │
│  │     @ auth_service.py:50-80                                         │   │
│  │                                                                      │   │
│  │  - Call supabase.auth.sign_in_with_otp(phone=phone_number)          │   │
│  │  - Supabase sends SMS with OTP                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  3. User enters OTP in Telegram                                      │   │
│  │     (6-8 digit code detected by OTPHandler)                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  4. Verify OTP                                                       │   │
│  │     @ otp_handler.py:80-130                                         │   │
│  │                                                                      │   │
│  │  - Check pending_registration exists                                │   │
│  │  - Check not expired (< 10 min)                                     │   │
│  │  - Check attempts < 3                                               │   │
│  │  - Verify OTP via Supabase                                          │   │
│  │  - Increment attempts on failure                                    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                                                                    │
│         ├──── FAIL ────▶ "Invalid code, X attempts remaining"               │
│         │                                                                    │
│         └──── SUCCESS ──▶                                                   │
│                         ▼                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  5. Create or link user                                              │   │
│  │     @ user_repository.py:100-150                                    │   │
│  │                                                                      │   │
│  │  - Create user record with phone_number, telegram_id                │   │
│  │  - Create user_metrics with default values                          │   │
│  │  - Delete pending_registration                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### OTP Handler Implementation

**File**: `nikita/platforms/telegram/otp_handler.py:1-150`

```python
# nikita/platforms/telegram/otp_handler.py:30-100

class OTPHandler:
    """Handler for OTP verification codes."""

    OTP_PATTERN = re.compile(r"^\d{6,8}$")
    MAX_ATTEMPTS = 3
    OTP_TTL_MINUTES = 10

    async def can_handle(self, update: Update) -> bool:
        """Check if message is an OTP code."""
        if not update.message or not update.message.text:
            return False

        text = update.message.text.strip()
        return bool(self.OTP_PATTERN.match(text))

    async def handle(self, update: Update) -> None:
        """Verify OTP and complete registration."""
        telegram_id = update.message.from_user.id
        otp_code = update.message.text.strip()

        # Get pending registration
        registration = await self.repo.get_pending(telegram_id)

        if not registration:
            await self.bot.send_message(
                telegram_id,
                "No pending verification. Please share your phone number first."
            )
            return

        # Check expiration
        if datetime.now(UTC) > registration.expires_at:
            await self.repo.delete(registration.id)
            await self.bot.send_message(
                telegram_id,
                "Code expired. Please share your phone number again."
            )
            return

        # Check attempts
        if registration.attempts >= self.MAX_ATTEMPTS:
            await self.repo.delete(registration.id)
            await self.bot.send_message(
                telegram_id,
                "Too many attempts. Please share your phone number again."
            )
            return

        # Verify with Supabase
        try:
            result = await self.supabase.auth.verify_otp(
                phone=registration.phone_number,
                token=otp_code,
                type="sms"
            )
        except Exception:
            # Increment attempts
            await self.repo.increment_attempts(registration.id)
            remaining = self.MAX_ATTEMPTS - registration.attempts - 1
            await self.bot.send_message(
                telegram_id,
                f"Invalid code. {remaining} attempts remaining."
            )
            return

        # Success - create user
        await self._create_user(telegram_id, registration, result.user)
```

### Pending Registration Model

**File**: `nikita/db/models/pending_registration.py:1-50`

```python
# nikita/db/models/pending_registration.py:10-40

class PendingRegistration(Base):
    """Pending OTP verification records."""

    __tablename__ = "pending_registrations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    telegram_id = Column(BigInteger, nullable=False, unique=True)
    phone_number = Column(String(20), nullable=False)
    otp_code = Column(String(8), nullable=False)
    attempts = Column(Integer, default=0)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
```

---

## JWT Authentication

### Supabase JWT Structure

```json
{
  "aud": "authenticated",
  "exp": 1738000000,
  "iat": 1737996400,
  "iss": "https://xxx.supabase.co/auth/v1",
  "sub": "uuid-of-user",
  "email": "user@example.com",
  "phone": "+1234567890",
  "app_metadata": {
    "provider": "phone"
  },
  "user_metadata": {
    "telegram_id": 123456789
  }
}
```

### JWT Validation

**File**: `nikita/api/dependencies/auth.py:1-100`

```python
# nikita/api/dependencies/auth.py:30-80

async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_db_session)
) -> User:
    """Extract and validate user from JWT."""

    # Get token from header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header"
        )

    token = auth_header.split(" ")[1]

    # Decode and validate
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated"
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Get user from database
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    repo = UserRepository(session)
    user = await repo.get_by_id(UUID(user_id))

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user
```

### Admin Authentication

**File**: `nikita/api/dependencies/auth.py:100-150`

```python
# nikita/api/dependencies/auth.py:100-140

async def get_current_admin_user(
    request: Request,
    session: AsyncSession = Depends(get_db_session)
) -> User:
    """Get admin user - must have @silent-agents.com email."""

    user = await get_current_user(request, session)

    # Check admin domain
    auth_header = request.headers.get("Authorization")
    token = auth_header.split(" ")[1]
    payload = jwt.decode(token, settings.SUPABASE_JWT_SECRET, algorithms=["HS256"])

    email = payload.get("email", "")
    if not email.endswith("@silent-agents.com"):
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    return user
```

---

## Telegram Phone Linking

### Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        TELEGRAM PHONE LINKING                                 │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                   │
│  │ Telegram    │     │  Portal     │     │   Phone     │                   │
│  │ User        │     │  User       │     │   (same)    │                   │
│  │ (123456)    │     │  (uuid-xyz) │     │             │                   │
│  └──────┬──────┘     └──────┬──────┘     └─────────────┘                   │
│         │                   │                                               │
│         │                   │                                               │
│         ▼                   ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Link Request (from Portal)                                          │   │
│  │  POST /api/v1/portal/link-telegram                                  │   │
│  │  { "phone_number": "+1234567890" }                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  1. Find existing user by phone                                      │   │
│  │  2. Check if user has telegram_id                                   │   │
│  │  3. Create telegram_link record                                     │   │
│  │  4. Wait for Telegram message                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  User sends /link in Telegram                                        │   │
│  │  - CommandHandler detects pending link                              │   │
│  │  - Updates user.telegram_id                                         │   │
│  │  - Deletes telegram_link record                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Link Endpoint

**File**: `nikita/api/routes/portal.py:150-200`

```python
# nikita/api/routes/portal.py:160-190

@router.post("/link-telegram")
async def link_telegram(
    request: LinkTelegramRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """Initiate Telegram account linking."""

    # Check if user already has telegram
    if current_user.telegram_id:
        raise HTTPException(
            status_code=400,
            detail="Telegram already linked"
        )

    # Create link record
    link_repo = TelegramLinkRepository(session)
    link = await link_repo.create(
        user_id=current_user.id,
        phone_number=request.phone_number,
        expires_at=datetime.now(UTC) + timedelta(hours=24)
    )

    return {
        "status": "pending",
        "instructions": "Send /link to @Nikita_my_bot from your Telegram account"
    }
```

---

## Voice Authentication

### Signed Token Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        VOICE AUTHENTICATION                                   │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐                                                            │
│  │ User calls  │                                                            │
│  │ Nikita phone│                                                            │
│  └──────┬──────┘                                                            │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  ElevenLabs pre-call webhook                                         │   │
│  │  POST /api/v1/voice/pre-call                                        │   │
│  │  { "caller_id": "+1234567890" }                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  1. Lookup user by phone number                                      │   │
│  │  2. If found: create signed_token (30 min TTL)                      │   │
│  │  3. Return dynamic_variables with user_id + signed_token            │   │
│  │  4. If not found: route to onboarding agent                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Server tool calls include signed_token for validation               │   │
│  │  get_context(user_id, signed_token)                                 │   │
│  │  → Validates token before returning data                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Pre-Call Handler

**File**: `nikita/api/routes/voice.py:50-100`

```python
# nikita/api/routes/voice.py:60-95

@router.post("/pre-call")
async def voice_pre_call(
    request: PreCallRequest,
    session: AsyncSession = Depends(get_db_session)
):
    """Handle ElevenLabs pre-call webhook."""

    caller_id = request.caller_id

    # Lookup user by phone
    repo = UserRepository(session)
    user = await repo.get_by_phone(caller_id)

    if not user:
        # Route to onboarding agent
        return {
            "agent_id": settings.ELEVENLABS_AGENT_META_NIKITA,
            "dynamic_variables": {
                "caller_phone": caller_id,
                "is_new_user": "true"
            }
        }

    # Create signed token
    signed_token = create_signed_token(user.id)

    # Return user context
    metrics = await repo.get_metrics(user.id)

    return {
        "agent_id": settings.ELEVENLABS_AGENT_ID,
        "dynamic_variables": {
            "user_id": str(user.id),
            "signed_token": signed_token,
            "user_name": user.display_name,
            "chapter": str(metrics.chapter_number),
            # ... more variables
        }
    }
```

---

## Profile Gates

### Onboarding Status Check

**File**: `nikita/platforms/telegram/message_handler.py:80-120`

```python
# nikita/platforms/telegram/message_handler.py:90-115

async def handle_message(self, update: Update) -> None:
    """Handle incoming message."""

    user = await self.repo.get_by_telegram_id(update.message.from_user.id)

    if not user:
        # Redirect to registration
        await self.redirect_to_registration(update)
        return

    # Check onboarding status
    if user.onboarding_status not in ("completed", "skipped"):
        await self.redirect_to_onboarding(update)
        return

    # Check game over
    if user.chapter_number > 5:
        await self.send_game_over_message(update)
        return

    # Process message normally
    await self.process_message(update, user)
```

### Valid Onboarding States

| Status | Description | Can Message |
|--------|-------------|-------------|
| `pending` | Just started | No |
| `in_progress` | Answering questions | No |
| `completed` | Finished onboarding | Yes |
| `skipped` | Skipped via voice | Yes |

---

## Security Measures

### SEC-01: Webhook Signature Validation

**File**: `nikita/platforms/telegram/webhook.py:30-60`

All Telegram webhooks validated with HMAC-SHA256.

### SEC-02: Rate Limiting

**File**: `nikita/platforms/telegram/rate_limiter.py:1-100`

- 20 requests/minute soft limit
- 500 requests/day hard limit
- Database-backed for persistence

### SEC-03: Token Expiration

| Token Type | TTL | Refresh |
|------------|-----|---------|
| Supabase JWT | 1 hour | Auto-refresh |
| Voice signed token | 30 minutes | Per-call |
| OTP code | 10 minutes | Manual resend |

---

## Key File References

| File | Line | Purpose |
|------|------|---------|
| `nikita/platforms/telegram/otp_handler.py` | 1-150 | OTP verification |
| `nikita/api/dependencies/auth.py` | 1-150 | JWT validation |
| `nikita/api/routes/voice.py` | 50-100 | Voice pre-call auth |
| `nikita/api/routes/portal.py` | 150-200 | Telegram linking |
| `nikita/db/models/pending_registration.py` | 1-50 | OTP state |

---

## Related Documentation

- **Onboarding Flow**: [ONBOARDING.md](ONBOARDING.md)
- **Integration Details**: [INTEGRATIONS.md](INTEGRATIONS.md)
- **Database Schema**: [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md)
