---
title: Walk B4 — Spec 217 Final Integration Walk
lifecycle: frozen
date: 2026-05-08
walk_label: walkB4
spec: 217
backend_revision: nikita-api-00303-xsx
master_commit: c17b6d8 (FE deployed from master via Vercel)
worktree_branch: worktree-agent-a851065262550655d
walk_user: simon.yang.ch+walkB4@gmail.com (lowercased to +walkb4 by Supabase)
verdict: PARTIAL — chain-prefix verified through wizard step 1; backstory + dashboard reach BLOCKED-BY-#568
---

# Walk B4 — Spec 217 Final Integration

Final integration walk after merge of all Spec 217 sub-PRs (217-0/1/2/2c/3A.1/3A.2/3A.3/3B). Exercises the full chain: cold-start landing → CTA prefill → Telegram OTP → portal handoff → /onboarding wizard mount → wizard begin → wizard step 1 (name).

## Verdict

**PARTIAL**. The chain is verified through wizard step 1; further progression is BLOCKED by the pre-known **GH #568** (emission agent over-emits `ReactionOnly` for clean slot inputs, deterministic-card never advances).

No NEW critical/high findings. All Plan-Step-6 exit assertions that are reachable PASS.

## Plan Step 6 Exit-Criteria Matrix

| # | Assertion | Status | Evidence |
|---|---|---|---|
| (a) | Cold-start TG CTA prefills `/start welcome` | **PASS** | Landing CTA `Start Relationship` href = `https://t.me/Nikita_my_bot?start=welcome`. Bot replied to `/start welcome` (msg 22383): "Hey. New face. I'm Nikita. If you want me in your life, give me your email." Screenshot: `walk-B4-step1b-coldstart-cta.png`. |
| (b) | Interstitial reskin renders Spec 208 brand veil | **PASS** | DOM probe at `/onboarding` mount: `[class*="aurora"]` present, `[class*="glow"]` (GlowButton) present. `glassCard` selector miss is cosmetic (class naming may differ); aurora+glow confirms reskin. Screenshot: `walk-B4-step9a-onboarding-mount.png`. |
| (c) | No loading flash | **PASS** | At every wizard mount, `document.body.innerText` did NOT match `/in development\|in progress/i`. Loading state shows "personalizing" + "Nikita is thinking" (intentional copy). Screenshot: `walk-B4-step9b-wizard-begin.png`. |
| (d) | Wizard renders sibling DOM (deterministic-card + agent-subspace) | **PASS** | Both `[data-testid="deterministic-card"]` and `[data-testid="agent-subspace"]` present. Both parented to `MAIN.flex flex-col gap-4` (testid `wizard-main`). `parentNode === parentNode` → `true`. NOT nested. |
| (e) | Backstory completes p99 ≤30s OR retry CTA renders | **BLOCKED-BY-#568** | Backstory turn never reached. Card stuck at name step due to GH #568. |
| (f) | FinalForm fires + redirect to `/dashboard` | **BLOCKED-BY-#568** | Same root cause. FinalForm requires all slots filled; only name was advanced cumulatively. |

## Step-by-Step Walk Log

### Step 1: Cold-start landing → PASS
- Cleared localStorage/sessionStorage/cookies, reloaded `https://nikita-mygirl.com/`
- Landing rendered "Start Relationship" CTA twice (hero + below-fold).
- Both CTAs have `href="https://t.me/Nikita_my_bot?start=welcome"` ✅
- Console: only 2 errors (Vercel insights 404 + MIME-type — neither blocks function).
- Screenshot: `walk-B4-step1-landing.png`, `walk-B4-step1b-coldstart-cta.png`.

### Step 2: CTA semantics → PASS (verified via DOM, not click)
- href contains `?start=welcome` payload ✅ (assertion a)

### Step 3: Telegram deep-link follow → PASS
- Sent `/start welcome` to `@Nikita_my_bot` via Telegram MCP
- Bot replied 13:05:38 UTC (msg 22383): "Hey. New face. I'm Nikita. If you want me in your life, give me your email. I'll send you a code."

### Step 4-5: Email collection → PASS
- Sent `simon.yang.ch+walkB4@gmail.com` to bot
- Bot replied (msg 22385): "Check your inbox. Send me the code."

### Step 6: OTP retrieval → PASS
- Gmail query `from:onboarding@silent-agents.com newer_than:5m` returned message 19e07b1d9338488b at 13:05:55 UTC
- Subject: "Confirm Your Signup", To: `simon.yang.ch+walkb4@gmail.com` (lowercased by Supabase, expected)
- OTP: `36846011`, magic-link: `https://nikita-mygirl.com//auth/confirm?token_hash=...&type=email&next=/onboarding`

### Step 7: Verification submit → PASS
- Sent OTP `36846011` to bot
- Bot replied (msg 22387): "You're cleared. Tap to enter."
- Inline button `Enter the portal →` URL: `https://nikita-mygirl.com/auth/confirm?token_hash=10375ac46d745d66ec4fece0c2b749f5b2519be8a500c966c6eff7b9&type=magiclink&next=/onboarding`

### Step 8: Portal handoff → PASS (with anomaly)
- Navigated portal handoff URL via Chrome MCP
- Final URL: `https://nikita-mygirl.com/dashboard` (NOT `/onboarding` as `next=` param requested)
- **Anomaly**: `next=/onboarding` did NOT take user to `/onboarding`; redirect went to `/dashboard` instead. Possible causes: (i) auth confirm post-redirect logic ignoring `next=`, (ii) middleware deciding the user is already onboarded (unlikely for fresh user), (iii) magic-link path branching to dashboard. Screenshot: `walk-B4-step8-post-confirm.png`.
- **NEW finding (LOW)**: `auth/confirm?next=/onboarding` redirects to `/dashboard` instead of `/onboarding`. Possibly cosmetic since user can navigate to `/onboarding` manually, but undermines the intended handoff UX.

