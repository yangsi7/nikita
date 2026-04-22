# Frontend Validation Report — FR-11d Amendment (v2)

**Spec:** `specs/214-portal-onboarding-wizard/spec.md` (branch `spec/214-fr11d-slot-filling-amendment`, commit 72e06d6)
**Scope:** FR-11d frontend concerns only (AC-11d.2, AC-11d.7, AC-11d.8, a11y, localStorage, flag semantics)
**Status:** FAIL
**Timestamp:** 2026-04-23T00:00:00Z

---

## Summary

- CRITICAL: 1
- HIGH: 1
- MEDIUM: 1
- LOW: 1

---

## Findings

| Severity | Category | Issue | Location | Recommendation |
|----------|----------|-------|----------|----------------|
| CRITICAL | Wire-Format / TypeScript Types | `ConverseResponse` TypeScript type is missing `link_code` and `link_expires_at` fields. These are part of the spec-mandated wire-format extension (AC-11d.7) but are absent from the FE type definition. The wizard works around this by calling a separate `api.linkTelegram()` POST endpoint instead. This means the FE is operating on a different integration contract than the spec requires. | `portal/src/app/onboarding/types/converse.ts:30-40` | Add `link_code?: string \| null` and `link_expires_at?: string \| null` to `ConverseResponse`. The spec at line 731 requires FE to reject responses where `conversation_complete=True` but either link field is null — this guard cannot be implemented if the fields are absent from the type. |
| HIGH | AC-11d.8 — GET Reload / Re-mint Flow | The spec (line 733) mandates that when GET /conversation returns `link_code_expired: true`, the FE re-runs `/converse` with the existing `conversation_history` to re-mint a fresh code. No such code path exists in the FE. The `getConversation()` hydration branch (onboarding-wizard.tsx:79-100) maps `progress_pct` and `elided_extracted` but has no branch checking `link_code_expired` and no re-mint call. The wizard also defers link minting to a second POST call (`api.linkTelegram()`) rather than reading the code from the /converse terminal response or GET hydration. | `portal/src/app/onboarding/onboarding-wizard.tsx:79-100` | Add `link_code_expired` to the GET response type and handle it in the `getConversation()` `.then()` block: if `data.link_code_expired === true`, immediately re-call `api.converse({conversation_history: state.turns})` to trigger re-mint. |
| MEDIUM | AC-11d.2 — FE Mirror of BE `progress_pct` | The spec requires the FE reducer to mirror `response.progress_pct` verbatim and never recompute. The reducer does correctly write `progressPct: response.progress_pct` on the `server_response` action (useConversationState.ts:169). However, the 429 rate-limit fallback path in `onboarding-wizard.tsx:162-175` constructs a synthetic `server_response` with `progress_pct: state.progressPct` — i.e., it preserves the prior value rather than deriving a new one. This is acceptable (it keeps the last server-authoritative value), but it also means if the 429 occurs mid-session the reducer will re-emit a `server_response` action that re-sets `isComplete: false` (line 171). If the user has already received a terminal response and the 429 fires on a subsequent (redundant) turn, this would incorrectly clear `isComplete`. | `portal/src/app/onboarding/onboarding-wizard.tsx:162-175` | The 429 synthetic response should not override `isComplete` — add `conversation_complete: state.isComplete` instead of hardcoding `false`. This ensures a completed wizard is not un-completed by a stray rate-limit error on any retry attempt after the terminal turn. |
| LOW | `ClearanceGrantedCeremony` — Missing `aria-label` on CTA anchor | The "Meet her on Telegram" CTA is an `<a>` element with visible text content, which is acceptable. However the link opens `target="_blank"` with no accessible warning that it opens in a new tab. WCAG 2.1 SC 3.2.2 (On Input) / advisory: links opening in new windows should signal this to SR users. | `portal/src/app/onboarding/components/ClearanceGrantedCeremony.tsx:100-116` | Add `aria-label="Meet her on Telegram (opens in new tab)"` or append a visually-hidden `<span className="sr-only">(opens in new tab)</span>` inside the anchor. |

---

## Detailed Findings

### CRITICAL — `ConverseResponse` TypeScript type missing `link_code` + `link_expires_at`

**Spec requirement (line 724-731):** FR-11d Wire-Format Extension states that `ConverseResponse` is extended additively with `link_code: str | None = None` and `link_expires_at: datetime | None = None`. The spec explicitly states: "FE MUST reject responses where `conversation_complete=True` but either link field is null (treat as server bug, surface error UI per AC-11b.5)."

**Current FE type (`types/converse.ts:30-40`):**

```typescript
export interface ConverseResponse {
  nikita_reply: string
  extracted_fields: Record<string, unknown>
  confirmation_required: boolean
  next_prompt_type: PromptType
  next_prompt_options?: string[] | null
  progress_pct: number
  conversation_complete: boolean
  source: "llm" | "fallback" | "idempotent" | "validation_reject"
  latency_ms: number
  // link_code and link_expires_at are ABSENT
}
```

