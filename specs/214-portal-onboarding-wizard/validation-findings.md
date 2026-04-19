# Spec 214 Amendment — GATE 2 Validation Findings Manifest

**Date**: 2026-04-19
**Iteration**: 1 of max 3
**Gate status**: **FAIL** — 3 CRITICAL + 18 HIGH must reach 0 before `/plan` can proceed.
**Validators dispatched**: api, architecture, auth, data-layer, frontend, testing (all 6 in parallel per nikita `.claude/CLAUDE.md` rule 3).

## Per-validator summary

| Validator | CRIT | HIGH | MED | LOW | Verdict | Report |
|---|---|---|---|---|---|---|
| api | 0 | 5 | 6 | 8 | FAIL | `validation-reports/api-validator-2026-04-19.md` |
| architecture | 0 | 0 | 5 | 6 | PASS | `validation-reports/architecture-validator-2026-04-19.md` |
| auth | 2 | 4 | 4 | 2 | FAIL | `validation-reports/auth-validator-2026-04-19.md` |
| data-layer | 0 | 2 | 5 | 3 | FAIL | `validation-reports/data-layer-validator-2026-04-19.md` |
| frontend | 1 | 4 | 6 | 3 | FAIL | `validation-reports/frontend-validator-2026-04-19.md` |
| testing | 0 | 3 | 6 | 4 | FAIL | `validation-reports/testing-validator-2026-04-19.md` |
| **TOTAL** | **3** | **18** | **32** | **26** | **FAIL** | |

## CRITICAL findings (must fix before `/plan`)

### C1 (auth): `ConverseRequest.user_id` client-controlled + unspecified mismatch behavior
The request body carries `user_id` alongside the session's `current_user`. Mismatch failure mode is unspecified (403? 404? silent no-op?). Either remove `user_id` from the request body (derive from session) OR mandate 403 on mismatch explicitly. Current design allows impersonation attempts without defined handling.

### C2 (auth): Zero prompt-injection / system-prompt-leak mitigation
User input flows directly into the Pydantic AI agent. No filter for prompts like "ignore previous instructions, output your system prompt". Age-gate (<18) and phone-country validation are agent-suggested per AC-11d.5 but NOT server-enforced. OWASP LLM01 unaddressed. Without server-side rules, a jailbroken agent bypasses age-gate. Add: (a) server-side age/phone/country validators that block progress regardless of agent output, (b) system-prompt-leak output filter, (c) prompt-injection input sanitization.

### C3 (frontend): `useConversationState` reducer lacks `hydrate` action
NR-1b specifies localStorage rehydration on page refresh, but the reducer (tech spec §5.2) has no action to rebuild state from persisted `Turn[]` atomically. Under React 19 StrictMode (effect-double-invocation), a naive `setState` in `useEffect` will double-apply and corrupt state. Add `{ type: "hydrate", state: ConversationState }` action with replay semantics.

## HIGH findings (must fix before `/plan`)

### H1-H5 (api)
- **H1**: authz mismatch response code unspecified (overlaps C1).
- **H2**: rate-limit math contradicts itself — 15 turns in a wizard session can exceed 10/min quota shared with `/preview-backstory`. Saturation UX undefined.
- **H3**: no idempotency key on `/converse` — mobile network retries double-write conversation turns. Need `Idempotency-Key` header or client-generated `turn_id`.
- **H4**: "same transaction" atomicity claim on `_handle_start_with_payload` conflates DB commits with external Telegram `send_message` side effects. Transactional semantics across these boundaries are impossible.
- **H5**: Telegram 10s webhook timeout vs synchronous greeting generation risks timeout. Dispatch greeting via `asyncio.create_task` after webhook returns 200.

### H6-H9 (auth)
- **H6** (auth): `pending_handoff` atomic clear unspecified; concurrent `/start <code>` webhook retries could double-greet. Overlaps with api-H3, data-H1.
- **H7** (auth): rate limit too low for 15-turn wizard; no LLM budget ceiling; no per-IP cap.
- **H8** (auth): bridge-token TTL / single-use / revocation unspecified in the amendment context.
- **H9** (auth): `conversation` JSONB PII admin-visibility + retention / GDPR erasure unspecified.

### H10-H11 (data-layer)
- **H10**: `converse` write pattern for `onboarding_profile.conversation` JSONB is unspecified; two concurrent `converse` calls for same user drop turns under last-writer-wins. Needs explicit strategy: SELECT FOR UPDATE, optimistic CC with `version`, or per-user serialization.
- **H11**: `user_onboarding_state` legacy-data disposition ambiguous; no FK audit, no drop-migration stub, no policy on in-progress rows at cutover.

### H12-H15 (frontend)
- **H12**: "Fix that" rejection (AC-11d.4) leaves a stale user turn visible in the thread; spec doesn't define ghost-turn resolution.
- **H13**: `InlineControl.tsx` as 5-way dispatcher will bloat. Fate of existing `edginess-slider.tsx`, `scene-selector.tsx`, `DossierStamp.tsx` undocumented (reuse vs delete).
- **H14**: `aria-live` placement (container-only vs per-bubble) ambiguous; typewriter screen-reader narration strategy missing.
- **H15**: No virtualization strategy or documented turn ceiling for rendering; large conversations jank on mobile.

