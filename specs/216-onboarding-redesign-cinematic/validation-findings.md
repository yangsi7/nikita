# Spec 216 Validation Findings Manifest

**Source**: GATE 2 parallel validator run, 2026-04-29
**Iteration**: 2 of max 3 (per SDD enforcement rule 7) — **GATE 2 CLEAN**
**Branch**: `feat/216-onboarding-redesign-cinematic`
**Status**: ✅ ALL 6 VALIDATORS PASS — 0 CRIT + 0 HIGH across api/auth/frontend/data/testing/architecture

## Iteration 2 — Aggregate Verdict (2026-04-29)

| Validator | Iter1 verdict | Iter2 verdict | Iter1 (CRIT/HIGH/MED/LOW) | Iter2 (CRIT/HIGH/MED/LOW) |
|-----------|---------------|---------------|---------------------------|---------------------------|
| sdd-architecture-validator | **PASS** | (not re-run; was clean) | 0 / 0 / 2 / 3 | 0 / 0 / 2 / 3 |
| sdd-api-validator | NEEDS_FIXES | **PASS** | 2 / 7 / 5 / 3 | 0 / 0 / 0 / 2 |
| sdd-auth-validator | NEEDS_FIXES | **PASS** | 0 / 3 / 4 / 2 | 0 / 0 / 0 / 0 |
| sdd-frontend-validator | NEEDS_FIXES | **PASS** | 0 / 4 / 5 / 2 | 0 / 0 / 0 / 0 |
| sdd-data-layer-validator | NEEDS_FIXES | **PASS** | 0 / 1 / 4 / 2 | 0 / 0 / 0 / 1 |
| sdd-testing-validator | NEEDS_FIXES | **PASS** | 0 / 3 / 4 / 3 | 0 / 0 / 2 / 3 |
| **Total** | | **GATE 2 CLEAN** | **2 / 18 / 24 / 15** | **0 / 0 / 4 / 9** |

All 2 CRIT + 18 HIGH iter-1 findings closed via spec amendments. Remaining MEDIUM/LOW are non-blocking documentation hygiene + deferred items (formula resolution, MC validator, GH issues queued).



## Iteration 1 — Aggregate Verdict

| Validator | Verdict | CRIT | HIGH | MED | LOW |
|-----------|---------|------|------|-----|-----|
| sdd-architecture-validator | **PASS** | 0 | 0 | 2 | 3 |
| sdd-frontend-validator | NEEDS_FIXES | 0 | 4 | 5 | 2 |
| sdd-data-layer-validator | NEEDS_FIXES | 0 | 1 | 4 | 2 |
| sdd-api-validator | NEEDS_FIXES | 2 | 7 | 5 | 3 |
| sdd-auth-validator | NEEDS_FIXES | 0 | 3 | 4 | 2 |
| sdd-testing-validator | NEEDS_FIXES | 0 | 3 | 4 | 3 |
| **Total** | | **2** | **18** | **24** | **15** |

**Note**: api-validator HIGH-1 (A1.9 disambiguation) overlaps with auth-validator HIGH-1; counted once in 18.

## CRITICAL Findings (closed in iteration 1)

| ID | Source | Issue | Fix | AC binding |
|----|--------|-------|-----|------------|
| C1 | api-validator | `POST /api/v1/onboarding/answer` lacks named Pydantic models | Added `AnswerRequest` + `AnswerResponse` to master spec §HTTP API Contracts; AC B1.13 declares `response_model=AnswerResponse` + OpenAPI metadata | master + B1.13 |
| C2 | api-validator | No documented `responses={...}` status-code map | Added status-code matrix to master spec §HTTP API Contracts (200, 401, 422, 429, 500); AC B1.13 binds | master + B1.13 |

## HIGH Findings (closed in iteration 1)

