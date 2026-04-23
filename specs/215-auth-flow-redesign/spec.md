# Feature Specification: Auth Flow Redesign — Telegram-First Signup (Spec 215)

**Spec ID**: 215-auth-flow-redesign
**Status**: DRAFT v1 (pending GATE 2 validators)
**Date**: 2026-04-23
**Author**: Phase C executor (per Plan v17.1)
**Authority**: Plan v17.1 (`~/.claude/plans/delightful-orbiting-ladybug.md`) + ADR-010 (Telegram-first signup direction) + ADR-011 (live-testing-protocol-as-rule)
**Number-collision note**: directory `215-heartbeat-engine/` also exists (COMPLETE). Per project precedent (`210-kill-skip-variable-response/` + `210-test-quality-audit/`), duplicate number prefixes are tolerated when directory slugs differ. ROADMAP tracks both.
**Supersedes (implicit)**:
- Spec 208 anon-CTA target (`/onboarding/auth`) — overridden by §4 FR-1 (CTA → Telegram deep-link)
- Spec 214 implicit "auth precondition is portal magic-link" — Spec 215 owns auth; Spec 214 wizard executes post-auth
- GH #393 (PKCE 422 on `/auth/callback` for new signups) — eliminated by `verifyOtp({token_hash, type})` (non-PKCE) replacement; resolved architecturally
- Legacy Telegram-first OTP (`registration_handler.py` + `otp_handler.py`) — replaced by consolidated `signup_handler.py`
- `auth_bridge_tokens` table + `/auth/bridge` route — collapsed to `portal_bridge_tokens` + new `/auth/confirm`

---

## §1 Goals

1. **Telegram-first signup**: anonymous landing visitors enter via Telegram (`t.me/Nikita_my_bot?start=welcome`), not a portal magic-link form. The bot collects email, sends an OTP code to inbox, verifies the code in chat, then mints a single-use magic-link delivered IN-CHAT (not by email) for the user to tap and enter the portal wizard.
2. **Single source of truth for identity**: `auth.users` is the only place a user identity is created. No fabricated rows. `telegram_id ↔ auth.uid()` binds during the signup phase (before wizard), making `/start <CODE>` (FR-11b) idempotent on re-tap.
3. **Eliminate PKCE failure surface**: `/auth/confirm?token_hash=…&type=…&next=…` calls `verifyOtp({token_hash, type})` (non-PKCE), removing GH #393 entirely.
4. **Nikita-voiced auth UX everywhere**: returning-user `/login` is Nikita-voiced; iOS interstitial post-magic-link is Nikita-voiced; error states never bounce to a generic `/login?error=…` cold page.
5. **Full auth ownership**: signup, login, session refresh, dashboard auth gates, error UX, and email templates are all under Spec 215. Spec 214 references Spec 215 as an entry precondition, not an internal collaborator.

## §2 Non-goals / Out of scope

- **Voice onboarding (Spec 028)** — voice path is preserved for already-onboarded users; voice-onboarding redesign is a separate spec lifecycle.
- **Email change flow** — DEFERRED to Spec 215 v2 (rare path; v1 escape hatch documented in §4 FR-15).
- **Telegram LoginUrl / native ID** — REJECTED for v1 per plan §18.7 D12: game UX requires a verified email, so OTP path stays.
- **Single sign-on (Google / Apple)** — out of scope; passwordless OTP only.
- **Password authentication** — explicitly never. The system is passwordless end-to-end.
- **Multi-device linking** — `/start <CODE>` retains the link-code primitive, but no UI for "link a second device" lands in v1.
- **Multi-locale** — English-only.
- **Daily engagement emails** — moves to NEW Spec 216 (per plan §20 S4).
- **Schema migration tooling for in-flight users** — destructive reset of 5 dev `pending` users per D6 (plan §18.5 verification 2 + §19); productionised migration tool is out of scope.

## §3 User flows

### §3.1 Happy path (Telegram-first signup → wizard → game)

```
LANDING (portal /, anon)
├─ [CTA-Hero] "Start Relationship" → href="https://t.me/Nikita_my_bot?start=welcome"
├─ [CTA-Cta]  same
└─ [CTA-Nav]  same  (+ visible "Sign in" secondary link → /login per FR-11)

[USER TAPS CTA → Telegram opens]

TELEGRAM /start welcome   (signup_handler.handle_welcome)
├─ no telegram_id↔user binding yet
├─ Nikita greets in-character + "What's your email?"
└─ session.signup_state = AWAITING_EMAIL

[USER SENDS EMAIL]

TELEGRAM email handler   (signup_handler.handle_email)
├─ regex validate format
├─ supabase.auth.sign_in_with_otp({email, options:{should_create_user:True}})
│   └─ Supabase sends ONE email → 6-digit OTP code (template per docs §1.1)
├─ store telegram_signup_sessions(telegram_id, email, signup_state="code_sent",
│       attempts=0, last_attempt_at=now, expires_at=now+5min)
└─ Nikita: "Check your inbox. Send me the 6-digit code."

[USER RECEIVES EMAIL → 6-digit code only — NO LINK]

TELEGRAM code handler   (signup_handler.handle_code)
├─ regex ^[0-9]{6}$
├─ supabase.auth.verify_otp({email, token, type:"email"})
│   ├─ INVALID → attempts++ ; if 3+ → rate-limit message
│   └─ VALID → continue
├─ supabase.auth.admin.generate_link(
│       {type:"magiclink", email,
│        options:{redirect_to:"<portal>/auth/confirm?next=/onboarding"}})
│   └─ returns {action_link, hashed_token, verification_type, ...}
│       NB: verification_type is dynamic — "magiclink" if user pre-exists,
│       "signup" if NEW. Backend MUST use response value, NOT hardcode (§21).
├─ public.users row binding (FR-11b 307 auto-provision; idempotent if exists)
├─ UPDATE users SET telegram_id = <tg_id> WHERE id = <auth_uid>
├─ session.signup_state = MAGIC_LINK_SENT ; magic_link_sent_at = now
└─ Nikita reply via inline URL button:
   text:  "You're cleared. Tap to enter."
   button: action_link
   send_message(..., disable_web_page_preview=True)   ← MANDATORY (§5 NFR-Sec-1)

[USER TAPS LINK → mobile browser / IAB opens Supabase verify URL]
[Supabase verifies token, sets cookies, 302 → portal /auth/confirm?token_hash=…&type=…&next=/onboarding]

PORTAL /auth/confirm (route handler)   (NEW — portal/src/app/auth/confirm/route.ts)
├─ read ?token_hash, ?type, ?next from query
├─ if missing → redirect /login?error=missing_params
├─ createServerClient (cookies adapter per @supabase/ssr docs)
├─ supabase.auth.verifyOtp({type, token_hash})   ← type is from query, NOT hardcoded
├─ if error → redirect /login?error=<code>
└─ render IS-A always-interstitial page (NOT raw 302)
   ├─ "You're cleared. Enter the portal." (Nikita voice)
   ├─ Primary button "Enter the portal" → router.push(next)
   └─ Secondary "Open in Safari" Universal Link (iOS IAB escape, ~150 LOC)

PORTAL /onboarding   (existing Spec 214 FR-11d wizard)
├─ getUser() passes (just minted)
├─ if onboarded → /dashboard
└─ mount OnboardingWizard (chat-first, cumulative state, Pydantic gate)

[WIZARD CONVERSATION_COMPLETE → ClearanceGrantedCeremony (FR-11b retained)]
├─ S2: wizard slot for "preferred call window" was collected pre-completion
├─ S3: ceremony copy adds "Bookmark this portal — your dashboard, history, and
│       Nikita's daily highlights live here."
└─ a href="t.me/Nikita_my_bot?start=<LINK_CODE>"  (FR-11b — synchronous user-tap gate)

[USER TAPS → Telegram /start <CODE>]

TELEGRAM /start <CODE>   (existing FR-11b path; semantics adjusted per D1)
├─ verify_code atomic DELETE..RETURNING
├─ telegram_id is ALREADY bound (signup phase)
│   └─ update_telegram_id is IDEMPOTENT no-op
├─ claim_handoff_intent (one-shot)
└─ BackgroundTasks._dispatch_handoff_greeting
   └─ S2: Nikita proactively proposes phone-call within first 3 turns

[GAME STARTS]
```