**Consequence:** The FE has worked around this by making a separate `api.linkTelegram()` POST call after `conversation_complete` fires (onboarding-wizard.tsx:131-143). This is a divergence from the spec's intended integration contract where the terminal /converse response carries the link payload. It also means the spec's guard ("FE MUST reject responses where `conversation_complete=True` but either link field is null") cannot be enforced in the reducer.

The existing `api.linkTelegram()` approach may work in practice, but it represents a spec/code contract mismatch that will cause confusion during implementation of the BE changes in AC-11d.7. Once the BE ships `link_code` in the terminal /converse response, the FE will silently ignore those fields (unknown properties pass through in TS), and two mint calls (one from the FE's POST, one implicit in the BE) may produce conflicting codes.

**Recommendation:** Add to `ConverseResponse`:
```typescript
link_code?: string | null
link_expires_at?: string | null
```
Then update the `server_response` reducer case to set `state.linkCode` from `response.link_code` when `response.conversation_complete === true` and `response.link_code` is non-null — eliminating the separate `api.linkTelegram()` POST call. Add the guard: `if (response.conversation_complete && !response.link_code) → dispatch server_error`.

---

### HIGH — AC-11d.8 GET reload / re-mint flow: no FE code path

**Spec requirement (line 733):** "If the previously minted code has expired (FE refreshes the page > 10 min after completion), the GET returns `link_code=None, link_expires_at=None` AND a new flag `link_code_expired: bool = False` [sic, should be `True`] — FE then re-runs `/converse` with the same conversation_history to re-mint a fresh code via the existing completion-gate path."

**Current FE:** The `getConversation()` hydration block (onboarding-wizard.tsx:79-100) reads:
- `data.conversation` → `turns`
- `data.elided_extracted` → `extractedFields`
- `data.progress_pct` → `progressPct`

It does NOT read `data.link_code`, `data.link_expires_at`, or `data.link_code_expired`. If a user refreshes the portal page more than 10 minutes after completing the wizard, the FE will hydrate the chat with the prior turns and show the chat shell again — there is no path that detects the completed-but-expired state and either (a) shows an interstitial while re-minting, or (b) re-runs `/converse` to trigger re-mint.

**Recommendation:** Add `link_code`, `link_expires_at`, `link_code_expired` to the GET /conversation response type and handle them in the hydration `.then()` block:

```typescript
if (data.conversation_complete && data.link_code) {
  // Hydrate to isComplete=true with existing code — show ceremony immediately.
  dispatch({ type: "link_code", code: data.link_code, expiresAt: data.link_expires_at })
  dispatch({ type: "server_response", response: { ...syntheticTerminal, conversation_complete: true } })
} else if (data.link_code_expired) {
  // Re-mint path: converse with existing history, gate will succeed, BE mints fresh code.
  void triggerConverse(state.turns)
}
```

---

## Component Inventory

| Component | Type | Shadcn | Notes |
|-----------|------|--------|-------|
| `ChatShell` | Custom | None | Correct `role="log"` on scroll container + dedicated `role="status" aria-live="polite"` SR sibling — a11y PASS |
| `ClearanceGrantedCeremony` | Custom | None | Hard-throws on null `linkCode` (AC-T4.1.3) — correct guard. CTA `target="_blank"` missing new-tab SR hint (LOW). |
| `OnboardingWizard` (ChatOnboardingWizard) | Custom | None | Flag gate `isLegacyFlagOn()` correctly reads `NEXT_PUBLIC_USE_LEGACY_FORM_WIZARD`. Ceremony render gate tied to `state.isComplete` (correct). Interstitial spinner + error surface present. |
| `useConversationState` reducer | Hook | None | `progressPct: response.progress_pct` at line 169 — verbatim mirror, PASS for AC-11d.2 main path. 429 fallback preserves prior `progressPct` (acceptable). |
| `ConverseResponse` (TypeScript type) | Type | N/A | Missing `link_code` + `link_expires_at` — CRITICAL gap vs spec wire-format extension. |

---

## Accessibility Checklist

- [x] Chat log: `role="log"` on scroll container (ChatShell.tsx:66)
- [x] SR live region: dedicated `role="status" aria-live="polite" aria-atomic="true"` sibling announcing newest Nikita reply (ChatShell.tsx:101-109)
- [x] Ceremony interstitial: `role="status" aria-live="polite"` spinner while link minting (onboarding-wizard.tsx:210-213)
- [x] Link error UI: `role="alert"` on mint-failure panel (onboarding-wizard.tsx:234)
- [x] `prefers-reduced-motion`: `motion-safe:` Tailwind variants on ceremony fade-in (ClearanceGrantedCeremony.tsx:74-77)
- [x] Legacy flag toggle: correctly scoped to build-time env var, no runtime DOM side-effects
- [ ] CTA anchor: missing new-tab SR hint on `target="_blank"` (LOW)

---

## Responsive / Dark Mode Checklist

- [x] Ceremony: `min-h-[100dvh]` + `gap-8` responsive layout
- [x] QR code: `QRHandoff` component present, desktop-only gating is within component scope
- [x] Dark mode: `bg-background`, `text-foreground`, `text-muted-foreground`, `text-primary` semantic tokens throughout — no raw color literals observed
- [x] Chat shell: `h-[100dvh]` viewport-aware height

---

## localStorage Scope Checklist (spec line 745)

Spec requires: under chat-first variant, `localStorage` MUST NOT cache `WizardSlots`, `progress_pct`, or `conversation_complete`. Only ephemeral UI state permitted.

**Verification:** No `localStorage` calls were observed in:
- `useConversationState.ts` (useReducer, no localStorage)
- `onboarding-wizard.tsx` (useState, no localStorage)
- `ChatShell.tsx` (no localStorage)
- `ClearanceGrantedCeremony.tsx` (no localStorage)

All state is in-memory React state. **localStorage constraint: PASS.**

---

## Flag Semantics Checklist (AC-T3.9.2)

- [x] FR-1 SUPERSEDED callout at spec.md:52 correctly identifies the flag name `NEXT_PUBLIC_USE_LEGACY_FORM_WIZARD` and states "default = chat-first; flag=true reverts to FR-1 step wizard"
- [x] `isLegacyFlagOn()` in onboarding-wizard.tsx:36-39 reads `process.env.NEXT_PUBLIC_USE_LEGACY_FORM_WIZARD === "true"` — correct build-time check
- [x] Default behavior (flag unset/undefined) returns `false` via the `typeof process === "undefined"` guard — chat-first is the default

---

## Recommendations

### 1. CRITICAL — Add `link_code` + `link_expires_at` to `ConverseResponse` TypeScript type

File: `portal/src/app/onboarding/types/converse.ts`

```typescript
export interface ConverseResponse {
  // ... existing fields ...
  /** Present only on the terminal turn (conversation_complete=true). Null on all prior turns. */
  link_code?: string | null
  link_expires_at?: string | null
}
```

Then update the `server_response` reducer case in `useConversationState.ts` to set `linkCode` from `response.link_code` when available — removing the dependency on the separate `api.linkTelegram()` POST call. Add the guard per spec line 731.

### 2. HIGH — Implement GET reload + re-mint path (AC-11d.8)

The `getConversation()` `.then()` block in `onboarding-wizard.tsx` must:
1. Check for `data.conversation_complete === true` with a valid `data.link_code` → dispatch `link_code` action and hydrate to isComplete state.
2. Check for `data.link_code_expired === true` → re-call `/converse` with the hydrated `turns` to trigger BE re-mint (Pydantic gate succeeds, fresh code returned).

This requires extending the GET response TypeScript type (parallel to `ConverseResponse` extension).

### 3. MEDIUM — Fix 429 fallback hardcoded `conversation_complete: false`

File: `portal/src/app/onboarding/onboarding-wizard.tsx:171`

Change:
```typescript
conversation_complete: false,
```
To:
```typescript
conversation_complete: state.isComplete,
```

This prevents a 429 error on any post-terminal retry from resetting `isComplete` to false and un-mounting the ceremony.

### 4. LOW — Add new-tab SR hint to CTA

File: `portal/src/app/onboarding/components/ClearanceGrantedCeremony.tsx:100-116`

```tsx
<a
  ...
  aria-label="Meet her on Telegram (opens in new tab)"
>
  {CTA_LABEL}
</a>
```

---

## Pass/Fail Rationale

**Status: FAIL.** The CRITICAL finding (missing `link_code`/`link_expires_at` from `ConverseResponse` TypeScript type) means the FE cannot implement the spec's required wire-format guard. The HIGH finding (missing AC-11d.8 GET reload re-mint flow) is a spec-mandated user-facing recovery path with no current FE code path.

Both must be resolved before this spec is ready for implementation planning. The two MEDIUM/LOW findings are non-blocking but should be addressed in the same PR to avoid a follow-up QA iteration.

**What PASSES:**
- AC-11d.2 main path: `progressPct` mirrors BE verbatim (line 169), no FE recomputation
- Ceremony render gate: correctly gated on `state.isComplete` + `state.linkCode`
- localStorage constraint: fully respected — no wizard state persisted locally
- Flag semantics: correctly implemented (`NEXT_PUBLIC_USE_LEGACY_FORM_WIZARD`)
- Accessibility: `role="log"` + SR live region pattern in ChatShell
- Dark mode: semantic tokens throughout, no raw color literals
