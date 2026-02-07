# Onboarding

```yaml
context_priority: high
audience: ai_agents
last_updated: 2026-02-03
related_docs:
  - AUTHENTICATION.md
  - USER_JOURNEY.md
  - VOICE_IMPLEMENTATION.md
```

## Overview

Nikita has two onboarding paths:
- **Voice Onboarding** (Primary) - Conversational via Meta-Nikita agent
- **Text Onboarding** (Fallback) - Form-like via Telegram

The goal is to collect user profile data before the first Nikita conversation.

---

## Onboarding Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        ONBOARDING ARCHITECTURE                                │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                         ┌─────────────────┐                                  │
│                         │   NEW USER      │                                  │
│                         │   DETECTED      │                                  │
│                         └────────┬────────┘                                  │
│                                  │                                           │
│                    ┌─────────────┴─────────────┐                             │
│                    │                           │                              │
│                    ▼                           ▼                              │
│         ┌───────────────────┐       ┌───────────────────┐                   │
│         │   VOICE PATH      │       │   TEXT PATH       │                   │
│         │   (Preferred)     │       │   (Fallback)      │                   │
│         │                   │       │                   │                   │
│         │  Phone call       │       │  Telegram /start  │                   │
│         │  → Meta-Nikita    │       │  → Questions      │                   │
│         │  → Conversation   │       │  → Form-like      │                   │
│         └─────────┬─────────┘       └─────────┬─────────┘                   │
│                   │                           │                              │
│                   │                           │                              │
│                   ▼                           ▼                              │
│         ┌───────────────────┐       ┌───────────────────┐                   │
│         │  Profile          │       │  Profile          │                   │
│         │  Extraction       │       │  Collection       │                   │
│         │  (LLM)            │       │  (Direct)         │                   │
│         └─────────┬─────────┘       └─────────┬─────────┘                   │
│                   │                           │                              │
│                   └───────────┬───────────────┘                              │
│                               │                                              │
│                               ▼                                              │
│                    ┌───────────────────┐                                    │
│                    │  PROFILE STORED   │                                    │
│                    │  onboarding_status│                                    │
│                    │  = completed      │                                    │
│                    └─────────┬─────────┘                                    │
│                              │                                               │
│                              ▼                                               │
│                    ┌───────────────────┐                                    │
│                    │  HANDOFF TO       │                                    │
│                    │  NIKITA AGENT     │                                    │
│                    └───────────────────┘                                    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Voice Onboarding (Meta-Nikita)

### Concept

Meta-Nikita is a separate ElevenLabs agent designed specifically for onboarding. It:
- Has a friendly, welcoming personality
- Asks conversational questions about the user
- Extracts profile data using LLM
- Stores profile via server tool
- Hands off to the main Nikita agent

### Agent Configuration

**Agent ID**: `ELEVENLABS_AGENT_META_NIKITA`

**System Prompt** (simplified):
```
You are Meta-Nikita, a friendly assistant helping users get started with Nikita.

Your goal is to learn about the user through natural conversation:
1. Their name and what they'd like to be called
2. What they do for work or study
3. Their hobbies and interests
4. What kind of relationship they're looking for

Keep the conversation natural and friendly. When you have enough information,
use the store_user_profile tool to save their profile, then say goodbye and
let them know Nikita will call them soon.

If the user wants to skip onboarding, that's okay! Just store minimal info
and set onboarding_status to "skipped".
```

### Server Tools

**File**: `nikita/onboarding/server_tools.py:1-150`

| Tool | Purpose | Parameters |
|------|---------|------------|
| `store_user_profile` | Save extracted profile | name, occupation, hobbies, goals |
| `get_caller_info` | Get caller's phone | (automatic) |
| `complete_onboarding` | Mark as complete | user_id |

```python
# nikita/onboarding/server_tools.py:30-80

@with_timeout_fallback(timeout=2.0)
async def store_user_profile(
    user_id: str,
    signed_token: str,
    display_name: str,
    occupation: Optional[str] = None,
    hobbies: Optional[List[str]] = None,
    relationship_goals: Optional[str] = None,
    personality_notes: Optional[str] = None
) -> Dict[str, Any]:
    """Store user profile from voice onboarding."""

    if not validate_voice_token(signed_token, user_id):
        return {"error": "Invalid token"}

    async with get_db_session() as session:
        repo = UserRepository(session)

        await repo.update(
            user_id=UUID(user_id),
            display_name=display_name,
            occupation=occupation,
            hobbies=hobbies or [],
            relationship_goals=relationship_goals,
            personality_notes=personality_notes,
            onboarding_status="completed",
            onboarding_channel="voice"
        )

    return {"status": "success", "message": "Profile saved!"}
```

### Handoff Flow