### §3.2 Supporting diagrams (lifted from Plan §18.10 tree-of-thought)

Six diagrams produced by review agent `a0827ffa586d754ce` are referenced (not embedded inline) — Phase D `/plan` will copy them into `docs/diagrams/onboarding-journey-v17.md`:

1. Landing-page user-state decision tree (anon / auth-not-onboarded / auth-onboarded)
2. Telegram-first signup FSM (`UNKNOWN → AWAITING_EMAIL → CODE_SENT → MAGIC_LINK_SENT → BOUND → COMPLETED`)
3. Happy-path sequence diagram (User / Telegram / Bot / Supabase / Email / Browser / Portal, latency budget t<30s)
4. Failure-mode sequences (4a code expired, 4b magic-link TTL, 4c different email mid-flow)
5. Data-model dependency ERD with write-sites + dead tables marked
6. Phase-by-phase delivery Gantt with parallelization markers

### §3.3 Returning-user login flow

```
LANDING NAV "Sign in" → /login (Nikita-voiced)
├─ email form (existing portal/src/app/login/page-client.tsx, REDESIGNED)
├─ supabase.auth.signInWithOtp({email,
│     options:{emailRedirectTo:"<portal>/auth/confirm?next=/dashboard"}})
│   └─ Supabase sends email containing magic LINK only (template §1.2 of docs)
├─ user clicks link in email → Supabase /verify → /auth/confirm (same handler)
└─ Nikita-voiced "You're cleared. Welcome back." interstitial → /dashboard
```

Returning login email template is **link-only** (D2 round 1). Telegram signup template is **code-only**. Two different Supabase template configurations; documented in §7 Architecture + Supabase dashboard runbook.

---

## §4 Functional Requirements

### FR-1 — Landing CTAs flip to Telegram deep-link
**Description**: All three landing CTAs (`hero-section.tsx`, `cta-section.tsx`, `landing-nav.tsx`) render `href="https://t.me/Nikita_my_bot?start=welcome"` for the anonymous branch. Authenticated branch behavior preserved per FR-11 (D3).

**Acceptance** (AC-1):
- AC-1.1: For anon visitor, Hero/Cta/Nav buttons emit `<a href="https://t.me/Nikita_my_bot?start=welcome">…</a>` with no `<Link>` interception
- AC-1.2: For auth'd-not-onboarded user, button routes to `/dashboard` (which middleware-redirects to `/onboarding` if `onboarding_status != 'completed'`)
- AC-1.3: For auth'd-onboarded user, button routes to `/dashboard`; nav shows secondary "Continue with Nikita" → Telegram deep-link

### FR-2 — Telegram bot greets + collects email
**Description**: When `/start welcome` is received and the calling `telegram_id` has no bound `auth.users.id`, signup_handler greets Nikita-style and asks for email. Subsequent free-text from this user enters `signup_handler.handle_email`. Email is regex-validated (`^[^\s@]+@[^\s@]+\.[^\s@]+$`); invalid → Nikita-voiced rejection ("That email doesn't look right. Try again.").

**Acceptance** (AC-2):
- AC-2.1: `/start welcome` for unbound `telegram_id` triggers welcome message and sets `signup_state=AWAITING_EMAIL` row in `telegram_signup_sessions`
- AC-2.2: invalid-email submission emits Nikita-voiced rejection AND keeps `signup_state=AWAITING_EMAIL` (no row mutation)
- AC-2.3: valid-email submission triggers FR-3

### FR-3 — Backend OTP send via `sign_in_with_otp` (signup template fires)
**Description**: For valid email, backend calls `client.auth.sign_in_with_otp({email, options:{should_create_user:True}})`. Supabase fires the SIGNUP email template (code-only per D2 round 1; new HTML referenced in `docs-to-process/20260423-auth-templates-v17-1.md` §1.1). Stores `telegram_signup_sessions(telegram_id, email, signup_state='code_sent', expires_at=now+5min, attempts=0, last_attempt_at=now)`. Nikita reply: "Check your inbox. Send me the 6-digit code."

**Acceptance** (AC-3):
- AC-3.1: `sign_in_with_otp` is called with `should_create_user=True`
- AC-3.2: row inserted/updated in `telegram_signup_sessions` with TTL = 5 min (D10)
- AC-3.3: Nikita reply matches Nikita-voice tone (no SaaS "Email sent successfully")
- AC-3.4: Supabase signup email template renders `{{ .Token }}` only (not `{{ .ConfirmationURL }}`); template configuration documented in §7

