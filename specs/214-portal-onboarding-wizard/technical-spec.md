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
    user_id: UUID
    conversation_history: list[Turn]
    user_input: Union[str, ControlSelection]  # str for text input, ControlSelection for chip/slider
    locale: Literal["en"] = "en"

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
    current_user: UserDep,
    conversation_agent: Annotated[Agent, Depends(get_conversation_agent)],
    rate_limiter: Annotated[RateLimiter, Depends(get_preview_rate_limiter)],  # shared quota
) -> ConverseResponse:
    ...
```

**Behavior**:
1. Validate `req.user_id == current_user.id` (authz).
2. Enforce rate limit (shared `preview-backstory` group, 10/min/user).
3. Build agent input from `conversation_history` + `user_input`.
4. Call `await asyncio.wait_for(conversation_agent.run(...), timeout=2.5)`.
5. Validate agent output (regex + length + PII-concat reject per validation rules).
6. On success: persist turn to `users.onboarding_profile.conversation` JSONB + return response with `source="llm"`.
7. On timeout/error/validation-reject: return a hardcoded fallback reply for the current field with `source="fallback"`. Never raise 500 for agent issues.
8. Compute `progress_pct` based on extracted-fields coverage of required onboarding fields.
9. Set `conversation_complete=true` when all required fields are extracted AND confirmed.

**Validation rules** (server-side):

| Check | Reject condition | Action |
|---|---|---|
| Length | `nikita_reply > 140 chars` | Return fallback |
| Markdown | `nikita_reply contains [*_#\`]` | Return fallback |
| Quotes | `nikita_reply contains [\"\']` | Return fallback |
| PII concat | `nikita_reply contains (name AND age AND occupation) concatenated` | Return fallback |
| Confidence | `confidence < 0.85` | Set `confirmation_required=true` |
| Age | `age < 18` | Agent in-character rejection; do not advance field |
| Phone | `phone` fails E.164 parse | Agent in-character rejection |
| Country | `phone` country not in supported list | Agent suggests text path |

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

### 2.5 `_handle_start_with_payload` extension (FR-11e)

`nikita/platforms/telegram/commands.py::_handle_start_with_payload` gains:
- After atomic bind success, call `generate_handoff_greeting(trigger="handoff_bind")` and dispatch via `bot.send_message`.
- Clear `users.pending_handoff` in the same transaction (not on first-user-message as today).
- One-shot semantics: idempotent on repeated `/start <code>` (second call is a no-op; welcome-back renders).

## 3. Portal: component tree

### 3.1 New components

**Path**: `portal/src/app/onboarding/components/`

| Component | Purpose |
|---|---|
| `ChatShell.tsx` | Message thread container; scroll region; input form at bottom |
| `MessageBubble.tsx` | Left-aligned Nikita / right-aligned user; typewriter reveal on Nikita turns |
| `TypingIndicator.tsx` | Pulsing-dots animation rendered before Nikita speaks |
| `InlineControl.tsx` | Dispatcher: renders text input / chip grid / 1-5 slider / toggle / card picker based on `next_prompt_type` |
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

No DDL migration. PATCH `/portal/onboarding/profile` endpoint already accepts arbitrary JSONB keys (Spec 213 contract).

### 4.2 `users.pending_handoff` flag semantic change (FR-11e)

Pre-FR-11e: cleared in `message_handler` on first user message.
Post-FR-11e: cleared in `_handle_start_with_payload` on proactive-greeting send.

Backward compat: legacy users who onboarded pre-FR-11c but whose `pending_handoff` was already cleared by an earlier message are unaffected.

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
  | { type: "user_input"; input: string | ControlSelection }
  | { type: "server_response"; response: ConverseResponse }
  | { type: "server_error"; error: string }
  | { type: "confirm" }
  | { type: "reject_confirmation" }
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
| `tests/agents/onboarding/test_conversation_agent.py` | Persona snapshot, 20 fixture extractions, confidence <0.85 triggers confirmation, off-topic handling, backtracking, in-character validation (age <18, invalid phone) |
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

### 7.4 Live dogfood

- Preview-env smoke pre-merge each PR (PR 1 Telegram-only, PR 2 backend-only curl, PR 3 agent-browser chat, PR 4 Telegram-MCP greeting timing).
- Prod dogfood (user-side): fresh incognito chat walk → ceremony → tap CTA → Nikita greeting arrives within 5s referencing name. Send Telegram `/start` from a SECOND account to verify FR-11c unchanged redirect behavior.

## 8. Rollout & rollback

### 8.1 Ship sequence

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
2. **Caching reactions**: should common extractions (e.g., "Zurich" + scene=techno, extremely common) cache the agent reply for 7 days to reduce LLM calls? Expected hit rate: ~30%. Decision owner: `/plan`.
3. **Conversation size cap**: 100 turns max (per AC-NR1b.5). Hard failure mode if exceeded? Truncate oldest? Spec says elide oldest + preserve extracted fields. Confirm elision semantics in `/plan`.
4. **Handoff greeting fallback**: if `FirstMessageGenerator` fails on the bind path, should the bot send a minimal welcome (`"Hey, welcome."`) or delay greeting to first-user-message (degrade to legacy)? Recommend: minimal welcome + log error. Confirm in `/plan`.
5. **Rate limit quota**: shared with `/preview-backstory` at 10/min/user. Is this enough for 15-turn chat? Worst case 15 rpm in a tight session → still within limit. Confirm in `/plan` load-test.

## 11. Cross-references

- Functional spec: `specs/214-portal-onboarding-wizard/spec.md` (FR-11c, FR-11d, FR-11e, NR-1b)
- Approved plan: `~/.claude/plans/quirky-floating-liskov.md` (research base + 12 UX citations + code intel synthesis)
- Prior shipped scope: FR-1 through FR-11b (PR-A/B/C/D + PR #322), unchanged
- Related specs: Spec 001 (main text agent, persona source), Spec 042 (pipeline), Spec 060 (prompt caching), Spec 213 (FirstMessageGenerator, backstory preview endpoint), Spec 214 PR-D (PUT chosen-option endpoint)
- Rules: `.claude/rules/testing.md`, `.claude/rules/pr-workflow.md`, `.claude/rules/parallel-agents.md`
- Diagram: `docs/diagrams/20260417-onboarding-journey-actual-vs-intended.md` (add FR-11c/d/e rows on ship)
