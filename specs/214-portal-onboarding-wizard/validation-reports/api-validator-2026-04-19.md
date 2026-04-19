# sdd-api-validator Report, Spec 214 Amendment

**Date**: 2026-04-19
**Scope**: FR-11c, FR-11d, FR-11e, NR-1b
**Validator**: sdd-api-validator
**Spec refs**: `specs/214-portal-onboarding-wizard/spec.md` + `technical-spec.md`

## Findings

### CRITICAL

None. Core contracts (request/response Pydantic models, status codes, auth dependency, fallback strategy) are explicitly specified in technical-spec §2.3 and tracked by AC-11d.3 / AC-11d.9.

### HIGH

1. **Authz failure mode on `user_id` mismatch is not specified** (tech-spec §2.3 line 172). The handler `Validate req.user_id == current_user.id (authz)` is stated but the HTTP response on mismatch is undefined. REST-correct answer is 403 (Forbidden — authenticated but operating on another user) OR 404 (avoid leaking user existence, safer for enumeration). Pick one and encode it; right now implementers will coin their own convention. Recommendation: `403` with envelope `{"error": "user_mismatch", "detail": "..."}` to match the existing `portal_onboarding` PATCH profile convention, and add an AC to Spec FR-11d requiring it.

2. **Rate-limit saturation behavior not specified for a 15-turn chat flow** (spec §FR-11d line 713, tech-spec §10.5). Shared `preview-backstory` quota at 10/min/user. A normal chat run can plausibly exceed 10 `converse` calls/min during rapid typing + correction + backstory preview interleaved with the existing `preview-backstory` consumer that reserves 1+ calls. Spec says "shared with `/preview-backstory`"; in §10.5 it hand-waves "15 rpm in a tight session → still within limit" (15 > 10, so the math contradicts the claim). Observable consequence: legitimate wizard users see 429s mid-turn with no documented UX. Recommendation: raise the per-endpoint quota for `converse` to ≥20/min OR add separate quota for `converse` + explicit AC "429 triggers an in-character `source='fallback'` reply, does NOT halt wizard, does NOT surface a red banner" (currently AC-11d.9 only covers timeout/validator reject paths, not 429 specifically).

3. **Idempotency contract for `POST /converse` is absent** (tech-spec §2.3, AC-11d.3). Non-idempotent POST by design (each turn mutates `onboarding_profile.conversation` JSONB + advances state). But network-retry semantics are not defined: if the client resends the same turn due to a dropped socket, the server currently has no dedupe — the conversation history will double-write the user turn, break progress math, and poison persistence. Recommendation: require an `Idempotency-Key` header (or client-sent `turn_id: UUID`) and an explicit AC "replay with same key returns the original response without re-invoking the agent". Critical once PR 3 rolls out and real mobile networks are in the loop.

4. **Server greeting atomicity / error-path gap for `_handle_start_with_payload`** (spec §FR-11e AC-11e.3 line 759, tech-spec §2.5). Spec text says `pending_handoff` is cleared "in the same transaction" as the proactive greeting send. Problem: `bot.send_message` is an external HTTP call to Telegram's servers, not a DB statement. It cannot be inside a DB transaction. Observable failure: DB transaction commits (flag cleared) → `send_message` fails after retry exhaustion → user never receives greeting AND flag is cleared, so the one-shot gate blocks future retry on first user message (legacy path). Recommendation: restate AC-11e.3 as "pending_handoff is cleared AFTER a successful Telegram API response (200 OK) on the proactive greeting; on send_message exception, flag remains True and the legacy first-user-message path will re-trigger greeting generation, preserving fallback safety". Technical-spec §2.5 should add this ordering explicitly.

5. **Telegram webhook 10-second timeout is not addressed for `_handle_start_with_payload`** (tech-spec §2.5). After atomic bind, the handler must return 200 to Telegram's webhook within 10s, but now must also: (a) generate a handoff greeting (potentially an LLM call through `FirstMessageGenerator`, which historically takes 1-3s), (b) dispatch via `bot.send_message`. Under load or LLM latency spike, the webhook handler could time out. Recommendation: dispatch the proactive greeting via `asyncio.create_task` (fire-and-forget background task) AFTER returning the webhook response; explicitly state that the confirmation text sends synchronously but the greeting sends asynchronously. Add AC: "webhook returns HTTP 200 to Telegram within 2s regardless of greeting-generation latency".

### MEDIUM