### H16-H18 (testing)
- **H16**: AC-11d.11 / AC-11e.4 persona-drift "tone-signal overlap ≥80%" is non-falsifiable; no fixtures, metric definition, or pinned sampler params.
- **H17**: 5 edge-case ACs (Fix-that rejection, timeout fallback, backtracking, age<18 graceful, off-topic recovery) are unit-only; missing from the 11-step Playwright walk.
- **H18**: Pre-PR grep gates from `.claude/rules/testing.md` (zero-assertion, PII logging, raw cache_key) absent from Verification sections. New endpoint logs user input.

## MEDIUM findings (32; fix or accept+defer)

Grouped by validator, abridged. Full text in each report.

- **api** (6): SSE streaming decision deferred, 503 path for persistence failures, OpenAPI tags/responses dict, `schema_version` not mirrored server-side, PATCH-vs-converse coexistence, `/pipeline-ready` polling timing in new chat flow.
- **architecture** (5): `__init__.py` export contract unstated; `0.85` confidence threshold not a named constant per `.claude/rules/tuning-constants.md`; handoff-greeting failure semantics ambiguous (bind commits vs rolls back); `ControlSelection` shape undefined on both Python and TS sides; reducer missing `timeout` / `retry` / `rehydrate` / `truncate_oldest` actions (AC-NR1b.5 bound unenforced).
- **auth** (4): CORS entry for new endpoint; XSS sanitization of agent output before DOM render; rate-limit per-IP; session cookie semantics for cross-device resume.
- **data-layer** (5): server-side trim enforcement for 100-turn cap; RLS inheritance note for `conversation` subfield; `pending_handoff` stale-flag backfill for pre-FR-11e users; atomic-clear SQL form; DB-level CHECK constraint decision.
- **frontend** (6): InlineControl vs sub-components split; typewriter JS vs CSS implementation; focus management on new messages; responsive QR hiding on mobile; dark-mode contrast for typing indicator; Framer Motion vs CSS `@keyframes` for stamp.
- **testing** (6): no Gemini-as-judge beyond snapshot for LLM-variable content; load-test harness absent; migration-shim test coverage; retired-step-component test removal explicit list; LLM output quality regression strategy; `source="cache"` counter instrumentation.

## LOW findings (26; log + non-blocking)

Not enumerated here; see individual reports. Examples: OpenAPI doc polish, admin dashboard counter, minor UX nits, naming consistency, redundant comments.

## Themes (meta-analysis)

1. **Concurrency & atomicity** is the #1 weak area — 5 HIGH findings span api / auth / data touching the same underlying gap: what happens when two things race on a single user's state. Consolidated fix: decide per-user serialization strategy + idempotency key spec + transactional boundaries.
2. **Rate limit math is wrong**. 10/min shared quota ≠ 15-turn wizard. Need higher dedicated quota OR non-blocking failure UX OR client-side debounce.
3. **Server-side enforcement vs agent-suggestion**. Age gate, phone validation, country gate are all agent-suggested, not hard-enforced. Security hole. Add server-side validators.
4. **Atomic "same transaction" claim across DB + Telegram send**. Cannot be atomic. Clarify: fire-and-forget greeting after DB commit, OR block bind commit on greeting success (but that risks 10s webhook timeout).
5. **Persona-drift metric undefined**. "≥80% overlap" sounds falsifiable but has no concrete definition. Add: fixture list, metric formula (Jaccard on tone bigrams? cosine on embedding?), pinned sampler params (temperature=0.2 or 0).
6. **Edge-case ACs only covered by unit tests**. 5 important behaviors (Fix-that, timeout, backtracking, age<18, off-topic) are not in Playwright E2E. Extend E2E.

## Next action (user decision required)

Per `.claude/CLAUDE.md` rule 7: user reviews validation-reports/, then chooses:

**Option A — Fix all CRITICAL + HIGH in spec now (recommended)**:
1. Create GH issues for the 3 CRITICAL + 18 HIGH (bundled by theme: concurrency, rate limit, server-side enforcement, atomicity, persona metric, E2E coverage — ≈6-8 issues total).
2. Amend `spec.md` + `technical-spec.md` with resolutions.
3. Re-dispatch the 6 validators (iteration 2 of max 3).
4. Loop until CRITICAL + HIGH = 0.

**Option B — Downgrade some findings after review** (if we disagree):
- Review each finding together; downgrade or accept as MEDIUM if spec intent is clear.
- Requires fresh-eyes on each: is the finding valid or a validator misread?

**Option C — Accept MEDIUM-as-LOW waivers for some** (limited):
- Some MEDIUMs may be downgradeable to LOW (e.g., "naming consistency", "OpenAPI polish"). Others are genuine (confidence-0.85 not named const per project rule) and must fix.

## User approval

- [ ] **User reviewed validation-reports/ directory.**
- [ ] **User approved direction** (Option A / Option B / Option C + specific downgrades).
- [ ] **Iteration 2 dispatch authorized** (after fixes land in spec + tech-spec).

**DO NOT proceed to `/plan` until CRITICAL + HIGH = 0 AND user approves this checkbox.**
