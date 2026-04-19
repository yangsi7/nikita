# Technical Specification: Spec 214 Onboarding Overhaul (FR-11c / FR-11d / FR-11e)

**Date**: 2026-04-19
**Companion to**: `specs/214-portal-onboarding-wizard/spec.md` (functional spec, amended 2026-04-19)
**Prior shipped scope** (PR-A/B/C/D, FR-1 through FR-11b): unchanged; this technical spec covers ONLY the new FRs.

This document specifies the technical design for the three new amendments:

- **FR-11c**: eliminate legacy in-Telegram Q&A, route all Telegram entry to portal.
- **FR-11d**: chat-first conversational wizard with Pydantic AI agent + tool-use extraction.
- **FR-11e**: ceremonial portal→Telegram handoff with proactive bot greeting on bind.

---

## 1. System overview

```
portal (Next.js)                 backend (FastAPI, Cloud Run)      telegram bot
┌─────────────────────┐           ┌────────────────────────┐       ┌──────────────────┐
│ /onboarding         │  POST     │ /portal/onboarding/    │       │ /start            │
│ ChatShell           │─────────> │   converse             │       │ commands.py       │
│   MessageBubble     │  <─────── │   ConversationAgent    │       │  _handle_start    │
│   TypingIndicator   │           │     (Pydantic AI)      │       │  _handle_start_   │
│   InlineControl     │           │     Claude Sonnet      │       │    with_payload   │
│   ProgressHeader    │           │     Nikita persona     │       │  message_handler  │
│ ClearanceGranted    │           │     Tool-use           │       │                   │
│   Ceremony (FR-11e) │           │     extraction         │       │ generate_portal_  │
│                     │           │                        │       │   bridge_url      │
│ uses:               │           │ persists:              │       │ FirstMessage      │
│   useConversation   │           │   users.onboarding_    │       │   Generator       │
│     State (new)     │           │     profile.conversa-  │       │     (trigger=     │
│   useOnboardingAPI  │           │     tion JSONB         │       │      handoff_bind)│
│     .converse()     │           │                        │       │                   │
└─────────────────────┘           └────────────────────────┘       └──────────────────┘
        │                                    │                              │
        └──── localStorage (NR-1b v2) ───────┘                              │
        │                                                                   │
        └── Step 11 CTA: t.me/Nikita_my_bot?start=<code> (PR #322) ────────┘
```

## 2. Backend: new modules

### 2.1 Conversation agent

**Path**: `nikita/agents/onboarding/conversation_agent.py`

```python
from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel

from nikita.agents.text.persona import NIKITA_PERSONA  # verbatim reuse, no fork
from nikita.agents.onboarding.conversation_prompts import WIZARD_SYSTEM_PROMPT
from nikita.agents.onboarding.extraction_schemas import (
    LocationExtraction, SceneExtraction, DarknessExtraction,
    IdentityExtraction, BackstoryExtraction, PhoneExtraction,
    ConverseResult,
)
from nikita.config.settings import get_settings


def get_conversation_agent() -> Agent[ConverseDeps, ConverseResult]:
    settings = get_settings()
    model = AnthropicModel(settings.anthropic_model_id)  # same as main text agent
    agent = Agent(
        model=model,
        deps_type=ConverseDeps,
        result_type=ConverseResult,
        system_prompt=WIZARD_SYSTEM_PROMPT,  # composes NIKITA_PERSONA + wizard framing
    )
    # Tool-use for structured extraction per topic (one tool per schema)
    agent.tool_plain(LocationExtraction)
    agent.tool_plain(SceneExtraction)
    agent.tool_plain(DarknessExtraction)
    agent.tool_plain(IdentityExtraction)
    agent.tool_plain(BackstoryExtraction)
    agent.tool_plain(PhoneExtraction)
    return agent
```

**Contract**:
- Stateless per call. No memory, no chapter context, no recall_memory tool.
- Input: full conversation history + new user input.
- Output: `ConverseResult` Pydantic model (see 2.3 endpoint contract).
- Model: same Claude Sonnet as the main text agent (voice consistency).
- Prompt caching enabled on the system prompt block (NIKITA_PERSONA is long; benefits from cache).

### 2.2 Extraction schemas

**Path**: `nikita/agents/onboarding/extraction_schemas.py`

One Pydantic model per wizard topic. Each is a tool the agent can call to commit an extraction:

```python
class LocationExtraction(BaseModel):
    """Call this when the user has given a location. Confidence MUST be 0.0-1.0."""
    city: str = Field(min_length=2, max_length=100)
    confidence: float = Field(ge=0.0, le=1.0)

class SceneExtraction(BaseModel):
    """Call this when the user has chosen a scene."""
    scene: Literal["techno", "art", "food", "cocktails", "nature"]
    life_stage: Optional[Literal["tech", "finance", "creative", "student", "entrepreneur", "other"]] = None
    confidence: float = Field(ge=0.0, le=1.0)

class DarknessExtraction(BaseModel):
    """Call this when the user has given a 1-5 darkness rating."""
    drug_tolerance: int = Field(ge=1, le=5)
    confidence: float = Field(ge=0.0, le=1.0)

class IdentityExtraction(BaseModel):
    """Call this when user has given at least one of name/age/occupation."""
    name: Optional[str] = Field(default=None, max_length=100)
    age: Optional[int] = Field(default=None, ge=18, le=99)  # <18 triggers in-character validation
    occupation: Optional[str] = Field(default=None, max_length=100)
    confidence: float = Field(ge=0.0, le=1.0)

class BackstoryExtraction(BaseModel):
    """Call this when the user has picked a backstory scenario."""
    chosen_option_id: str = Field(pattern=r"^[a-f0-9]{12}$")
    cache_key: str                         # from preview-backstory response
    confidence: float = Field(ge=0.0, le=1.0)

class PhoneExtraction(BaseModel):
    """Call this when the user has chosen voice or text, and (if voice) given a phone."""
    phone_preference: Literal["voice", "text"]
    phone: Optional[str] = Field(default=None)  # E.164 if voice
    confidence: float = Field(ge=0.0, le=1.0)
```