| Source | Subspec | Issue | Fix | AC |
|--------|---------|-------|-----|-----|
| api + auth | 216-A | A1.9 magic-link idempotency was disjunction not predicate | Tightened to deterministic cookie-presence predicate; 302 if cookie valid, 400 + ErrorEnvelope otherwise | A1.9 (revised) |
| api | master | Error envelope shape + codes not specified | Added `ErrorEnvelope` model + `ErrorCode` StrEnum to master | master §HTTP API Contracts |
| api | 216-B | UnexpectedModelBehavior fallback shape unspecified | 200 + AnswerResponse with `meta.fallback_reason` | B1.17 |
| api | 216-B | Auth mechanism on /answer not stated | `Depends(require_auth_cookie)`; 401 envelope | B1.14 |
| api | 216-B | No deprecation path for legacy /converse | 410 Gone shim 1 deploy cycle | B1.16 |
| api | 216-B | No idempotency on POST /answer | turn_id UUID4 check-before-write | B1.15 |
| api | 216-E | Tool failure log shape unspecified | Structured `agent_tool_call` log shape in master + E1.9 | master + E1.9 |
| api | 216-E | FIRECRAWL_API_KEY secret handling unstated | Cloud Run secret env var; never logged or returned | E1.10 |
| auth | 216-A | JWT cookie attributes not asserted | A1.10: HttpOnly + Secure + SameSite=Lax + Path=/ + Max-Age≥604800 | A1.10 |
| auth | 216-A | Concurrent magic-link click race not in AC | A1.11 with asyncio.gather integration test | A1.11 |
| frontend | 216-C | A11y ARIA contracts absent | C1.12 enumerates per-control ARIA + keyboard contracts | C1.12 |
| frontend | 216-C | "+ other" 40-char rule ambiguous | Hard cap 40 + maxLength + len/40 helper | C1.6 (revised) |
| frontend | 216-C | Missing chrome components from inventory | Added CityInput, SuggestionChips, PersonalizingBadge, BackLink, NikitaThinkingDots, FallingPattern to Critical Files | Critical Files table |
| frontend | 216-C | Auth guard underspecified | C1.13 Server Component cookie read + redirect | C1.13 |
| data | 216-D | Backfill predicate brittle (length<64) | Replaced with regex `cache_key !~ '^[a-f0-9]{64}$'` | D1.8 (revised) |
| testing | 216-F | NikitaReaction missing from F1.6 | Added to vitest scope | F1.6 (revised) |
| testing | 216-F | integration_full_flow.test.tsx unbound | Bound to F1.6 with concrete assertions | F1.6 (revised) |
| testing | 216-F | M3+M4 fixtures missing from F1.2 | Per-meta-prompt fixture counts: M1=3, M2=12, M3=3, M4=3 (≥21 total) | F1.2 (revised) |

## MEDIUM Findings (deferred to in-spec amendments OR GH issues)