**File**: `nikita/onboarding/handoff.py:1-100`

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        AGENT HANDOFF FLOW                                     │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐                                                            │
│  │ Meta-Nikita │                                                            │
│  │ completes   │                                                            │
│  │ profile     │                                                            │
│  └──────┬──────┘                                                            │
│         │                                                                    │
│         │ store_user_profile()                                              │
│         │ → onboarding_status = "completed"                                 │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Meta-Nikita says goodbye:                                           │   │
│  │  "It was great talking to you! Nikita is excited to meet you.       │   │
│  │   She'll reach out soon. Take care!"                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                                                                    │
│         │ Call ends                                                         │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Touchpoint system schedules first Nikita message                    │   │
│  │  (typically 1-2 hours later via Telegram)                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  User receives first Nikita message:                                 │   │
│  │  "Hey [name]! I heard you talked to my assistant earlier...         │   │
│  │   I'm Nikita. Nice to finally meet you! 😊"                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Pre-Call Routing

**File**: `nikita/api/routes/voice.py:50-100`

```python
# nikita/api/routes/voice.py:60-95

@router.post("/pre-call")
async def voice_pre_call(request: PreCallRequest, session: AsyncSession = Depends(get_db_session)):
    """Route incoming call to appropriate agent."""

    caller_id = request.caller_id
    repo = UserRepository(session)

    # Try to find existing user
    user = await repo.get_by_phone(caller_id)

    if not user:
        # NEW USER → Meta-Nikita onboarding
        # Create pending user record
        user = await repo.create_pending(
            phone_number=caller_id,
            onboarding_status="pending"
        )

        return {
            "agent_id": settings.ELEVENLABS_AGENT_META_NIKITA,
            "dynamic_variables": {
                "user_id": str(user.id),
                "signed_token": create_signed_token(user.id),
                "caller_phone": caller_id,
                "is_new_user": "true"
            }
        }

    if user.onboarding_status not in ("completed", "skipped"):
        # INCOMPLETE → Continue with Meta-Nikita
        return {
            "agent_id": settings.ELEVENLABS_AGENT_META_NIKITA,
            "dynamic_variables": {
                "user_id": str(user.id),
                "signed_token": create_signed_token(user.id),
                "is_new_user": "false"
            }
        }

    # EXISTING USER → Main Nikita agent
    return {
        "agent_id": settings.ELEVENLABS_AGENT_ID,
        "dynamic_variables": build_dynamic_variables(user)
    }
```

---

## Text Onboarding

### Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        TEXT ONBOARDING FLOW                                   │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  User sends /start to Telegram                                              │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  CommandHandler detects new user                                     │   │
│  │  → Redirects to RegistrationHandler                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Step 1: Phone Verification                                          │   │
│  │  Bot: "Welcome! Please share your phone number to get started."     │   │
│  │  User: [Shares contact or enters number]                            │   │
│  │  → OTP sent via Supabase                                            │   │
│  │  → User enters code                                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Step 2: Name                                                        │   │
│  │  Bot: "Great! What's your name?"                                    │   │
│  │  User: "Alex"                                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Step 3: Occupation                                                  │   │
│  │  Bot: "Nice to meet you, Alex! What do you do for work?"           │   │
│  │  User: "Software engineer"                                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Step 4: Hobbies                                                     │   │
│  │  Bot: "Cool! What do you like to do for fun?"                       │   │
│  │  User: "Gaming, hiking, cooking"                                    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Step 5: Relationship Goals                                          │   │
│  │  Bot: "Last question - what kind of relationship are you looking   │   │
│  │        for with Nikita?"                                            │   │
│  │  User: "Someone to chat with, have fun"                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Complete!                                                           │   │
│  │  Bot: "Perfect! Let me introduce you to Nikita..."                  │   │
│  │  → onboarding_status = "completed"                                  │   │
│  │  → First Nikita message sent immediately                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Registration Handler

**File**: `nikita/platforms/telegram/registration_handler.py:1-200`

```python
# nikita/platforms/telegram/registration_handler.py:30-100

class RegistrationHandler:
    """Handle text-based onboarding flow."""

    STEPS = [
        "phone_verification",
        "name",
        "occupation",
        "hobbies",
        "relationship_goals"
    ]

    async def can_handle(self, update: Update) -> bool:
        """Check if user is in onboarding flow."""
        user = await self.repo.get_by_telegram_id(update.message.from_user.id)
        return user and user.onboarding_status == "in_progress"

    async def handle(self, update: Update) -> None:
        """Process onboarding step."""
        user = await self.repo.get_by_telegram_id(update.message.from_user.id)
        current_step = user.onboarding_step or 0

        # Process current step
        if current_step == 0:
            await self._handle_phone(update, user)
        elif current_step == 1:
            await self._handle_name(update, user)
        elif current_step == 2:
            await self._handle_occupation(update, user)
        elif current_step == 3:
            await self._handle_hobbies(update, user)
        elif current_step == 4:
            await self._handle_relationship_goals(update, user)
            await self._complete_onboarding(user)

    async def _complete_onboarding(self, user: User) -> None:
        """Mark onboarding complete and send first Nikita message."""
        await self.repo.update(
            user_id=user.id,
            onboarding_status="completed",
            onboarding_channel="text"
        )

        # Send first Nikita message
        first_message = await self._generate_first_message(user)
        await self.bot.send_message(user.telegram_id, first_message)
```

### Skip Option

Users can skip onboarding with `/skip`:

```python
# nikita/platforms/telegram/commands.py:80-100

async def handle_skip(self, update: Update) -> None:
    """Allow user to skip detailed onboarding."""
    user = await self.repo.get_by_telegram_id(update.message.from_user.id)

    if user.onboarding_status not in ("pending", "in_progress"):
        return

    # Get just the name
    await self.bot.send_message(
        update.message.chat.id,
        "No problem! Just tell me your name and we'll get started."
    )

    await self.repo.update(
        user_id=user.id,
        onboarding_status="skipped",
        onboarding_channel="text"
    )
```

---

## Profile Data Collected

### Core Fields

| Field | Voice Source | Text Source | Required |
|-------|-------------|-------------|----------|
| `display_name` | LLM extraction | Direct question | Yes |
| `phone_number` | Caller ID | Telegram share + OTP | Yes |
| `occupation` | LLM extraction | Direct question | No |
| `hobbies` | LLM extraction | Direct question | No |
| `relationship_goals` | LLM extraction | Direct question | No |
| `personality_notes` | LLM inference | Not collected | No |

### Voice Extraction Prompt

**File**: `nikita/onboarding/meta_nikita.py:50-100`

```
Based on this conversation, extract the following profile information:

1. display_name: What the user wants to be called
2. occupation: Their job or main activity
3. hobbies: List of interests and hobbies mentioned
4. relationship_goals: What they're looking for
5. personality_notes: Any observations about their personality

Respond in JSON format:
{
  "display_name": "...",
  "occupation": "...",
  "hobbies": ["...", "..."],
  "relationship_goals": "...",
  "personality_notes": "..."
}
```

---

## Onboarding States

### Status Values

| Status | Description | Can Message Nikita |
|--------|-------------|-------------------|
| `pending` | Just created, no data | No |
| `in_progress` | Answering questions | No |
| `completed` | Finished all steps | Yes |
| `skipped` | Skipped via /skip or voice | Yes |

### State Machine

```
             ┌──────────────────────────────────────────┐
             │                                          │
             ▼                                          │
┌─────────┐      ┌─────────────┐      ┌─────────────┐ │
│ pending │─────▶│ in_progress │─────▶│ completed   │─┘
└─────────┘      └──────┬──────┘      └─────────────┘
                        │
                        │ /skip or voice skip
                        ▼
                 ┌─────────────┐
                 │  skipped    │
                 └─────────────┘
```

---

## First Nikita Message

### Voice Path

After voice onboarding, the first Nikita message is scheduled via touchpoints:

```python
# nikita/touchpoints/engine.py:100-130

async def schedule_first_message(user_id: UUID) -> None:
    """Schedule first Nikita message after onboarding."""
    delay_hours = random.uniform(1, 3)  # 1-3 hours

    await ScheduledMessageRepository.create(
        user_id=user_id,
        message_type="first_nikita_message",
        scheduled_for=datetime.now(UTC) + timedelta(hours=delay_hours)
    )
```

### Text Path

After text onboarding, first message is sent immediately:

```python
# nikita/platforms/telegram/registration_handler.py:150-180

async def _generate_first_message(self, user: User) -> str:
    """Generate Nikita's first message after onboarding."""

    template = """
    Hey {name}! I'm Nikita 😊

    {opener}

    So... what are you up to right now?
    """

    openers = [
        "I've been looking forward to meeting you!",
        "I heard a bit about you and you seem really interesting.",
        "Finally! I was wondering when we'd get to talk.",
    ]

    return template.format(
        name=user.display_name,
        opener=random.choice(openers)
    )
```

---

## Key File References

| File | Line | Purpose |
|------|------|---------|
| `nikita/onboarding/meta_nikita.py` | 1-150 | Meta-Nikita agent config |
| `nikita/onboarding/server_tools.py` | 1-150 | Voice onboarding tools |
| `nikita/onboarding/handoff.py` | 1-100 | Agent handoff logic |
| `nikita/platforms/telegram/registration_handler.py` | 1-200 | Text onboarding |
| `nikita/api/routes/voice.py` | 50-100 | Pre-call routing |

---

## Testing Onboarding

### Test User States

**File**: `tests/fixtures/users.py`

```python
# Test users at different onboarding states
@pytest.fixture
def pending_user():
    return create_user(onboarding_status="pending")

@pytest.fixture
def in_progress_user():
    return create_user(onboarding_status="in_progress", onboarding_step=2)

@pytest.fixture
def completed_user():
    return create_user(onboarding_status="completed")

@pytest.fixture
def skipped_user():
    return create_user(onboarding_status="skipped")
```

### E2E Test Flow

```bash
# Voice onboarding E2E
pytest tests/e2e/test_voice_onboarding.py -v

# Text onboarding E2E
pytest tests/e2e/test_text_onboarding.py -v
```

---

## Related Documentation

- **Authentication Details**: [AUTHENTICATION.md](AUTHENTICATION.md)
- **User Journey**: [USER_JOURNEY.md](USER_JOURNEY.md)
- **Voice Agent**: [VOICE_IMPLEMENTATION.md](VOICE_IMPLEMENTATION.md)
- **Integrations**: [INTEGRATIONS.md](INTEGRATIONS.md)