Agent uses Claude tool-use: calls the appropriate tool when extraction is possible; omits tool calls on off-topic or backtracking turns.

### 2.3 Endpoint: `POST /portal/onboarding/converse`

**Path**: `nikita/api/routes/portal_onboarding.py` (extend existing router).

```python
class Turn(BaseModel):
    role: Literal["nikita", "user"]
    content: str
    extracted: Optional[dict] = None
    timestamp: datetime
    source: Optional[Literal["llm", "fallback"]] = None

class ConverseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")  # rogue user_id rejected 422 (resolves #350, AC-11d.3)
    conversation_history: list[Turn]
    user_input: Union[str, ControlSelection]  # str for text input, ControlSelection for chip/slider
    locale: Literal["en"] = "en"
    turn_id: UUID | None = None  # (#352) idempotency-key; client-generated UUIDv4 per turn

class ConverseResponse(BaseModel):
    nikita_reply: str = Field(max_length=500)           # server validator enforces <=140 in practice
    extracted_fields: dict                               # Partial<OnboardingProfile>
    confirmation_required: bool
    next_prompt_type: Literal["text", "chips", "slider", "toggle", "cards", "none"]
    next_prompt_options: Optional[list[str]] = None
    progress_pct: int = Field(ge=0, le=100)
    conversation_complete: bool
    source: Literal["llm", "fallback"]
    latency_ms: int

@router.post("/onboarding/converse")
async def converse(
    req: ConverseRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_authenticated_user)],  # Bearer JWT — identity derived here, not from body (#350)
    conversation_agent: Annotated[Agent, Depends(get_conversation_agent)],
    converse_rate_limiter: Annotated[RateLimiter, Depends(get_converse_rate_limiter)],  # dedicated bucket (#353)
    ip_rate_limiter: Annotated[RateLimiter, Depends(get_converse_ip_rate_limiter)],  # per-IP bucket (#353)
    spend_ledger: Annotated[LLMSpendLedger, Depends(get_llm_spend_ledger)],  # daily cap (#353)
    idempotency: Annotated[IdempotencyStore, Depends(get_idempotency_store)],  # (#352)
) -> ConverseResponse:
    ...
```

