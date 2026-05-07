# Subspec 217-2 — Backstory Fallback (FE Guard + BE Defense-in-Depth)

**Parent**: `specs/217-onboarding-wizard-deterministic-redesign/spec.md` FR-4a, FR-4b, FR-4c (deferred)
**PR boundary**: 217-2 (depends on 217-1 merged)
**Estimated**: 80-150 LOC (mostly FE + 5 LOC BE)
**Status**: Draft (GATE 1)
**Authoritative inputs**: Frozen spike `docs-to-process/20260507-spec217-2-backstory-diagnosis.md`

---

## Scope

Fixes the user-reported "preparing the three of us…" indefinite hang by addressing root cause **C5** (per spike artifact): FE has no fallback when `archetype_cards === null` in the `archetype` screen branch at `portal/src/app/onboarding/_components/WizardShell.tsx:771-776`. BE-side `default_archetype_cards` already exists; the missing piece is the FE guard.

The brief's original Reqs #5 (`POST /preview-backstory/restart` endpoint), #6 (polling-related observability), and #7 (35s polling timeout) are SUPERSEDED per ERRATA — the wrong architecture (legacy 213/214 PipelineGate path). The 216 `/answer` route is already idempotent on `(user_id, turn_id)` per `portal_onboarding.py:1846-1851`; FE retry simply re-POSTs.

### Cross-Spec Audit-Backlog Overlap

Per spike artifact §216-audit overlap-check:
- **F-2 (216-DE-wire)** CRIT closed — overlaps INDIRECTLY (`should_populate_archetype_cards` gate at `wiring.py:94-99` is in the same code path; gate works correctly per audit T-B-13 + T-D-2). Cite this overlap in PR body.
- **D1.12** (`archetype_candidates` JSONB column) — partial overlap if FR-4c rehydration ships; column already authored.
- Total overlap ≈ 30 LOC, well under the 400-LOC split threshold. Do NOT split 217-2.

## Acceptance Criteria

| AC | Description | Severity |
|---|---|---|
| AC-4a.1 | `WizardShell.tsx` `case "archetype":` block (currently L771-776) renders shadcn/ui `Alert` with retry CTA after 3-5s if `state.lastResponse.output.archetype_cards === null`; ELSE renders existing 3-card picker | CRITICAL |
| AC-4a.2 | Retry button click POSTs `/api/v1/onboarding/answer` with the user's last input (uses existing `(user_id, turn_id)` idempotency cache); on success `state.lastResponse.output.archetype_cards` populates and the picker renders | CRITICAL |
| AC-4a.3 | EITHER (preferred): screen-advance guard refuses to advance `screenIndex` to `archetype` until `archetype_cards` is non-null in `state.lastResponse` — making the placeholder unreachable. Implementor picks AC-4a.1+2 OR AC-4a.3, not both. | HIGH |
| AC-4a.4 | Structured log emitted on FE fallback fire: `console.warn("backstory_fallback_fired", { user_id_hash, reason: "null_cards" })` (FE-side; BE Sentry hook optional) | MEDIUM |
| AC-4b.1 | `nikita/api/routes/portal_onboarding.py:1367` wraps `pick_three_archetypes(...)` in `asyncio.wait_for(..., timeout=20.0)`; on `asyncio.TimeoutError` the existing `except Exception` returns `default_archetype_cards(...)` | HIGH |
| AC-4b.2 | Structured log on BE timeout: `logger.warning("backstory_pipeline_timeout", extra={"user_id_hash": ..., "stage": "archetype", "elapsed_ms": ...})` | MEDIUM |
| AC-4c.1 (DEFERRED) | OPTIONAL — `/state` response shape includes `archetype_cards` for cross-device resume. Defer to a follow-up spec if AC-4a + AC-4b close the user-visible hang. | DEFERRED |
| AC-T.1 | New vitest `portal/src/app/onboarding/_components/__tests__/WizardShell.archetype-fallback.test.tsx`: (a) renders Alert when `archetype_cards === null`, (b) retry click triggers POST, (c) POST success advances to picker | HIGH |
| AC-T.1bis (TEST-M2 RESOLVED) | The 3-5s fallback timer MUST be tested with virtualized clock — NEVER real wall-clock (would slow test by 3-5s each, multiplied across re-runs). Required vitest scaffold: `import { vi, beforeEach, afterEach } from "vitest"; beforeEach(() => { vi.useFakeTimers(); }); afterEach(() => { vi.useRealTimers(); });` Test body uses `vi.advanceTimersByTime(3000)` between the initial render assertion (`expect(screen.queryByRole("alert")).toBeNull()`) and the post-timeout assertion (`expect(screen.getByRole("alert")).toBeInTheDocument()`). If a Playwright e2e variant is added at `portal/e2e/onboarding-archetype-fallback.spec.ts`, it MUST use `await page.clock.install({ now: ... })` followed by `await page.clock.fastForward(3000)` (Playwright virtualized clock primitive) — NOT `await page.waitForTimeout(3000)`. | HIGH |
| AC-T.2 | New pytest `tests/api/routes/test_portal_onboarding_archetype_timeout.py`: mocks `pick_three_archetypes` to sleep 25s; asserts `wait_for` raises `asyncio.TimeoutError` and route returns response with `default_archetype_cards` | HIGH |
| AC-W.1 | Walk B2 from `simon.yang.ch+walkB2@gmail.com` per `live-testing-protocol.md`; drives 11 turns until `next_slot_kind=backstory_pick`; captures response body via Chrome MCP DevTools network tab. Anti-fabrication discipline applies. DB cleanup post-walk. | HIGH |
| AC-W.2 | Walk B2 falsifier (per spike): if `output.archetype_cards` is 3-element array → BE healthy, FE fallback covers (mechanism-1). If null AND <3s response → BE conditional skipped picker (mechanism-2 covered by AC-4b). Either way, user-visible hang resolved. | HIGH |

## Files Touched

- `portal/src/app/onboarding/_components/WizardShell.tsx:771-776` (FR-4a guard)
- `portal/src/app/onboarding/_components/__tests__/WizardShell.archetype-fallback.test.tsx` (NEW vitest)
- `nikita/api/routes/portal_onboarding.py:1367` (FR-4b 5-LOC `wait_for`)
- `tests/api/routes/test_portal_onboarding_archetype_timeout.py` (NEW pytest, IF not already in scope)
- (DEFERRED FR-4c) `nikita/api/routes/portal_onboarding.py` `/state` shape — separate spec if needed

## Pydantic AI / Agentic-Design-Patterns Notes

This sub-PR does NOT modify the agent emission contract or `WizardSlots`. Hard rule conformance is preserved by leaving `nikita/agents/onboarding/` untouched. The 5-LOC BE patch at `portal_onboarding.py:1367` is route-layer code, NOT agent code.

## Out of Scope

- Agent emission union (217-3A).
- FE wizard refactor (217-3B).
- `/preview-backstory/restart` endpoint (DROPPED per ERRATA — wrong architecture).
- 35s polling timeout (DROPPED per ERRATA — wrong scenario).