### FR-4 — Telegram code verify via `verify_otp({email, token, type})`
**Description**: When `signup_state='code_sent'` and incoming free-text matches `^[0-9]{6}$`, backend calls `client.auth.verify_otp({email, token, type:"email"})`. On `INVALID`: increment `attempts`; if `attempts >= 3` within 1 hour, rate-limit per D10. On `VALID`: proceed to FR-5.

**Acceptance** (AC-4):
- AC-4.1: invalid code increments `attempts`; Nikita reply: "Not right. {N} tries left."
- AC-4.2: 3 invalid attempts within 1h triggers rate-limit message + `signup_state` reset to `AWAITING_EMAIL`
- AC-4.3: expired code (now > expires_at) triggers Nikita-voiced "Code expired. Send /start to retry." + row purge
- AC-4.4: valid code response proceeds to FR-5 atomically

### FR-5 — Backend mints magic-link via `admin.generate_link`; bot delivers via Telegram with link-preview disabled
**Description**: After FR-4 success, backend calls `client.auth.admin.generate_link({type:"magiclink", email, options:{redirect_to:"<portal>/auth/confirm?next=/onboarding"}})`. Supabase returns `{action_link, hashed_token, verification_type, ...}`. **No second email is dispatched** — confirmed by Plan §21 spike against prod Supabase. Backend stores `magic_link_token=hashed_token`, `magic_link_sent_at=now`, `signup_state='magic_link_sent'`, `verification_type=<response value>`. Bot sends `action_link` to Telegram via inline URL button with **`disable_web_page_preview=True`** (PR-blocker — see §5 NFR-Sec-1).

**Acceptance** (AC-5):
- AC-5.1: `admin.generate_link` is called with `type="magiclink"` AND `options.redirect_to` is the portal `/auth/confirm?next=/onboarding` URL
- AC-5.2: `verification_type` from response is persisted on the row (used in FR-6 lookup); test asserts no hardcoded `"magiclink"` literal in handler code (regression guard against §21 refinement)
- AC-5.3: Telegram message uses `send_message(..., disable_web_page_preview=True)`. Phase E test simulates a Telegram link-preview crawler `GET` against `action_link` and asserts the user can still consume the token (single-use semantics not pre-burned)
- AC-5.4: Nikita reply text is in-character ("You're cleared. Tap to enter.") + button label is "Enter portal"
- AC-5.5: bind `public.users.telegram_id = <telegram_id>` is idempotent (re-runs OK); row created via FR-11b 307 auto-provision pathway if absent

### FR-6 — Portal `/auth/confirm` route + IS-A always-interstitial
**Description**: NEW route `portal/src/app/auth/confirm/route.ts` (server route handler) reads `?token_hash`, `?type`, `?next` from URL. Calls `supabase.auth.verifyOtp({token_hash, type})` server-side via `createServerClient` (`@supabase/ssr` cookies adapter per Next.js 16 App Router pattern). On error: redirect to `/login?error=<code>`. On success: render IS-A always-interstitial component (NOT raw 302). Interstitial has primary "Enter the portal" button (router.push next), Nikita-voiced copy, and optional "Open in Safari" Universal Link (iOS IAB escape per Plan §18.3).

**Acceptance** (AC-6):
- AC-6.1: `/auth/confirm` GET with valid `token_hash + type + next` calls `verifyOtp({token_hash, type})` and sets cookies on response
- AC-6.2: invalid/missing params → redirect `/login?error=missing_params` (no crash)
- AC-6.3: expired token_hash → redirect `/login?error=link_expired` with Nikita-voiced error state
- AC-6.4: success path renders interstitial UNCONDITIONALLY (no UA detection branch); interstitial requires user gesture to advance (Apple SFSafariViewController self-contained-session mitigation, plan §18.3 Approach IS-A)
- AC-6.5: interstitial includes "Open in Safari" Universal Link visible iff `navigator.userAgent` matches IAB pattern (Telegram in-app browser detection)
- AC-6.6: Phase E browser test verifies session cookie present on redirected `/onboarding` request

### FR-7 — Wizard entry (delegates to Spec 214 FR-11d)
**Description**: After interstitial advance to `/onboarding`, control transfers to Spec 214 FR-11d chat-first wizard. Spec 215 contributes nothing further to wizard internals; wizard's `getUser()` precondition is now reliably satisfied because Spec 215 minted the session.

**Acceptance** (AC-7):
- AC-7.1: `/onboarding` route's existing `getUser()` check passes immediately after `/auth/confirm` advance (no race)
- AC-7.2: Spec 214 FR-11d wizard mounts; no Spec 215 code reaches into wizard internals

### FR-8 — Wizard completion → ClearanceGrantedCeremony renders link_code (synchronous tap gate)
**Description**: Wizard completion fires existing FR-11b ceremony with `t.me/Nikita_my_bot?start=<LINK_CODE>`. Per D1 (plan §18.6 Option C2): the link_code retains its role as a SYNCHRONOUS user-tap gate confirming "user is ready to play". Because `telegram_id` was bound during signup (FR-5), the `/start <CODE>` handler's `update_telegram_id` becomes an idempotent no-op — semantics unchanged from existing FR-11b code path.

**Acceptance** (AC-8):
- AC-8.1: ceremony renders the `t.me/Nikita_my_bot?start=<LINK_CODE>` URL (existing FR-11b)
- AC-8.2: when user taps and `telegram_id` is already bound (signup phase), `update_telegram_id` is no-op (idempotent UPDATE..RETURNING with guard)
- AC-8.3: `claim_handoff_intent` still fires; greeting dispatch unchanged

### FR-9 — `_dispatch_handoff_greeting` fires on `/start <CODE>` consumption
**Description**: Existing FR-11b/c path. `_dispatch_handoff_greeting` fires from BackgroundTasks. S2 (per §20): the greeting + first 3 turns of conversation include a proactive proposal to set up a phone call.

**Acceptance** (AC-9):
- AC-9.1: greeting dispatched within 5 seconds of `/start <CODE>` consumption
- AC-9.2: phone-call proposal appears in one of the first 3 Nikita turns (S2)