6. **HTTP verb for `converse` is POST — correct, but SSE streaming question is left unresolved** (tech-spec §10.1). Open question #1 defers SSE to `/plan`. If the answer is "yes, stream", the endpoint contract changes materially: `response_model=None`, `StreamingResponse` with `media_type="text/event-stream"`, and AC-11d.3's "200 on success" becomes ambiguous (status 200 with chunked body, or the first SSE frame carries a status?). Recommendation: resolve this before `/plan` exits — not after. If SSE, amend technical-spec §2.3 with the stream format (event types: `reply_chunk`, `extracted`, `complete`; keep-alive every 15s per ops convention).

7. **`source` field enum-leak on error** (tech-spec §2.3 line 158, §2.3 validation table line 178). `source: Literal["llm", "fallback"]`. If an unexpected exception escapes the fallback path (e.g., DB write fails while persisting the turn), the endpoint behavior is undefined — does it 500 with no body? Return `source="error"` (not in the Literal)? Spec says "never raise 500 for agent issues" but is silent on persistence failures. Recommendation: add `source="error"` to the Literal OR specify a separate 503 path with `Retry-After` header for persistence outages. AC-11d.3 says "500 only if the server-side fallback itself fails" — tighten to "500 on unexpected exception; 503 with Retry-After on DB unavailable".

8. **`schema_version` is a client-side-only concept; server does not version the JSONB** (spec §NR-1b line 554-555). The spec says `schema_version: 2` is bumped in the `WizardPersistedStateV2` (localStorage), and "migration shim: v1 → v2 synthesizes `conversation: []`" (AC-NR1b.3). But the JSONB payload at `users.onboarding_profile` is not versioned. Observable consequence: if the backend ships before the frontend (PR 2 merged, PR 3 deferred), and a future fourth schema adds a field, there's no server-side signal to coordinate the client. Recommendation: add a `schema_version` key to the JSONB subfield too (default 1 for existing rows, 2 for new writes post-FR-11d), and document in AC-NR1b.3 that both stores carry the version.

9. **Rate-limit 429 response envelope is not specified** (spec §FR-11d). The existing `portal_onboarding` endpoints likely set a `Retry-After` header on 429 (standard FastAPI SlowAPI pattern), but the spec doesn't enforce it. The client-side fallback at AC-11d.9 does not reference 429 at all. Recommendation: amend AC-11d.3 to require `Retry-After` header on 429 responses.

10. **Existing contract preservation of `PATCH /portal/onboarding/profile` and `PUT /portal/onboarding/profile/chosen-option`** (spec context, implicit). Spec implies the old field-write endpoints stay usable but does not explicitly say whether `converse` is the sole write path for onboarding fields going forward, or whether PATCH remains as a fallback. In tech-spec §4.1 it says "PATCH ... already accepts arbitrary JSONB keys (Spec 213 contract)" — used by `converse` internally? Or still callable by the client? Recommendation: add to AC-11d.10 "PATCH /portal/onboarding/profile remains available for out-of-band writes (wizard_step persistence, cross-device resume) but MUST NOT be called by the chat flow; the server writes all chat-extracted fields via the `converse` handler's own write path". Clarify whether `converse` internally reuses the PATCH service method or bypasses it.

11. **GET `/pipeline-ready` flow from chat completion not traced** (spec §FR-11d AC-11d.13, §NR-5). AC-11d.13 says completion triggers the FR-11e ceremony; NR-5 says `/pipeline-ready` is polled on step 11 for voice-ringing / degraded state. The new chat flow never explicitly enters the "pipeline gate" step (tech-spec §3.3 mentions "Keep PipelineGate (step 10 theatrical); it sits between conversation-complete and ceremony, unchanged"). But the spec does not clarify WHEN `/pipeline-ready` polling kicks off — on `conversation_complete=true` or on ceremony mount? Observable bug: chat completes → ceremony renders → CTA clicked → Telegram opens, BUT voice-path users never saw the ring animation because PipelineGate was visually skipped. Recommendation: add AC to FR-11e clarifying the step-11 journey (PipelineGate → Ceremony) for both voice and text paths, and specify where `/pipeline-ready` polling lives in the new chat flow.

### LOW

12. **Response model `nikita_reply: str = Field(max_length=500)` vs "140 chars in practice"** (tech-spec §2.3 line 151). `max_length=500` is the Pydantic gate but comment says "server validator enforces <=140". This dual-cap is confusing. Recommendation: set `max_length=140` directly at the schema level; delete the comment's hand-wave.

13. **OpenAPI `responses={}` dict is not referenced** for `converse` endpoint (tech-spec §2.3). Standard FastAPI pattern: `responses={422: {...}, 429: {...}, 500: {...}}` on the decorator for `/docs` clarity. Recommendation: AC-11d.3 should require this dict.