**Behavior**:
1. Derive `user_id = current_user.id` from Bearer JWT. Body cannot carry `user_id` (Pydantic `extra="forbid"` rejects 422).
2. Idempotency short-circuit (resolves #352, AC-11d.3c): if `req.turn_id` present, query `idempotency.get((user_id, turn_id))`. Cache HIT → return cached response verbatim, skip rate-limit decrement, skip agent, skip JSONB write (M5).
3. Enforce rate limits (resolves #353): (a) per-user converse bucket 20/min via `converse_rate_limiter`; (b) per-IP bucket 30/min via `ip_rate_limiter` (IP from `X-Forwarded-For` per proxy-header config); (c) daily LLM spend cap `CONVERSE_DAILY_LLM_CAP_USD` (default $2.00) via `spend_ledger.get_today(user_id)`. Any breach → return 429 per AC-11d.9 (in-character bubble + `Retry-After: 30`).
4. Tool-call edge-case handling (resolves #351, S5): after the agent invocation returns, validate the tool-call set: (a) **zero tool calls** → treat as off-topic per AC-11d.6 (re-prompt for current field); (b) **≥2 tool calls** → process only the first by priority order `[extract_profile_field, confirm_profile_field, correct_profile_field, request_clarification]`; log `converse_multi_toolcall_warn`; (c) **required field `None`** → reject extraction (low-confidence), set `confirmation_required=true`; (d) **field-format violation** (e.g. `age` non-int, `location_cache_key` fails regex `^[a-z0-9_\-]{1,64}$`) → reject extraction and return fallback per AC-11d.9. Authz gate on tool-call JSONB-path arguments (resolves #350, AC-11d.3b): any tool argument resolving to `onboarding_profile` of a user_id ≠ `current_user.id` → 403 generic body + log `converse_authz_mismatch`.
5. Build agent input from `conversation_history` + `user_input`.
6. Call `await asyncio.wait_for(conversation_agent.run(...), timeout=2.5)`.
7. Validate agent output (regex + length + PII-concat reject per validation rules).
8. On success: persist turn via ORM per-user-serialized pattern (resolves #352, AC-NR1b.1b, S8):
   ```python
   async with session.begin():
       stmt = select(User).where(User.id == user_id).with_for_update()
       user = (await session.execute(stmt)).scalar_one()
       profile = dict(user.onboarding_profile or {})  # defensive copy
       profile.setdefault("conversation", []).append(new_turn)
       user.onboarding_profile = profile  # dirty-tracking via MutableDict.as_mutable
       # commit on context exit
   ```
   Avoid raw `jsonb_set` — PR #317 (double-encoded JSONB) and PR #319 (TEXT[] path land-mine) establish ORM-round-trip as the safe path. Return response with `source="llm"`.
9. Store idempotency cache entry `(user_id, turn_id) → response` with 5-min TTL (resolves #352, AC-11d.3c).
10. On timeout/error/validation-reject: return hardcoded fallback with `source="fallback"`. Never raise 500 for agent issues.
11. Compute `progress_pct` based on extracted-fields coverage of required onboarding fields.
12. Set `conversation_complete=true` when all required fields are extracted AND confirmed.

**Idempotency handling** (resolves #352, AC-11d.3c):

The endpoint reads either the `Idempotency-Key` HTTP header or the `turn_id: UUID` field from `ConverseRequest` (already added via T1.2 Edit 1). Dedupe key = `(user_id, turn_id)`. A Postgres-backed 5-minute TTL cache (`llm_idempotency_cache` table — DDL in §4.3a) stores `response_body JSONB + status_code INT`. On HIT within 5 min, the cached response is returned verbatim; the agent is NOT called; JSONB is NOT re-written; the rate-limit bucket is NOT re-decremented; the LLM-spend ledger is NOT incremented (M5 idempotent HIT). On MISS, the call proceeds and the response is cached at the end via `INSERT ... ON CONFLICT (user_id, turn_id) DO NOTHING RETURNING body`. TTL enforcement via pg_cron job `llm_idempotency_cache_prune` hourly.

**Validation rules** (server-side):

| Check | Reject condition | Action |
|---|---|---|
| Input strip (#351) | `user_input` contains `<`, `>`, or null byte | Strip silently before agent call |
| Input jailbreak (#351) | `user_input` matches any pattern in `jailbreak_patterns.yaml` (20+) | Return 200 + hardcoded fallback; log `converse_input_reject` |
| Input length (#351) | `len(user_input) > ONBOARDING_INPUT_MAX_CHARS` (500) | Return 200 + fallback reply |
| Tool-call count (#351, S5) | 0 tool calls emitted | Treat as off-topic; reprompt current field |
| Tool-call count (#351, S5) | ≥2 tool calls emitted | Process first by priority order; log `converse_multi_toolcall_warn` |
| Tool field required (#351, S5) | required field = `None` | Reject extraction; set `confirmation_required=true` |
| Tool field format (#351, S5) | `age` non-int / `phone` non-E.164 / `location_cache_key` fails `^[a-z0-9_\-]{1,64}$` | Reject extraction; return fallback |
| Length | `nikita_reply > NIKITA_REPLY_MAX_CHARS` (140) | Return fallback |
| Markdown | `nikita_reply contains [*_#\`]` | Return fallback |
| Quotes | `nikita_reply contains [\"\']` | Return fallback |
| PII concat | `nikita_reply contains (name AND age AND occupation) concatenated` | Return fallback |
| Output leak (#351) | `nikita_reply` contains first 32 chars of `WIZARD_SYSTEM_PROMPT` or `NIKITA_PERSONA` | Return fallback; log `converse_output_leak` |
| Tone filter (#351, S3) | `nikita_reply` contains any `ONBOARDING_FORBIDDEN_PHRASES` entry | Return fallback; log `converse_tone_reject` |
| Confidence | `confidence < CONFIDENCE_CONFIRMATION_THRESHOLD` (0.85) | Set `confirmation_required=true` |
| Age (#351, server-enforced) | `age < MIN_USER_AGE` (18) | Reject extraction; agent in-character rejection; do not advance field |
| Phone (#351, server-enforced) | `phone` fails E.164 parse | Reject extraction; agent in-character rejection |
| Country (#351, server-enforced) | `phone` country not in supported list | Reject extraction; agent suggests text path |

### 2.4 Handoff greeting generator

**Path**: `nikita/agents/onboarding/handoff_greeting.py` (new; extends `FirstMessageGenerator` from Spec 213 PR 213-5).

```python
async def generate_handoff_greeting(
    user_id: UUID,
    trigger: Literal["handoff_bind", "first_user_message"],
    *,
    user_repo: UserRepository,
    backstory_repo: BackstoryRepository,
    memory: SupabaseMemory,
) -> str:
    """
    Produce a Nikita-voiced greeting referencing onboarded data.
    trigger="handoff_bind" fires immediately on /start <code> success.
    trigger="first_user_message" preserves pre-FR-11e Spec 213 behavior for legacy users.
    """
```

Both triggers use the same agent + persona; only the prompt framing differs ("they just tapped the CTA" vs "they just sent their first message").

### 2.5 `_handle_start_with_payload` extension (FR-11e, resolves #352)

`nikita/platforms/telegram/commands.py::_handle_start_with_payload` gains a `background_tasks: BackgroundTasks` parameter (plumbed down from the telegram webhook route at `nikita/api/routes/telegram.py:508`, which already declares it). Sequence:

1. **Atomic bind** (unchanged from PR #322): consume Telegram-link code + write `telegram_id`.
2. **Claim one-shot intent** (NOT clear flag — resolves B1):
   ```sql
   UPDATE users SET handoff_greeting_dispatched_at = now()
    WHERE id = :uid
      AND handoff_greeting_dispatched_at IS NULL
      AND pending_handoff = TRUE
    RETURNING id;
   ```
   Proceed to step 3 only if `rowcount == 1`. Second concurrent `/start <code>` sees rowcount==0 and skips greeting.
3. **Webhook returns 200 first** (AC-11e.3b). BackgroundTasks run after the HTTP response commits.
4. **Dispatch greeting via `BackgroundTasks.add_task`**:
   ```python
   async def _dispatch_greeting_with_retry(user_id: UUID) -> None:
       backoff = [0.5, 1.0, 2.0]
       for attempt, delay in enumerate(backoff, start=1):
           try:
               greeting = await generate_handoff_greeting(user_id, trigger="handoff_bind", ...)
               await bot.send_message(chat_id=..., text=greeting)
               # Confirmed delivery → clear pending_handoff
               await user_repo.clear_pending_handoff(user_id)
               return
           except TelegramServerError:  # 5xx
               if attempt < len(backoff):
                   await asyncio.sleep(delay)
                   continue
       # Retries exhausted: reset dispatched_at so pg_cron backstop picks it up
       await user_repo.reset_handoff_dispatch(user_id)
       logger.error("handoff_greeting_retry_exhausted", user_id=str(user_id))

   background_tasks.add_task(_dispatch_greeting_with_retry, user.id)
   ```
5. **pg_cron backstop** (resolves B1): new job `nikita_handoff_greeting_backstop` every 60s calls `POST /api/v1/tasks/retry-handoff-greetings` (Bearer auth via `TASK_AUTH_SECRET`). The endpoint re-dispatches greetings for stranded rows `WHERE pending_handoff = TRUE AND telegram_id IS NOT NULL AND (handoff_greeting_dispatched_at IS NULL OR handoff_greeting_dispatched_at < now() - interval '30 seconds')`.
6. **Stranded-user one-shot migration** (resolves B6, AC-11e.3c): `scripts/handoff_stranded_migration.py` executed once post-deploy.
7. **Idempotency of `/start <code>`** preserved: repeated `/start <code>` from same user hits rowcount==0 in step 2 and renders welcome-back (AC-11e.6); no second greeting.

> **Convention note** (resolves B5): background dispatch in FastAPI routes MUST use `BackgroundTasks` (the convention established by `nikita/api/routes/portal_onboarding.py:247` and `nikita/api/routes/telegram.py:508`). `asyncio.create_task` is reserved for non-FastAPI contexts (e.g. `nikita/onboarding/handoff.py::FirstMessageGenerator` which is called from a voice-call completion path, not an HTTP request). New FR-11e code adheres to `BackgroundTasks`.

### 2.6 `/portal/link-telegram` mint timing (resolves S9, FR-11b)

The one-time Telegram-link code is MINTED inside the reducer's `COMPLETE` transition handler, BEFORE `ClearanceGrantedCeremony` paints. Previously (pre-wizard) the mint happened on `HandoffStep` mount; since HandoffStep is retired in FR-11c Phase A, the mint moves into the reducer. Concretely, the reducer's case for `type: "server_response"` with `conversation_complete=true` calls `POST /portal/link-telegram` and stores `{ code, expiresAt }` in state BEFORE dispatching the transition to CEREMONY. `ClearanceGrantedCeremony` reads `code` from reducer state (never initiates the mint itself; the ceremony is pure presentation). Test: on the final confirm turn, assert POST /portal/link-telegram is called exactly once before `ClearanceGrantedCeremony` paints; subsequent mounts of the ceremony do not re-mint.

## 3. Portal: component tree

### 3.1 New components

**Path**: `portal/src/app/onboarding/components/`

| Component | Purpose |
|---|---|
| `ChatShell.tsx` | Message thread container; scroll region; input form at bottom |
| `MessageBubble.tsx` | Left-aligned Nikita / right-aligned user; typewriter reveal on Nikita turns |
| `TypingIndicator.tsx` | Pulsing-dots animation rendered before Nikita speaks |
| `InlineControl.tsx` | Slim dispatcher (~30 LOC, resolves #355): reads `next_prompt_type` from a `controls/` registry and renders one of `TextControl`, `ChipsControl`, `SliderControl`, `ToggleControl`, `CardsControl`. No inline switch/if-else tree. |
| `controls/TextControl.tsx` | Text input; replaces inline text branch. |
| `controls/ChipsControl.tsx` | Chip grid; replaces inline chips branch. |
| `controls/SliderControl.tsx` | 1-5 segmented button row; replaces both the inline slider branch AND (deferred to Phase D) the retired `edginess-slider` step component. |
| `controls/ToggleControl.tsx` | 2-option switch; replaces inline toggle branch. |
| `controls/CardsControl.tsx` | Card picker; replaces both the inline cards branch AND (deferred to Phase D) the retired `scene-selector` step component. `DossierStamp` remains mounted inside `ClearanceGrantedCeremony`. |
| **Legacy form-wizard step components** (resolves S1) | During Phase A (FR-11c ship), legacy step components (`EdginessSliderStep.tsx`, `SceneSelectorStep.tsx`, `DossierRevealStep.tsx`, `HandoffStep.tsx`, and any other pre-wizard step files) MUST be MOVED (not deleted) to `portal/src/app/onboarding/steps/legacy/` behind feature flag `USE_LEGACY_FORM_WIZARD` (env var + portal Settings surface). Deletion deferred to Phase D (PR 5, minimum 7 days after PR 3 production ship AND after AC-11d.13c gate PASS). |
| `ProgressHeader.tsx` | Top bar + label "Building your file... N%" |
| `ConfirmationButtons.tsx` | `[Yes] [Fix that]` inline below Nikita's echo when `confirmation_required=true` |
| `ClearanceGrantedCeremony.tsx` | Full-viewport FR-11e closeout: stamp animation + final line + CTA + QR |

### 3.2 Hooks

| Hook | Purpose |
|---|---|
| `useConversationState.ts` | State machine replacing `WizardStateMachine.ts`: holds turn array, extracted fields, confirmation-pending flag, completion flag |
| `useOnboardingAPI.ts::converse()` | New method; POST `/portal/onboarding/converse` (no retry wrapper; non-idempotent) |
| `useOptimisticTypewriter.ts` | Drives typewriter reveal + typing indicator timing |

### 3.3 Wizard rewrite

**Path**: `portal/src/app/onboarding/onboarding-wizard.tsx` (rewrite).

Old shape: hardcoded step switch (3→11) rendering LocationStep / SceneStep / etc.
New shape: single `ChatShell` container driven by `useConversationState`. On `conversation_complete=true`, mount `ClearanceGrantedCeremony`.

Retired step components (LocationStep, SceneStep, DarknessStep, IdentityStep, BackstoryReveal, PhoneStep): DELETED. Keep PipelineGate (step 10 theatrical); it sits between conversation-complete and ceremony, unchanged. Keep HandoffStep (refactored to render ClearanceGrantedCeremony).

### 3.4 Accessibility

- `ChatShell` uses `role="log"` + `aria-live="polite"`.
- `MessageBubble` has `aria-label` per turn with role + content.
- Input field has visible `<label>`.
- Controls have visible focus rings.
- Keyboard nav: Tab cycles input → send → inline controls → progress bar.
- `prefers-reduced-motion` disables typewriter reveal and stamp animation.

## 4. Data model changes

### 4.1 `users.onboarding_profile` JSONB

Existing shape (Spec 214 PR-D, shipped 2026-04-16):

```json
{
  "wizard_step": 8,
  "location_city": "Zurich",
  "social_scene": "techno",
  "life_stage": "tech",
  "drug_tolerance": 3,
  "name": "Simon",
  "age": 30,
  "occupation": "engineer",
  "phone": "+41791234567",
  "chosen_option_id": "abc123def456",
  "cache_key": "zurich|techno|3|tech|engineer|twenties|engineer"
}
```

Extended shape (FR-11d, additive; no schema migration required):

```json
{
  "...all existing fields above...": "...",
  "conversation": [
    {"role": "nikita", "content": "Hey. Building your file. Where do I find you on a Thursday night?", "timestamp": "2026-04-19T14:00:00Z", "source": "llm"},
    {"role": "user", "content": "Zurich", "extracted": {"location_city": "Zurich"}, "timestamp": "2026-04-19T14:00:12Z"},
    {"role": "nikita", "content": "Zurich. I know some places there. Right?", "timestamp": "2026-04-19T14:00:14Z", "source": "llm"}
  ]
}
```

No DDL migration for `onboarding_profile.conversation` itself (subfield of existing JSONB). PATCH `/portal/onboarding/profile` endpoint already accepts arbitrary JSONB keys (Spec 213 contract).

**RLS inheritance** (resolves #354): `onboarding_profile.conversation` inherits `users` table RLS policies (user-scoped: `USING (id = (SELECT auth.uid()))`). No separate policy needed because JSONB subfields share the row-level gate.

**90-day pg_cron retention** (resolves #354, AC-NR1b.4b): new pg_cron job `onboarding_conversation_nullify_90d` runs daily at 03:00 UTC:

```sql
SELECT cron.schedule(
  'onboarding_conversation_nullify_90d',
  '0 3 * * *',
  $$
  UPDATE users
     SET onboarding_profile = onboarding_profile - 'conversation'
   WHERE onboarding_status = 'completed'
     AND (onboarding_profile->>'completed_at')::timestamptz < now() - interval '90 days'
     AND onboarding_profile ? 'conversation';
  $$
);
```

Structured fields (`name`, `age`, `occupation`, `location_city`, etc.) remain; only the `conversation` key is dropped.

### 4.2 `users.pending_handoff` flag semantic change (FR-11e, resolves B1)

Pre-FR-11e: cleared in `message_handler` on first user message.
Post-FR-11e: NOT cleared until the proactive greeting is CONFIRMED delivered (see §2.5). New column `handoff_greeting_dispatched_at TIMESTAMPTZ NULL` added to `users` (claim-intent marker).

Migration DDL:
```sql
ALTER TABLE users ADD COLUMN handoff_greeting_dispatched_at TIMESTAMPTZ NULL;
CREATE INDEX idx_users_handoff_backstop
  ON users (handoff_greeting_dispatched_at)
  WHERE pending_handoff = TRUE AND telegram_id IS NOT NULL;
```

Backward compat: rows existing pre-migration get `handoff_greeting_dispatched_at=NULL`; handled by AC-11e.3c one-shot stranded migration (`scripts/handoff_stranded_migration.py`).

### 4.3 Legacy data disposition (resolves #354, M6)

`user_onboarding_state` table dropped in a follow-up migration after a 30-day quiet period per §8.1 PR 5. Pre-drop checklist:

1. FK-audit query:
   ```sql
   SELECT tc.table_name, kcu.column_name
     FROM information_schema.table_constraints AS tc
     JOIN information_schema.key_column_usage AS kcu
       ON tc.constraint_name = kcu.constraint_name
    WHERE tc.constraint_type = 'FOREIGN KEY'
      AND kcu.referenced_table_name = 'user_onboarding_state';
   ```
   MUST return zero rows.
2. In-flight rows (< 15 per 2026-04-19 snapshot): abandoned at cutover. Count documented in migration PR description.
3. Migration file `migrations/YYYYMMDD_drop_user_onboarding_state.sql` reserved; runs `DROP TABLE IF EXISTS user_onboarding_state CASCADE;`. Non-reversible.
4. **GDPR coupling during quiet period** (resolves M6): the account-delete path in `nikita/db/repos/user_repo.py::delete_user` MUST also delete any rows in `user_onboarding_state` for the target user_id between PR 3 ship and PR 5 drop. Test: insert a `user_onboarding_state` row, call `delete_user`, assert row removed.

### 4.3a `llm_idempotency_cache` (new, resolves #352 AC-11d.3c)

```sql
CREATE TABLE llm_idempotency_cache (
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  turn_id UUID NOT NULL,
  response_body JSONB NOT NULL,
  status_code INT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, turn_id)
);
CREATE INDEX idx_llm_idempotency_cache_created ON llm_idempotency_cache (created_at);
ALTER TABLE llm_idempotency_cache ENABLE ROW LEVEL SECURITY;
CREATE POLICY "admin_and_service_role_only"
  ON llm_idempotency_cache FOR ALL
  USING (is_admin() OR auth.role() = 'service_role')
  WITH CHECK (is_admin() OR auth.role() = 'service_role');

-- Prune >5 minutes old hourly
SELECT cron.schedule('llm_idempotency_cache_prune', '0 * * * *', $$
  DELETE FROM llm_idempotency_cache WHERE created_at < now() - interval '5 minutes';
$$);
```

### 4.3b `llm_spend_ledger` (new, resolves #353 AC-11d.3d, S6)

```sql
CREATE TABLE llm_spend_ledger (
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  day DATE NOT NULL,
  spend_usd NUMERIC(10,4) NOT NULL DEFAULT 0,
  last_updated TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, day)
);
CREATE INDEX idx_llm_spend_ledger_day ON llm_spend_ledger (day);
ALTER TABLE llm_spend_ledger ENABLE ROW LEVEL SECURITY;
CREATE POLICY "admin_and_service_role_only"
  ON llm_spend_ledger FOR ALL
  USING (is_admin() OR auth.role() = 'service_role')
  WITH CHECK (is_admin() OR auth.role() = 'service_role');

-- Daily rollover (archive/prune old rows) at 00:05 UTC
SELECT cron.schedule('llm_spend_ledger_rollover', '5 0 * * *', $$
  DELETE FROM llm_spend_ledger WHERE day < current_date - interval '30 days';
$$);
```

## 5. State machine replacement

### 5.1 `WizardStateMachine.ts` (retire)

Old: enforced step transitions (3→4→5→…→11) with canTransition() guard. Retired alongside step components.

### 5.2 `useConversationState.ts` (new)

```typescript
type ConversationState = {
  turns: Turn[]
  extractedFields: Partial<OnboardingProfile>
  progressPct: number
  awaitingConfirmation: boolean
  currentPromptType: "text" | "chips" | "slider" | "toggle" | "cards" | "none"
  currentPromptOptions?: string[]
  isComplete: boolean
  isLoading: boolean  // true while awaiting /converse response
  lastError: string | null
}

type ConversationAction =
  | { type: "hydrate"; turns: Turn[]; extractedFields: Partial<OnboardingProfile>; progressPct: number; awaitingConfirmation: boolean }  // (#355) fired in useEffect, NOT render; StrictMode-guarded at 50ms
  | { type: "user_input"; input: string | ControlSelection }
  | { type: "server_response"; response: ConverseResponse }
  | { type: "server_error"; error: string }
  | { type: "timeout" }              // (#355) renders `source="fallback"` bubble
  | { type: "retry" }                // (#355) 429 / transient-error retry path
  | { type: "truncate_oldest" }      // (#355, NR1b.5) elide oldest turn while preserving extracted fields
  | { type: "confirm" }
  | { type: "reject_confirmation" }
  | { type: "clearPendingControl" }  // (#355, M2) REJECTED state clears stale pre-filled control
```

Reducer handles optimistic UI (pushes user's turn immediately; pushes Nikita's turn on server response). On `conversation_complete=true`, sets `isComplete=true` and the parent renders `ClearanceGrantedCeremony`.

## 6. Phase A technical details (FR-11c)

### 6.1 `_handle_start` rewrite

Replace current vanilla-payload branch (commands.py ~lines 160-227) with:

```python
user = await self.user_repository.get_by_telegram_id(telegram_id)

if user is None:
    return await self._send_portal_auth_link(chat_id, first_name)  # E1

if self.profile_repository is None:
    raise RuntimeError("profile_repository required post-FR-11c")  # AC-11c.9

has_profile = (await self.profile_repository.get(user.id)) is not None
fully_onboarded = user.onboarding_status == "completed" and has_profile

if fully_onboarded and user.game_status not in ("game_over", "won"):
    return await self.bot.send_message(chat_id=chat_id, text=WELCOME_BACK_COPY)  # E2/E8

if fully_onboarded and user.game_status in ("game_over", "won"):
    await self.user_repository.reset_game_state(user.id)
    return await self._send_bridge(user.id, chat_id, reason="re-onboard")  # E3/E4

return await self._send_bridge(user.id, chat_id, reason="resume")  # E5/E6
```

Helper `_send_bridge` uses `generate_portal_bridge_url` + `bot.send_message_with_keyboard` (inline URL button pattern from existing `_handle_onboard`).

**Bridge-token contract** (resolves #354, AC-11c.12): `generate_portal_bridge_url(user_id, reason)` MUST mint a single-use JWT or opaque DB-backed token with TTL per `reason`: 24h for `reason="resume"`, 1h for `reason="re-onboard"`. Token invalidated on password-reset (trigger: `auth.users` password-change webhook or RLS revocation row). Expired/revoked → portal `/onboarding/auth` with expiry-nudge copy (AC-11c.12). E1 (unknown user) path mints NO token; URL is bare `{portal_url}/onboarding/auth`.

### 6.2 `message_handler` early gate

Before Q&A consumption path:

```python
if user is None:
    return await self._send_portal_nudge(chat_id, reason="unknown_user")  # E1/E9

if EMAIL_REGEX.match(text):
    return await self._send_portal_nudge(chat_id, reason="email")  # E10

if user.onboarding_status != "completed" or not has_profile:
    return await self._send_portal_nudge(chat_id, reason="unonboarded")  # E9

# ... fall through to existing chat pipeline
```

### 6.3 Deletions

- `nikita/platforms/telegram/onboarding/` package (handler.py:1-1162).
- `OnboardingStateRepository` imports / DI wiring in telegram layer.
- `onboarding_handler` constructor param on `message_handler`.
- `TelegramAuth`: audit callers; if only Q&A-coupled, delete.
- Tests: `tests/platforms/telegram/onboarding/` directory.

## 7. Testing strategy

### 7.1 Backend

| Test file | Coverage |
|---|---|
| `tests/platforms/telegram/test_commands.py` | E1-E10 edge cases + DI guard (11 new cases for FR-11c) |
| `tests/platforms/telegram/test_message_handler.py` | E9 pre-onboard text nudge, E10 email nudge |
| `tests/agents/onboarding/test_conversation_agent.py` | Persona snapshot, 20 fixture extractions, confidence <0.85 triggers confirmation, off-topic handling, backtracking, in-character validation (age <18, invalid phone), falsifiable persona-drift metric (TF-IDF cosine ≥0.70 + mean-sentence-length / lowercase-ratio / canonical-phrase-count within ±15%; baseline CSV `tests/fixtures/persona_baseline_v1.csv`; ADR `specs/214-portal-onboarding-wizard/decisions/ADR-001-persona-drift-baseline.md`; resolves #356, M1), onboarding-tone filter (20-fixture Gemini-judged, resolves S3) |
| `tests/api/routes/test_converse_endpoint.py` | Happy path with mocked agent, timeout fallback, validator rejects (>140 chars, markdown, quotes, PII concat), rate limit 429, authz 403 |
| `tests/agents/onboarding/test_handoff_greeting.py` | Persona snapshot, references name/city/backstory, idempotent (one-shot) |
| `tests/platforms/telegram/test_commands.py::TestHandleStartWithPayload` | Extended: proactive greeting fires on bind, `pending_handoff` cleared atomically |
| `tests/db/integration/test_onboarding_profile_conversation.py` | JSONB conversation subfield persists across turns; v1→v2 migration shim |

### 7.2 Portal

| Test file | Coverage |
|---|---|
| `portal/src/app/onboarding/__tests__/ChatShell.test.tsx` | Message thread renders, scrolls to latest, typing indicator visible |
| `portal/src/app/onboarding/__tests__/MessageBubble.test.tsx` | Typewriter reveal timing, role-based alignment, reduced-motion fallback |
| `portal/src/app/onboarding/__tests__/InlineControl.test.tsx` | All 5 control types render; both typed + tapped paths commit equivalently |
| `portal/src/app/onboarding/__tests__/ProgressHeader.test.tsx` | Bar width maps to progress_pct; label format |
| `portal/src/app/onboarding/__tests__/ClearanceGrantedCeremony.test.tsx` | Stamp animation, CTA href, QR on desktop |
| `portal/src/app/onboarding/__tests__/onboarding-wizard.test.tsx` | Rewritten: drives chat flow, confirmation loop, completion triggers ceremony |
| `portal/src/app/onboarding/hooks/__tests__/useConversationState.test.ts` | Reducer actions, optimistic UI, confirmation flow |
| `portal/src/app/onboarding/hooks/__tests__/useOnboardingAPI.test.ts` | `converse()` method (extend existing file) |

### 7.3 E2E (Playwright)

Rewritten `tests/e2e/portal/test_onboarding.spec.ts`:

1. Fresh incognito → `/onboarding/auth` → submit email.
2. Follow magic link → lands on `/onboarding` with chat UI.
3. Assert Nikita's opening bubble + input field + progress bar at 0%.
4. Type "Zurich" → send → assert agent reply within 3s + progress bar advances.
5. Confirmation loop: assert `[Yes] [Fix that]` render + `Yes` advances.
6. Scene chip grid: tap chip → progress advances.
7. Darkness slider: pick 3 → advances.
8. Identity free-text → advances.
9. Backstory card picker → advances.
10. Phone toggle → advances.
11. Assert `ClearanceGrantedCeremony` renders + CTA href matches `t.me/Nikita_my_bot?start=[A-Z0-9]{6}$`.

Content assertions check DOM structure + bubble count, not content strings (LLM-variable).

**@edge-case tagged sub-suite** (resolves #356, AC-11d.13b): 4 additional Playwright walks at `tests/e2e/portal/test_onboarding.spec.ts` tagged `@edge-case`: Fix-that ghost-turn; 2500ms timeout fallback (asserts `data-source="fallback"` on bubble DOM); backtracking "change my city to Berlin" (later fields survive); age<18 in-character rejection (no red banner, control re-renders pre-filled). Run via `playwright test --grep @edge-case`.

### 7.4 Live dogfood

- Preview-env smoke pre-merge each PR (PR 1 Telegram-only, PR 2 backend-only curl, PR 3 agent-browser chat, PR 4 Telegram-MCP greeting timing).
- Prod dogfood (user-side): fresh incognito chat walk → ceremony → tap CTA → Nikita greeting arrives within 5s referencing name. Send Telegram `/start` from a SECOND account to verify FR-11c unchanged redirect behavior.

### 7.5 Pre-PR Gates (resolves #356)

Before dispatching `/qa-review` on any FR-11c / FR-11d / FR-11e PR, run the three grep gates from `.claude/rules/testing.md` against the changed files. Gates MUST return empty:

1. Zero-assertion test-shell gate — `rg -U "async def test_[^(]+\([^)]*\):[\s\S]*?(?=\nasync def|\nclass |\Z)" tests/ | rg -L "assert|pytest\.raises"`
2. PII-in-logs gate — `rg -nE "logger\.(info|warning|error|exception|debug).*%s.*(name|age|occupation|phone)" <changed .py files>`
3. Raw `cache_key` gate — `rg -n "cache_key=" <changed .py files> | rg -v "cache_key_hash|sha256"`

**Reply-cache key** (resolves §10.2 open question): `/converse` reply cache keys on `sha256(extracted_field_json_canonical || user_input_normalized)`. Raw `cache_key` string MUST NOT appear in logs — only SHA-256 hex. Binds open question §10.2.

## 8. Rollout & rollback

**Feature flag** (resolves S1): `USE_LEGACY_FORM_WIZARD` (env var + portal Settings). Default `false` in production after PR 3 ships; `true` reserved for break-glass rollback. Legacy step components live in `portal/src/app/onboarding/steps/legacy/` until Phase D (PR 5) deletes them.

### 8.1 Phases

- **Phase A** (PR 3 — FR-11c + FR-11d + FR-11e chat wizard): ship chat wizard + new `/converse` endpoint + handoff greeting. `USE_LEGACY_FORM_WIZARD=false`. Legacy step components MOVED to `portal/src/app/onboarding/steps/legacy/` (NOT deleted).
- **Phase B** (PR 4 — post-deploy measurement): run `scripts/converse_source_rate_measurement.py` for N=100 turns; PASS if `source="llm"` rate ≥90% (resolves AC-11d.9 / S2). On FAIL, escalate to SSE before proceeding.
- **Phase C** (≥7 days post-Phase A): measure chat-wizard completion rate at N=50 (AC-11d.13c / S4). PASS if within ±5pp of form-wizard baseline. On FAIL, block Phase D.
- **Phase D** (PR 5 — legacy delete): delete `portal/src/app/onboarding/steps/legacy/` AND drop `user_onboarding_state` table via `migrations/YYYYMMDD_drop_user_onboarding_state.sql`. Requires Phase B + Phase C PASS + ≥30-day quiet period.

Rollback path: flip `USE_LEGACY_FORM_WIZARD=true` at portal layer, revert the `/converse` endpoint feature gate in `nikita/api/routes/portal_onboarding.py` (disable `/converse` route). Legacy components + table remain intact until Phase D.

### 8.1a Ship sequence (per-PR details)

- PR 1 `fix/spec-214-fr11c-telegram-to-portal`: Phase A only. Regression-class. Hours scope. Ship first to close the user's immediate Q&A complaint.
- PR 2 `feat/spec-214-fr11d-conversation-agent-backend`: agent + endpoint + schemas + snapshot tests. Backend-only. Portal still uses old form wizard at this point.
- PR 3 `feat/spec-214-fr11d-chat-wizard-frontend`: portal chat UI consumes backend endpoint from PR 2. Old step components retired. Users see chat wizard for the first time.
- PR 4 `feat/spec-214-fr11e-ceremonial-handoff`: portal closeout + Telegram proactive greeting. Polish layer.
- PR 5 optional `chore/spec-214-onboarding-legacy-cleanup`: drop `user_onboarding_state` table after 30-day quiet period; remove `TelegramAuth` if fully unused.

### 8.2 Rollback

- PR 1 rollback: revert commit; bot re-enters legacy Q&A flow (regression, but functional).
- PR 2 rollback: endpoint returns 404; portal PR 3 handles 404 with fallback copy.
- PR 3 rollback: revert restores the form wizard; backend endpoint from PR 2 stays but is unreachable.
- PR 4 rollback: revert clears the `pending_handoff` flag semantic change; first-user-message behavior returns.

Each PR is independently revertable.

## 9. Non-goals (explicit)

- Full free-form chat-first UX without structured controls. Research-backed winner is hybrid; pure chat is OUT.
- Pre-generating branching conversation trees. Agent-per-turn is chosen.
- Voice-input wizard. Text only for this phase.
- Multi-language. English only.
- Admin dashboard for conversation completion funnel. Add when ≥1k users.
- Real-time Telegram↔portal mirror. Portal dashboard remains historical-only.

## 10. Open technical questions (to resolve in `/plan`)

1. **Agent streaming**: should the `POST /converse` endpoint stream chunked responses (SSE or chunked transfer) so the portal can start revealing Nikita's message early? Non-blocking already, but streaming could feel even snappier. Decision owner: `/plan`.
2. **Caching reactions** [RESOLVED 2026-04-19 via GH #356]: reply cache key = `sha256(extracted_field_json_canonical || user_input_normalized)`. Only SHA-256 hex ever in logs; raw key never emitted. TTL = 1 hour (conservative). Expected hit rate ~30%.
3. **Conversation size cap**: 100 turns max (per AC-NR1b.5). Hard failure mode if exceeded? Truncate oldest? Spec says elide oldest + preserve extracted fields. Confirm elision semantics in `/plan`.
4. **Handoff greeting fallback**: if `FirstMessageGenerator` fails on the bind path, should the bot send a minimal welcome (`"Hey, welcome."`) or delay greeting to first-user-message (degrade to legacy)? Recommend: minimal welcome + log error. Confirm in `/plan`.
5. **Rate limit quota** [RESOLVED 2026-04-19 via GH #353]: `/converse` and `/preview-backstory` have SEPARATE per-user buckets. `/converse` per-user bucket = `CONVERSE_PER_USER_RPM` (20). `/preview-backstory` bucket = 10 (unchanged). Per-IP secondary on `/converse` = `CONVERSE_PER_IP_RPM` (30). Per-user daily LLM spend cap = `CONVERSE_DAILY_LLM_CAP_USD` ($2.00). All constants in `nikita/onboarding/tuning.py` as `Final[int|float]` with rationale comments per `.claude/rules/tuning-constants.md` (resolves M7). Implementation via new `get_converse_rate_limiter`, `get_converse_ip_rate_limiter`, `get_llm_spend_ledger` DI providers.

**Tuning constants summary** (resolves M7, all in `nikita/onboarding/tuning.py`):

| Constant | Value | Rationale |
|---|---|---|
| `ONBOARDING_INPUT_MAX_CHARS` | 500 | Longer inputs are always prompt-injection; 500 covers verbose genuine answers. |
| `NIKITA_REPLY_MAX_CHARS` | 140 | Keeps bubble terse + consistent with persona. |
| `CONVERSE_PER_USER_RPM` | 20 | 15-turn wizard with headroom. |
| `CONVERSE_PER_IP_RPM` | 30 | Covers NAT at university / cafe. |
| `CONVERSE_DAILY_LLM_CAP_USD` | 2.00 | Cost cap; 200 turns × $0.01/turn. |
| `CONVERSE_TIMEOUT_MS` | 2500 | Median p99 at <2s; 2500 is the hard ceiling. |
| `CONVERSE_429_RETRY_AFTER_SEC` | 30 | Gentle backoff matches user typing cadence. |
| `CONFIDENCE_CONFIRMATION_THRESHOLD` | 0.85 | Below → trigger confirmation dialog. |
| `MIN_USER_AGE` | 18 | Legal floor (unchanged). |
| `STRICTMODE_GUARD_MS` | 50 | React StrictMode double-render dedup window (resolves M3). |
| `HANDOFF_GREETING_BACKSTOP_INTERVAL_SEC` | 60 | pg_cron cadence. |
| `HANDOFF_GREETING_STALE_AFTER_SEC` | 30 | How long to wait before backstop picks up a row. |
| `PERSONA_DRIFT_FEATURE_TOLERANCE` | 0.15 | ±15% per AC-11d.11. |
| `PERSONA_DRIFT_COSINE_MIN` | 0.70 | Minimum TF-IDF cosine. |
| `PERSONA_DRIFT_SEED_SAMPLES` | 20 | N per seed. |
| `LLM_SOURCE_RATE_GATE_N` | 100 | AC-11d.9 rollout gate sample size. |
| `LLM_SOURCE_RATE_GATE_MIN` | 0.90 | ≥90% `source="llm"` rate (resolves S2). |
| `CHAT_COMPLETION_RATE_TOLERANCE_PP` | 5 | ±5pp vs legacy form wizard (resolves S4). |
| `CHAT_COMPLETION_RATE_GATE_N` | 50 | AC-11d.13c rollout gate sample size. |

## 11. Cross-references

- Functional spec: `specs/214-portal-onboarding-wizard/spec.md` (FR-11c, FR-11d, FR-11e, NR-1b)
- Approved plan: `~/.claude/plans/quirky-floating-liskov.md` (research base + 12 UX citations + code intel synthesis)
- Prior shipped scope: FR-1 through FR-11b (PR-A/B/C/D + PR #322), unchanged
- Related specs: Spec 001 (main text agent, persona source), Spec 042 (pipeline), Spec 060 (prompt caching), Spec 213 (FirstMessageGenerator, backstory preview endpoint), Spec 214 PR-D (PUT chosen-option endpoint)
- Rules: `.claude/rules/testing.md`, `.claude/rules/pr-workflow.md`, `.claude/rules/parallel-agents.md`
- Diagram: `docs/diagrams/20260417-onboarding-journey-actual-vs-intended.md` (add FR-11c/d/e rows on ship)