| Severity | Source | Issue | Disposition |
|----------|--------|-------|-------------|
| MED | architecture | M-1 ConverseDeps schema not enumerated | **Closed in iteration 1**: master §Type System Anchors enumerates 14 fields |
| MED | architecture | M-2 SlotKind enum source not pinned | **Closed in iteration 1**: master §Type System Anchors defines `SlotKind` StrEnum |
| MED | api | Cookie flags (Secure, HttpOnly, SameSite) | Closed via A1.10 |
| MED | api | GET /auth/confirm side-effect note | Documented in master §HTTP API Contracts |
| MED | api | OpenAPI metadata absent | Closed via B1.13 |
| MED | api | Per-user rate limit | Closed via B1.22 |
| MED | api | firecrawl timeout per-attempt | Closed via E1.11 |
| MED | api | builtin_tools vs @agent.tool conflated | Closed via E1.12 |
| MED | api | prepared_web_search vs prepare_tools API | Closed via E1.12 (verify against Pydantic AI 1.71.0 in /clarify) |
| MED | auth | A1.8 wrong-OTP destructive purge | Closed via A1.14 (escalates #437 if violated) |
| MED | auth | A1.12 resume mid-wizard AC | Closed via A1.12 |
| MED | auth | Plus-alias inbox tolerance | Closed via Test Identity section |
| MED | auth | Telegram preview suppression scope | Closed via A1.13 |
| MED | data | M1 column placement (top-level vs JSONB) | Closed via D1.10 (top-level chosen) |
| MED | data | M2 constraint idempotency (DO-block) | Closed via D1.11 |
| MED | data | M3 brand_resonance_signal formula | **Deferred** to GH issue (placeholder cosine similarity per Open Q4) |
| MED | data | M4 Big5 MC validator + boundary triplet | **Deferred** to 216-D /implement phase per `.claude/rules/stochastic-models.md` |
| MED | frontend | Loading/pending/error states | Closed via C1.14 |
| MED | frontend | Resume mid-wizard UX | Closed via C1.15 |
| MED | frontend | AnimatePresence key uniqueness | Closed via C1.16 |
| MED | frontend | Reduced-motion ProgressRail | Closed via C1.17 |
| MED | frontend | Radix Slider declaration | Closed via C1.12 (uses Radix Slider) |
| MED | testing | M1 Big5 conflicting-signal assertion shape | **GH issue** filed (deferred to 216-D /implement) |
| MED | testing | M2 post-walk row-count gate explicit | **In-spec amendment** for F1.8 (queued for iteration 2 if validator flags) |
| MED | testing | M3 F1.9 process-check reformulation | Acceptable per current spec; F1.9 explicitly tagged as Post-walk step |
| MED | testing | M4 G.5 firecrawl log filter | Closed via E1.9 + master HTTP contracts log shape |

## LOW Findings (logged, non-blocking)

| Source | Issue | Disposition |
|--------|-------|-------------|
| architecture | NR-02 prompt-caching AC | Closed via B1.20 |
| architecture | p99 latency budget | Routed to 216-E + 216-F W4 walk |
| architecture | result.new_messages() JSONB shape | Closed via B1.21 |
| api | Telegram-secret-header regression test | **GH issue** filed |
| api | _send_bare_portal_auth_link Open Q1 resolution | Closed via 216-A Open Questions resolution |
| api | per-turn cost_events table | **GH issue** filed (telemetry phase) |
| auth | FSM completed-state transition | **GH issue** filed (documented in Spec 215) |
| auth | Rate limiting on bare /start | Closed via 216-A Out of Scope |
| data | L1 cohort cache index strategy | Acceptable (no DB index needed) |
| data | L2 migration filename NNN | **GH issue** filed (resolves at PR-open) |
| frontend | Hobby chip taxonomy TBD | **GH issue** filed (lock pre-216-C kickoff) |
| frontend | Visual-diff tooling | Soften to subjective parity per inspector judgment |
| testing | Test pyramid ratio explicit | Closed via inspection (~75/19/6) |
| testing | G.6 archetype_candidates persistence | Closed via D1.12 |
| testing | G.11 banned-vocab regex tightening | Closed via C1.11 (revised regex) |

## User Approval (Phase 5 prerequisite)

- [ ] User has reviewed iteration 1 fixes
- [ ] CRIT+HIGH count after iteration 2 = 0
- [ ] MEDIUM disposition acceptable (in-spec / GH issue / accepted)
- [ ] Approve proceeding to /plan

## Next steps

1. Re-dispatch 5 validators (skip architecture — already PASS) for iteration 2
2. If iteration 2 returns 0 CRIT + 0 HIGH → record outcome here, mark task #33 + #50 complete
3. File pending GH issues for unresolved MEDIUM/LOW items
4. Get user approval per SDD rule 7
5. Proceed to Phase 1.C (`/plan` + `/tasks` + `/audit`)

If iteration 2 still has CRIT+HIGH → iteration 3 (final). If iteration 3 fails → escalate per SDD rule 7 (NEVER auto-waive).