### FR-10 — Returning-user portal `/login` redesigned Nikita-voiced (link-only template)
**Description**: `portal/src/app/login/page-client.tsx` redesigned with Nikita-voiced copy. Magic-link flow only (`signInWithOtp` with `emailRedirectTo=/auth/confirm?next=/dashboard`). Email template is **link-only** (different from FR-3's code-only signup template) — see `docs-to-process/20260423-auth-templates-v17-1.md` §1.2.

**Acceptance** (AC-10):
- AC-10.1: `/login` UI matches landing aesthetic (no generic SaaS form)
- AC-10.2: copy is Nikita-voiced (no "Welcome back!" sterile greeting)
- AC-10.3: `signInWithOtp` is called with `emailRedirectTo` pointing to `/auth/confirm?next=/dashboard`
- AC-10.4: Supabase magic-link email template (login context) renders `{{ .ConfirmationURL }}` only (no `{{ .Token }}`)
- AC-10.5: error states show Nikita-voiced messages (not `?error=auth_callback_failed` cold page)

### FR-11 — Landing nav: visible "Sign in" + "Continue with Nikita" entries (D3)
**Description**: `landing-nav.tsx` adds two visible entries beyond the primary CTA:
- "Sign in" (always visible) → `/login` (returning users)
- "Continue with Nikita" (visible iff auth'd + onboarded) → Telegram deep-link

**Acceptance** (AC-11):
- AC-11.1: anon users see primary CTA (Telegram) + "Sign in" link
- AC-11.2: auth'd-onboarded users see "Continue with Nikita" → Telegram deep-link AND avatar/dashboard entry
- AC-11.3: auth'd-not-onboarded users see CTA → /onboarding (resume)

### FR-12 — Wizard slot: "preferred call window" (S2 — early phone-call proposal)
**Description**: Spec 214 FR-11d wizard adds one new slot: `preferred_call_window` (free-text, optional). Persisted to `user_profiles`. Used by S2 (FR-13) to ground Nikita's call-scheduling proposal.

**Acceptance** (AC-12):
- AC-12.1: `WizardSlots` Pydantic model adds `preferred_call_window: Optional[str]`
- AC-12.2: cumulative-state monotonicity test (per `.claude/rules/testing.md` Agentic-Flow Test Requirements) covers the new slot
- AC-12.3: `user_profiles` schema migration adds `preferred_call_window text NULL`
- AC-12.4: wizard agent's dynamic instructions include the new slot in `state.missing` injection

### FR-13 — Post-handoff: bot proactively proposes phone call within first 3 turns (S2)
**Description**: After FR-9 greeting fires, the next 3 turns of Telegram conversation include a Nikita-voiced proposal to schedule a phone call, grounded in `user_profiles.preferred_call_window` if populated.

**Acceptance** (AC-13):
- AC-13.1: text-agent persona/prompt update includes a "propose-phone-call" template fragment that fires for users with `chapter=1 AND telegram_handoff_at IS NOT NULL AND turns_since_handoff <= 3`
- AC-13.2: proposal copy is in-character (no SaaS scheduling-link UX)

### FR-14 — ClearanceGrantedCeremony copy adds portal-orientation teaching (S3)
**Description**: ClearanceGrantedCeremony component (Spec 214) adds the line: "Bookmark this portal — your dashboard, history, and Nikita's daily highlights live here." Wizard's final Nikita turn echoes a similar bookmark prompt.

**Acceptance** (AC-14):
- AC-14.1: visual snapshot test of ceremony component asserts new copy line present
- AC-14.2: wizard's terminal-turn message includes the bookmark phrasing
- AC-14.3: copy passes Nikita-voice review (no SaaS-tone "Don't forget to bookmark!")

### FR-15 — Email change flow (DEFERRED to Spec 215 v2)
**Description**: Mid-funnel email change is deferred. v1 escape hatch: user contacts support (`support@nikita-mygirl.com`) OR user issues `/start` in Telegram which triggers a destructive reset of `telegram_signup_sessions` (delete pending row → start over with new email at FR-2). User-facing copy in FR-2 will mention "send /start to start over."

**Acceptance** (AC-15):
- AC-15.1: spec body explicitly documents the v1 escape hatch
- AC-15.2: Telegram `/start` handler for users in `signup_state IN (AWAITING_EMAIL, CODE_SENT, MAGIC_LINK_SENT)` does destructive reset (delete row, restart at FR-2)

### FR-16 — Edge cases T-E1 through T-E30 (consolidated from Plan §17.2)

| # | Edge case | Target behavior | Coverage status |
|---|---|---|---|
| T-E1 | Anon clicks landing CTA | → Telegram deep-link `?start=welcome` | FR-1 |
| T-E2 | User sends invalid email format to bot | Regex reject; Nikita-voiced message | FR-2 |
| T-E3 | User sends email typo (`gmial.com`) | D8 post-failure inline "Change email" button (no preemptive list) | FR-2 + signup_handler |
| T-E4 | User sends correct 6-digit code | verifyOtp → mint magic-link → Telegram delivery | FR-4, FR-5 |
| T-E5 | User sends wrong code (1-2 attempts) | Nikita: "Not right. {N} tries left." | FR-4 |
| T-E6 | User sends wrong code (3+ within 1h) | Rate-limit; reset to AWAITING_EMAIL | FR-4, D10 |
| T-E7 | User sends code after 5min expiry | Nikita: "Code expired. Send /start to retry." + row purge | FR-4 |
| T-E8 | User abandons after email, returns 10min later | `/start` finds CODE_SENT state → "Send your code or /start to restart." | FR-15, signup_handler |
| T-E9 | User abandons after magic-link, returns 1h later | `/login` re-issues magic-link OR Nikita-voiced re-entry via Telegram FSM | FR-10, FR-15 |
| T-E10 | Email already bound to DIFFERENT telegram_id | "That email is already linked. Contact support." (no v1 self-service) | FR-15 (escape hatch) |
| T-E10b | pending_registration row in `code_sent` but expired | Auto-purge via pg_cron + restart | FR-4 + cron |
| T-E11 | Same email + same telegram_id (re-signup attempt) | Skip code; mint magic-link directly (idempotent) | FR-5 idempotency |
| T-E12 | User completes wizard, never taps CTA | link_code expires (10min); manual re-mint OR D11 reset | FR-8 (existing) |
| T-E13 | User already onboarded, clicks landing CTA | → /dashboard | FR-11 (D3) |
| T-E14 | User cleared cookies, clicks landing CTA | → Telegram (anon) OR /login (returning) | FR-1, FR-11 |
| T-E15 | Returning user wants portal login | `/login` Nikita-voiced + magic-link | FR-10 |
| T-E16 | User has telegram_id bound, no portal session | FR-11c E5/E6 resume bridge (existing) | unchanged |
| T-E17 | User types `/start` in Telegram after onboarded | E2 welcome (existing FR-11c) | unchanged |
| T-E18 | User types `/start` mid-onboarding (in MAGIC_LINK_SENT state) | "Continue by checking email for code." OR destructive reset | FR-15 |
| T-E19 | User sends email-shaped string in Telegram after onboarded | Nikita responds in-character; no signup re-trigger | signup_handler guard |
| T-E22 | Magic-link clicked after TTL | `/auth/confirm` error → Nikita-voiced "Link expired. Send /start in Telegram." | FR-6 |
| T-E23 | Magic-link clicked twice | Idempotent — Supabase returns existing session; redirect wizard or /dashboard | FR-6 |
| T-E24 | Magic-link clicked on different device (no cookies) | New session minted; lands on wizard | FR-6 |
| T-E25 | Telegram link-preview crawler GET burns token | MITIGATED: `disable_web_page_preview=True` | FR-5, NFR-Sec-1 |
| T-E26 | iOS Safari ITP / Telegram IAB session strand | MITIGATED: IS-A always-interstitial | FR-6 |
| T-E27 | Token replay (user shares Telegram message screenshot) | Single-use token; second click → expired-link interstitial | FR-6 |
| T-E28 | PKCE 422 (GH #393) reproduction | ELIMINATED: `verifyOtp({token_hash, type})` is non-PKCE | FR-6, §11 |
| T-E29 | Vercel cache of deleted `/onboarding/auth` route | T-deploy cache purge after PR-F2b merge | §9 Migration |
| T-E30 | Game-over re-email path | Skip OTP; mint magic-link directly (auth.users row exists) | D7, FR-10 variant |

---

## §5 Non-functional requirements

### NFR-Sec-1 (PR-blocker) — `disable_web_page_preview=True` on every Telegram message containing magic-link
Telegram's link-preview crawler will GET the action_link to render an embed, burning the single-use token before the user can tap. Bot MUST set `disable_web_page_preview=True` on the `send_message` call. Phase E test simulates the crawler `GET` and asserts subsequent user-tap still consumes the token successfully.

### NFR-Sec-2 — IS-A always-interstitial unconditional (no UA branch)
Apple SFSafariViewController is self-contained per Apple docs; cookies set inside Telegram in-app browser do not persist into Safari.app. The interstitial requires user gesture to advance, which preserves cookies. ~150 LOC component lands in PR-F2a (per Plan §18.4).

### NFR-Sec-3 — No PII in logs
Per existing `.claude/rules/testing.md` Pre-PR Grep Gates + GH #284: do not log raw email values, raw OTP codes, raw `magic_link_token`. Use `email_hash = sha256(email)[:12]` or `telegram_id` only. Pre-PR grep gate (#2) enforces.

### NFR-Sec-4 — Rate limits (D10)
- 10 emails sent per hour per telegram_id (resend cooldown 60s)
- 15 OTP codes verified per hour per email
- Code TTL 5 minutes (purged via pg_cron)
- Magic-link TTL: Supabase default (1h), single-use

### NFR-Sec-5 — Session lifetime
- Access token: Supabase default 1h (tunable 5m–1h)
- Refresh token: never-expires by default (single-use)
- Middleware MUST call `getUser()` to trigger refresh-token exchange (NEVER `getSession()` per Supabase Next.js 16 SSR guide). Existing `portal/src/lib/supabase/middleware.ts:40` does this correctly; preserved.

### NFR-Acc-1 — Accessibility / Nikita-voiced error states
All error states (`/login?error=…`, interstitial fallback, Telegram message rejections) maintain the Nikita-voice tone. No generic "Auth Error" or "Something went wrong" copy. Phase E checklist explicitly verifies copy review pass.

### NFR-Perf-1 — Latency budget
End-to-end signup (CTA tap → wizard entry) targets t < 30s P50, t < 60s P95 (Plan §18.10 Diagram 3). Telemetry events per FR-Telemetry-1 enable funnel monitoring.

### FR-Telemetry-1 — Signup funnel events
Add to `nikita/monitoring/events.py` (per Plan §17.6):
- `signup_started_telegram` (telegram_id, ts)
- `signup_email_received` (telegram_id, email_hash, ts)
- `signup_code_sent` (email_hash, ts, supabase_response_code)
- `signup_code_verified` (email_hash, attempts_count, ts)
- `signup_magic_link_minted` (email_hash, ts, action_link_ttl, verification_type)
- `signup_magic_link_clicked` (email_hash, ts, latency_ms_from_mint)
- `signup_wizard_session_minted` (user_id, ts)
- `signup_wizard_completed` (user_id, ts, total_signup_to_complete_ms)
- `signup_failed` (telegram_id, stage, reason)

---

## §6 Acceptance Criteria Summary

| AC | Mapped FR | Falsifiable assertion |
|---|---|---|
| AC-1.1..AC-1.3 | FR-1 | Landing CTAs route per branch |
| AC-2.1..AC-2.3 | FR-2 | Email collection state transitions correct |
| AC-3.1..AC-3.4 | FR-3 | OTP send + signup template + 5min TTL |
| AC-4.1..AC-4.4 | FR-4 | Code verify + rate-limit + expiry |
| AC-5.1..AC-5.5 | FR-5 | generate_link + verification_type passthrough + disable_web_page_preview + idempotent bind |
| AC-6.1..AC-6.6 | FR-6 | /auth/confirm route + IS-A interstitial + cookie persistence |
| AC-7.1..AC-7.2 | FR-7 | Wizard entry handoff |
| AC-8.1..AC-8.3 | FR-8 | Ceremony link_code synchronous gate; idempotent telegram_id |
| AC-9.1..AC-9.2 | FR-9 | Greeting dispatch + S2 phone-call proposal |
| AC-10.1..AC-10.5 | FR-10 | /login Nikita-voiced + link-only template |
| AC-11.1..AC-11.3 | FR-11 | Nav dual entries |
| AC-12.1..AC-12.4 | FR-12 | Wizard slot preferred_call_window |
| AC-13.1..AC-13.2 | FR-13 | Post-handoff phone-call proposal |
| AC-14.1..AC-14.3 | FR-14 | Ceremony portal-orientation copy |
| AC-15.1..AC-15.2 | FR-15 | Email change escape hatch documented + destructive reset works |
| AC-CodeOnlyTemplate | FR-3 | Supabase signup template renders `{{ .Token }}` ONLY (no link) — verify via dashboard inspection + Phase E live email |
| AC-LinkOnlyTemplate | FR-10 | Supabase magic-link (login) template renders `{{ .ConfirmationURL }}` ONLY (no token) |
| AC-LegacyDelete | §9 | `nikita/platforms/telegram/registration_handler.py` and `otp_handler.py` removed; `auth_bridge_tokens` table dropped (count=0 verified Plan §18.9) |
| AC-PKCEGone | T-E28 | Repro test for GH #393 cannot reproduce on `/auth/confirm` path (non-PKCE verifyOtp) |
| AC-LiveWalk | all | Spec 215 implementation passes a Phase F W1 dogfood walk per `.claude/rules/live-testing-protocol.md` (12-step canonical protocol; NO DB fabrication; Telegram MCP + Gmail MCP + agent-browser only) |

---

## §7 Architecture

### §7.1 New / changed files

**NEW**:
- `nikita/platforms/telegram/signup_handler.py` — consolidated FSM (handle_welcome, handle_email, handle_code; replaces legacy registration_handler + otp_handler)
- `nikita/api/routes/portal_auth.py::generate_magiclink_for_telegram_user` — admin endpoint (service-role only) invoked by signup_handler after FR-4 success
- `portal/src/app/auth/confirm/route.ts` — server route handler (GET) calling `verifyOtp({token_hash, type})`
- `portal/src/app/auth/confirm/interstitial.tsx` — IS-A always-interstitial Client Component (~150 LOC)
- `supabase/migrations/<NNN>_rename_pending_registrations_to_telegram_signup_sessions.sql` — table rename + new columns
- `supabase/migrations/<NNN>_drop_auth_bridge_tokens.sql` — drop legacy table (count=0)
- `supabase/migrations/<NNN>_add_preferred_call_window_to_user_profiles.sql` — FR-12

**MODIFIED**:
- `portal/src/components/landing/{hero-section,cta-section,landing-nav}.tsx` — anon CTA → Telegram URL; nav adds "Sign in" + "Continue with Nikita"
- `portal/src/app/login/page-client.tsx` — Nikita-voiced redesign; emailRedirectTo → `/auth/confirm`
- `portal/src/lib/supabase/middleware.ts` — remove `/onboarding/auth` exemption; add `/auth/confirm` exemption
- `nikita/api/routes/telegram.py` — webhook routes email/code messages to signup_handler (replaces registration_handler/otp_handler wiring)
- `nikita/db/models/pending_registration.py` → renamed `telegram_signup_session.py` — add `signup_state` enum, `magic_link_token`, `magic_link_sent_at`, `attempts`, `last_attempt_at`, `verification_type`
- `nikita/db/repositories/pending_registration_repository.py` → renamed; CRUD + atomic verify + 3-strike rate-limit
- `nikita/agents/onboarding/wizard_slots.py` — add `preferred_call_window` slot (FR-12)
- `nikita/agents/text/persona.py` or template — add S2 phone-call proposal fragment (FR-13)
- `portal/src/components/onboarding/ClearanceGrantedCeremony.tsx` — add S3 portal-orientation copy
- `nikita/monitoring/events.py` — add 9 signup funnel events

**DELETED** (PR-F3 per Plan §18.4):
- `portal/src/app/onboarding/auth/` route (entire directory)
- `nikita/platforms/telegram/auth.py:61-141` (`register_user`, `verify_otp` deprecated methods)
- `nikita/platforms/telegram/registration_handler.py`
- `nikita/platforms/telegram/otp_handler.py`
- `nikita/db/models/auth_bridge.py` + `nikita/api/routes/auth_bridge.py` + `auth_bridge_repository.py` + `auth_bridge_tokens` table
- `portal/src/components/onboarding/onboarding-wizard-legacy.tsx` + `onboarding/steps/legacy/` + `onboarding/components/legacy/` (D4 confirmed: `NEXT_PUBLIC_USE_LEGACY_FORM_WIZARD` UNSET in all Vercel envs per Plan §22)
- Dual `generate_portal_bridge_url` in `utils.py` (collapse to `onboarding/bridge_tokens.py`; GH #233 finally closed)
- `_send_bare_portal_auth_link` in commands.py:408-429 (or repurpose for T-E30)
- `/onboard` slash-command + handler (commands.py:198) + help-text reference (commands.py:643)

### §7.2 Data model

**`telegram_signup_sessions`** (renamed from `pending_registrations`):

| Column | Type | Notes |
|---|---|---|
| id | uuid PK | gen_random_uuid() |
| telegram_id | bigint | INDEX; FK to public.users.telegram_id (nullable until bind) |
| email | text | INDEX |
| signup_state | text CHECK IN ('awaiting_email','code_sent','magic_link_sent','completed') | NOT NULL |
| magic_link_token | text | hashed_token from generate_link response; NULL until FR-5 |
| magic_link_sent_at | timestamptz | NULL until FR-5 |
| verification_type | text CHECK IN ('email','signup','magiclink','recovery') | persisted from generate_link response per §21 |
| attempts | int DEFAULT 0 | OTP verify attempts |
| last_attempt_at | timestamptz | for rate-limit windowing |
| created_at | timestamptz DEFAULT now() | |
| expires_at | timestamptz | code TTL 5min from created_at |
| RLS | service-role only | no end-user access |

**Migration ops**:
1. RENAME TABLE pending_registrations TO telegram_signup_sessions
2. ADD COLUMN signup_state, magic_link_token, magic_link_sent_at, verification_type, attempts, last_attempt_at
3. Backfill existing 5 dev rows: signup_state='awaiting_email' (will be destructively reset per D6)
4. ENABLE RLS + service-role-only policy (per `.claude/rules/testing.md` DB Migration Checklist)

### §7.3 State machine (FSM)

```
[UNKNOWN]
   │ /start welcome (no telegram_id binding)
   ▼
[AWAITING_EMAIL]
   │ valid email
   ▼
[CODE_SENT]
   │ valid code           ┌────────────────────┐
   ├─────────────────────▶│  rate-limit reset  │ ← 3 invalid in 1h
   │ invalid code (<3)    └────────────────────┘
   │ ↻ (attempts++)
   │ expired              → AWAITING_EMAIL (purge)
   ▼
[MAGIC_LINK_SENT]
   │ user taps link in browser
   │ /auth/confirm verifies
   ▼
[COMPLETED]
   (telegram_signup_sessions row deleted; user fully bound)
```

Refer to Plan §18.10 Diagram 2 (Telegram-first signup FSM) for visual.

### §7.4 Supabase Email Templates (dashboard config)

Per Plan §6.3 + Plan §18.8 documentation:

| Template | Purpose | Fires for | Body content |
|---|---|---|---|
| **Signup** (FR-3) | Telegram-first OTP code | `sign_in_with_otp({email, options:{should_create_user:True}})` for NEW email | `{{ .Token }}` only (6-digit code; new HTML in `docs-to-process/20260423-auth-templates-v17-1.md` §1.1) |
| **Magic Link** (FR-10) | Returning-user portal login | `signInWithOtp` from `/login` page | `{{ .ConfirmationURL }}` only (link-only; new HTML in §1.2) |
| Recovery / Invite / Email Change | unused in v1 | — | leave Supabase default |

Both templates documented in `docs/deployment.md` Supabase Email Templates section (added in Phase E).

### §7.5 ADR

`~/.claude/ecosystem-spec/decisions/ADR-010-telegram-first-signup-direction.md` is the architectural authority. Cited throughout this spec.

---

## §8 Test strategy

Test pyramid: 70% unit, 20% integration, 10% E2E.

### §8.1 Unit (70%) — pytest + vitest

**Backend**:
- `tests/platforms/telegram/test_signup_handler.py` — FSM state transitions per FR-2/3/4; rate-limit per D10; expired-code purge
- `tests/db/repositories/test_telegram_signup_session_repository.py` — atomic verify, idempotent bind
- `tests/api/routes/test_portal_auth_generate_magiclink.py` — admin endpoint contract; service-role guard

**Portal**:
- `portal/tests/app/auth/confirm/route.test.ts` — verifyOtp wiring, error redirects, missing-params handling
- `portal/tests/app/auth/confirm/interstitial.test.tsx` — IS-A unconditional render, IAB UA detection, Universal Link href
- `portal/tests/app/login/page-client.test.tsx` — Nikita-voiced copy, emailRedirectTo wiring
- `portal/tests/components/landing/cta-href.test.tsx` — anon CTA = Telegram URL across all 3 components

### §8.2 Integration (20%)

- `tests/integration/test_signup_flow_e2e.py` — full FSM with mocked Supabase admin client (covers AC-3 through AC-5 end-to-end)
- `tests/integration/test_auth_confirm_session.py` — verifyOtp + cookie set + middleware getUser pickup

### §8.3 E2E (10%) — Phase F per `.claude/rules/live-testing-protocol.md`

12-step canonical protocol (NO DB fabrication; Telegram MCP + Gmail MCP + agent-browser only). Walk W1 acceptance: 0 CRITICAL findings, 0 unfiled HIGH, all FR-Telemetry-1 events fire correctly, plus AC-LiveWalk.

### §8.4 Mandatory Agentic-Flow Tests

Per `.claude/rules/agentic-design-patterns.md` + `.claude/rules/testing.md` Agentic-Flow Test Requirements: any code under `tests/agents/**` touching the wizard slot model (FR-12) MUST include:

1. Cumulative-state monotonicity test (≥3 turns, asserts `progress_pct[t+1] >= progress_pct[t]` after preferred_call_window slot lands)
2. Completion-gate triplet (empty/partial/full FinalForm validation)
3. Mock-LLM-emits-wrong-tool recovery (slot extraction fallback for preferred_call_window)

### §8.5 Pre-PR Grep Gates

Per `.claude/rules/testing.md`: zero-assertion shells, PII format strings, raw cache_key. All MUST return empty before `/qa-review` dispatch.

### §8.6 Live-Dogfood Anti-Patterns (PR-blockers)

Per `.claude/rules/live-testing-protocol.md`: no `INSERT INTO auth.users`, no `signInWithPassword`, no `E2E_AUTH_BYPASS=true`, no custom JWT minting. Walk Y precedent (#410, #411 — synthetic findings) drove this rule.

---

## §9 Migration

### §9.1 Schema migrations (sequential, in PR-F1a)

1. RENAME `pending_registrations` → `telegram_signup_sessions`
2. ADD COLUMN signup_state, magic_link_token, magic_link_sent_at, verification_type, attempts, last_attempt_at
3. ENABLE RLS + service-role-only CREATE POLICY
4. NEW migration: ADD COLUMN preferred_call_window text NULL ON user_profiles
5. NEW migration (PR-F3 only): DROP TABLE auth_bridge_tokens (verified count=0 in Plan §18.9)

### §9.2 Destructive reset of in-flight users (D6)

Per Plan §18.5 verification 2 + §19: 5 in-flight `pending` users in prod, all dev accounts (no telegram_id, oldest 2026-04-21). Destructive reset SQL (one-shot, run post-PR-F1a deploy):

```sql
DELETE FROM telegram_signup_sessions WHERE telegram_id IS NULL;
DELETE FROM public.users WHERE onboarding_status = 'pending' AND telegram_id IS NULL;
-- auth.users rows: leave for self-cleanup OR delete if zero risk
```

### §9.3 Vercel env flag removal (D4)

Per Plan §22: `NEXT_PUBLIC_USE_LEGACY_FORM_WIZARD` confirmed UNSET across all Vercel envs. Safe to delete legacy components in PR-F3. No env-var removal needed (already absent).

### §9.4 Cache purge (T-E29)

After PR-F2b merge (deletion of `/onboarding/auth`), Vercel cache MUST be purged so the route returns 404. Phase E checklist item.

### §9.5 Feature-flag gate (per Plan §18.4)

PRs F1a/F1b/F2a/F2b ship behind `NEXT_PUBLIC_TELEGRAM_FIRST_SIGNUP=true`. Flag flips ON only after Phase F W1 dogfood passes. PR-F3 deletion waits for 1 deploy cycle behind flipped flag (rollback safety).

---

## §10 Risks

Lifted from Plan §10 + §18.3:

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Telegram link-preview crawler burns single-use token | Medium | High | `disable_web_page_preview=True` (NFR-Sec-1, AC-5.3) + Phase E crawler-simulation test |
| iOS Safari ITP / Telegram IAB session strand | Medium | High | IS-A always-interstitial unconditional (FR-6, NFR-Sec-2) |
| Token replay via Telegram message screenshot share | Low | Medium | Single-use token; expired-link interstitial (T-E27) |
| Email template misconfigured | Medium | High | §7.4 documents both dashboard configs; AC-CodeOnlyTemplate + AC-LinkOnlyTemplate verify in Phase E live walk |
| `verifyOtp({type:'magiclink', token_hash})` deprecated in some Python versions | Low | Medium | Plan §21 spike confirmed supabase-py 2.24.0 supports both 'email' and 'magiclink'; use response `verification_type` (no normalize) |
| Supabase rate-limit collision with prod (360 OTP/hr/project shared) | Medium | Low | Plus-alias rotation (`+walkN`) per walk; staging Supabase optional |
| Vercel cache of deleted `/onboarding/auth` route | Low | Medium | T-E29 cache purge in Phase E checklist |
| PKCE 422 (#393) regression in `/auth/confirm` path | Low | High | Token-hash flow eliminates PKCE entirely; AC-PKCEGone repro test |
| Dropping `auth_bridge_tokens` breaks rollback | Low | Medium | PR-F3 sequential to PR-F1/F2; 1 deploy cycle behind flipped flag |
| Wizard slot addition (FR-12) breaks FR-11d cumulative state | Low | High | Agentic-Flow Test Requirements §8.4 cumulative-state monotonicity covers it |
| Walk subagent fabricates DB state | Medium | High | `.claude/rules/live-testing-protocol.md` PR-blocker anti-patterns + ADR-011 |

---

## §11 References

- **Plan**: `~/.claude/plans/delightful-orbiting-ladybug.md` (v17.1) — §1, §2.4, §3, §4, §5, §6, §7 (approach evaluation), §8 (phase structure), §9 (live testing protocol — now `.claude/rules/live-testing-protocol.md`), §10, §15, §17, §18, §19, §20, §21, §22
- **ADRs**:
  - `~/.claude/ecosystem-spec/decisions/ADR-010-telegram-first-signup-direction.md`
  - `~/.claude/ecosystem-spec/decisions/ADR-011-live-testing-protocol-as-rule.md`
  - `~/.claude/ecosystem-spec/decisions/ADR-009-agentic-design-patterns.md` (Spec 214 antecedent)
- **Project rules**:
  - `.claude/rules/agentic-design-patterns.md` — wizard slot FR-12 must follow these patterns
  - `.claude/rules/live-testing-protocol.md` — Phase F dogfood discipline (PR-blocker anti-patterns)
  - `.claude/rules/testing.md` — Agentic-Flow Test Requirements + Pre-PR Grep Gates + DB Migration Checklist
  - `.claude/rules/pr-workflow.md` — TDD + Pre-push HARD GATE + grep-verify gate + commit-hash verification
  - `.claude/rules/parallel-agents.md` — subagent dispatch caps (HARD CAP + scope + exit criterion)
  - `.claude/rules/vercel-cors-canonical.md` — pre-CORS check before any cors_origins edit
- **Supabase docs**:
  - https://supabase.com/docs/guides/auth/auth-email-passwordless
  - https://supabase.com/docs/guides/auth/server-side/nextjs (Next.js 16 App Router cookies adapter)
  - https://supabase.com/docs/reference/javascript/auth-verifyotp
  - https://supabase.com/docs/reference/javascript/auth-admin-generatelink
- **Telegram docs**:
  - https://core.telegram.org/bots/features#deep-linking (`?start=` payload, 64 chars, charset `[A-Za-z0-9_-]`)
  - https://core.telegram.org/bots/api#sendmessage (`disable_web_page_preview` field)
- **Sister specs**:
  - Spec 214 (post-auth wizard) — references Spec 215 as entry precondition
  - Spec 208 (landing page) — anon CTA target amended per FR-1
  - Spec 213 (onboarding backend foundation) — FR-11b 307 auto-provision pattern reused
- **Auth template content**: `docs-to-process/20260423-auth-templates-v17-1.md` (referenced in plan §19; physical file pending — content embedded in Plan §17.1 + §18.2)
- **Phase B.5 governance ship**: PR #412 commit `0a3534e` (live-testing-protocol rule + testing.md cross-link)
- **Live spike evidence (Plan §21)**: subagent `aa80290cd3209c57f`; probe email `simon.yang.ch+v17probe-001@gmail.com`; Supabase response `verification_type='signup'` for new email; supabase-py 2.24.0 native support for `admin.generate_link` confirmed
- **Six supporting diagrams** (Plan §18.10): produced by review agent `a0827ffa586d754ce`; copy into `docs/diagrams/onboarding-journey-v17.md` during Phase D

---

## §12 Open questions [NEEDS CLARIFICATION]

NONE.

All decisions D1 through D13 + scope items S1 through S4 are resolved per Plan §19, §19.1, and §20:
- D1 (link_code semantics): synchronous user-tap gate (FR-8 / Option C2)
- D2 (email templates): code-only signup template (FR-3) + link-only login template (FR-10)
- D3 (onboarded landing CTA): /dashboard + nav dual entries (FR-11)
- D4 (legacy flag): `NEXT_PUBLIC_USE_LEGACY_FORM_WIZARD` UNSET → safe deletion (PR-F3)
- D5/D13 (Spec 215 scope): full auth ownership (this spec)
- D6 (in-flight reset): destructive reset of 5 dev rows (§9.2)
- D7 (game-over re-email): skip OTP, mint magic-link directly
- D8 (typo affordance): post-failure inline button (T-E3)
- D9 (mid-wizard drop): keep portal resume bridge (FR-11c E5/E6, unchanged)
- D10 (rate limits): 10 emails/hr, 15 codes/hr, 60s resend, 5min code TTL (NFR-Sec-4)
- D11 (game-over backstory preservation): preserve user_profiles + backstory_cache; clear user_metrics only
- D12 (Telegram LoginUrl): REJECTED for v1
- S1 (Nikita initiates post-handoff): covered by FR-9 + Phase F W1 AC-LiveWalk
- S2 (early phone-call proposal): FR-12 + FR-13
- S3 (portal orientation teaching): FR-14
- S4 (daily engagement emails): MOVED to Spec 216 (separate spec lifecycle)

Phase B is COMPLETE per Plan §19.1. Pre-Phase-C verification 1 (Supabase admin.generate_link spike) PASSED per Plan §21.

---

**End Spec 215 — auth-flow-redesign DRAFT v1**