14. **`tags=["onboarding"]` and `summary`/`description`** are not specified for the new route (tech-spec §2.3). Existing `portal_onboarding.py` presumably has these; new route should too.

15. **`ControlSelection` type is referenced but not defined** (tech-spec §2.3 line 147). `Union[str, ControlSelection]`. Shape of `ControlSelection` is implied (chip label, slider value, toggle choice, card pick) but no Pydantic model is shown. Recommendation: add the Pydantic definition inline in tech-spec §2.3.

16. **No explicit mention of `async def` on the new route handler** (tech-spec §2.3). Handler will do async Pydantic AI calls + async DB writes; must be `async def converse(...)`. Currently reads as `async def` implicitly, but since this validator is pedantic: confirm in the signature.

17. **Proactive greeting retry policy on Telegram-API 5xx not specified** (tech-spec §2.5). Telegram occasionally returns 500/502 on send_message; `bot.send_message` library may retry once. Spec should state the retry budget (e.g., 3 retries with exponential backoff, then fall back to first-user-message legacy path).

18. **`trigger: Literal["handoff_bind", "first_user_message"]` is an internal parameter, not an API boundary** (tech-spec §2.4). It's fine as an internal function argument, but the technical spec presents it in a table suggesting an external contract. Recommendation: explicitly label this as an internal function signature, not a public API.

19. **One-shot semantics for `/start <code>` second call** (spec §FR-11e AC-11e.3 line 759). Spec says second call is a no-op with "welcome-back renders"; but does the code get re-consumed (already deleted per FR-11b) or re-validated? Ambiguity: if a user taps CTA twice quickly and the second webhook arrives after atomic DELETE, the payload handler sees an unknown code and short-circuits with the "expired link" error (AC-11b.4), not welcome-back. Recommendation: explicit AC "second `/start <code>` after successful bind: if `users.pending_handoff=false` AND `user.onboarding_status='completed'`, return welcome-back regardless of payload code validity".

## Strengths

- **Response schema is fully typed** with `Literal` enums on `next_prompt_type`, `source`, and role. Field constraints on `progress_pct` (0-100), `nikita_reply` max-length gate, and `ConverseResult` via Pydantic AI's result_type are sound.
- **Fallback strategy is clear and well-specified** (AC-11d.9 enumerates timeout / agent exception / validator reject as the three paths, all producing `source="fallback"` with the full response shape preserved). This is exactly right for a user-facing LLM-backed endpoint.
- **Server-side validation rules table** (tech-spec §2.3 line 184) is explicit, enumerable, and testable — length, markdown, quotes, PII-concat, age, phone, country. This is rare in spec work.
- **FR-11c DI guard uses `RuntimeError`, not `assert`** (AC-11c.9) — correct defensive coding per `python -O` stripping. Good catch.
- **No-500-on-agent-issue discipline** (tech-spec §2.3 step 7). Keeps the wizard resilient to LLM outages.
- **PATCH + PUT existing contracts are preserved** (tech-spec §4.1 note "already accepts arbitrary JSONB keys"). No breaking change.
- **NIKITA_PERSONA verbatim import** (AC-11d.11) locks voice consistency across the three agents. Persona-drift is a real risk this addresses.
- **Error envelope convention** is implicit via FastAPI HTTPException throughout portal_onboarding.py — consistent with existing shape.

## Summary

The amendment's API surface is substantially complete and well-specified for FR-11d's new endpoint, with fully typed request/response Pydantic models, explicit fallback semantics, and a clear validation rules table. No CRITICAL findings; the design is sound at the contract level.

Five HIGH findings cluster around operational edge cases that need tightening before planning: (1) authz mismatch response code, (2) rate-limit math contradicts itself and doesn't define saturation UX, (3) idempotency for retried chat turns is absent and will bite on mobile networks, (4) "same transaction" atomicity claim on `_handle_start_with_payload` conflates DB commits with external Telegram API calls, (5) Telegram's 10s webhook timeout interacts dangerously with synchronous greeting generation. Each is a specific, bounded amendment — not a rewrite. MEDIUM findings (6-11) are contract polish (SSE resolution, 503 path, OpenAPI tags, PATCH-vs-converse coexistence, pipeline-gate flow) — nice to have before `/plan`, not blocking. LOW findings are clean-up.

Recommendation: **FAIL** on the current draft pending HIGH fixes 1-5 (particularly 3-5, which alter the wire protocol and handler structure). MEDIUM findings can be addressed in `/plan` phase.