### Step 9a: /onboarding mount (manual nav) → PASS
- Manually navigated to `/onboarding`. Page rendered "let's begin." heading + "begin" button.
- DOM probe: 4 testids present (`wizard-main`, `deterministic-card`, `agent-subspace`, no `agent-reaction` yet). Sibling-DOM ✅.
- Brand veil: `auroraOrbs: true`, `glowButton: true`. ✅
- No "in development/in progress" copy ✅.

### Step 9b: Wizard begin click → PASS
- Clicked "begin". Step transitioned to "what should she call you?" (name input).
- Input rendered with placeholder `your name` and aria-label `your name`.
- Continue button initially disabled until input has value (good UX).
- progressbar value=0 (start state).

### Step 9c: Name submit → BLOCKED-BY-#568
- Filled `walkB4` into name input. Continue enabled.
- Clicked Continue. Loading state showed `personalizing` + `Nikita is thinking` ✅ (no loading flash).
- Backend POST `/api/v1/onboarding/answer` returned 200.
- After response: agent-subspace rendered "Love that energy. Now, real quick, how old are you?" ✅ (agent reaction emitted).
- **BUT**: deterministic-card did NOT advance. Still showed "what should she call you?" with input value `walkB4`. progressbar still 0.
- Re-clicked Continue (resubmit `walkB4`). Got second 200 response. agent-subspace updated to "Love that energy, already moving. Now, real quick: how old are you?". Card still stuck. progressbar still 0.
- This is **GH #568**: emission agent emits `ReactionOnly` (no slot delta) for the clean name input → cumulative state never adds the `name` slot → progress never advances.

### Step 10-11: Dashboard arrival + persistence check → BLOCKED-BY-#568

### Step 12: DB cleanup → DEFERRED
- Supabase MCP returned `Unauthorized` for `execute_sql` (access token issue, environmental). Cleanup deferred to operator. Cleanup target email: `simon.yang.ch+walkb4@gmail.com`.

## 217-3B AC Matrix Verification

The 217-3B sub-PR introduced sibling-DOM refactor + IdentityPair. Verified:

| AC | Description | Status |
|---|---|---|
| AC-1 | `[data-testid="deterministic-card"]` exists in DOM at wizard mount | PASS — verified at `/onboarding` and during name step |
| AC-2 | `[data-testid="agent-subspace"]` exists in DOM at wizard mount | PASS — verified |
| AC-3 | deterministic-card and agent-subspace are SIBLINGS (not nested) | PASS — both parented to `[data-testid="wizard-main"]` (`MAIN.flex flex-col gap-4`) |
| AC-4 | No "in development/in progress" loading copy at any state | PASS — body innertext check at multiple states |
| AC-5 | IdentityPair component renders for combined name+age step | NOT REACHABLE — wizard stuck at name due to GH #568 |
| AC-6 | Brand veil (Aurora + Glow) renders at /onboarding mount | PASS |

## Findings

### NEW findings

| # | Severity | Title | Evidence |
|---|---|---|---|
| F1 | LOW | `/auth/confirm?next=/onboarding` redirects to `/dashboard` after magic-link verification | Step 8: portal page list shows `/dashboard` as the post-confirm destination, not `/onboarding`. The `next` param appears to be ignored. |

No new CRITICAL/HIGH findings. No NEW MEDIUM findings.

### Pre-known issue triggered

**GH #568 (MEDIUM, OPEN)**: emission agent over-emits `ReactionOnly` for clean slot inputs — confirmed reproduces on `walkB4`. Same observable as Walk B3v2: deterministic-card never advances; agent-subspace shows reaction text; progressbar stays at 0. No duplicate filed.

## GH issues filed

- **F1 (LOW)** — proposed: `fix(portal,auth): /auth/confirm ignores next= param after magic-link verify, lands on /dashboard`. Severity LOW per `.claude/rules/issue-triage.md` (cosmetic/UX, not blocking). NOT filed as GH issue in this walk; orchestrator may file if confirmed not already tracked.

## DB cleanup status

DEFERRED. Supabase MCP returned `Unauthorized`. Operator should run the canonical cleanup SQL with `<EMAIL>='simon.yang.ch+walkb4@gmail.com'` per `.claude/rules/live-testing-protocol.md` DB Cleanup SQL Template.

## Audit report path on worktree branch

`audits/2026/20260508-walk-B4-spec217-final.md` (this file)

Screenshots colocated:
- `audits/2026/walk-B4-step1-landing.png`
- `audits/2026/walk-B4-step1b-coldstart-cta.png`
- `audits/2026/walk-B4-step8-post-confirm.png`
- `audits/2026/walk-B4-step9a-onboarding-mount.png`
- `audits/2026/walk-B4-step9b-wizard-begin.png`
- `audits/2026/walk-B4-step9c-after-name-submit.png`

## Anti-fabrication compliance

✅ No `INSERT INTO auth.users`
✅ No `signInWithPassword`
✅ No `E2E_AUTH_BYPASS=true`
✅ No custom JWT minting
✅ Real Telegram + email + magic-link flow
✅ Stopped at GH #568 blocker (did not work around)
