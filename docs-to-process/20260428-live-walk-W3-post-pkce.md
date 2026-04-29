# Walk W3 — Post-PKCE Live Battle Test (Spec 215 + Spec 214 v2 FR-11d)

**Date:** 2026-04-27 22:05–22:14 UTC
**Tester:** subagent (Telegram MCP + Chrome DevTools MCP + Supabase MCP + Gmail MCP)
**Environment:** production (apex `nikita-mygirl.com` + `nikita-api-1040094048579.us-central1.run.app`)
**Final verdict:** **FAIL** — multiple agentic-flow rule violations + PKCE fix path not exercised by deployed welcome flow

Tooling note: prompt referenced `mcp__claude-in-chrome__*` tools; this session only had `mcp__chrome-devtools__*` available. Substitution made per advisor (no functional gap).

---

## 1. Pre-walk gates

| Gate | Result |
|---|---|
| Vercel latest deployment | commit `b4e4be43` (>= baseline `8630442`) state=READY ✓ |
| Cloud Run revision | `nikita-api-00290-g9z` created `2026-04-26T00:06:28Z` (1.5h AFTER PR #438 commit `8630442` authored `2026-04-25T22:32:02Z`) ✓ |
| Master HEAD | `b4e4be4 fix(hooks): add hookEventName discriminator…` ✓ |
| Cleanup discovery: leftover `+pr438walk` rows | 0 ✓ |
| Cleanup discovery: telegram_signup_session for TG 746410893 | 0 ✓ |
| Telegram MCP session alive (`get_me`) | id=746410893, name="V.", username=`to5meo` ✓ |
| Chrome MCP available (`list_pages`) | ✓ (about:blank) |
| Simon's main account `simon.yang.ch@gmail.com` | id=`0a734aa6-656d-456f-9d33-ab5dc67fcbf3` (NOT touched) ✓ |
| Schema reality vs prompt | `nikita.conversation_jsonb` does NOT exist; wizard JSONB lives on `public.users.onboarding_profile` (jsonb). `user_vice_preferences` (plural) is the table. `telegram_signup_sessions` has `created_at` not `updated_at`. |

All preconditions for the walk: PASS. Note: the script's expected schema names diverge from reality, so cleanup SQL was adapted on the fly.

---

## 2. Step-by-step transcript

### Step 1 — `/start` to `@Nikita_my_bot`
- **User input (Telegram):** `/start`
- **Bot reply (msg 22327, 2026-04-27 22:05:30Z):** `"Hey V.. I don't think we've met.\n\nTap below to open the door."` + inline button.
- **Inline button:** text `"Meet her here"` → `url=https://nikita-mygirl.com/onboarding/auth` (NOT a Telegram-conversational email-collection prompt as the script expected).
- **DB state:** NO row in `telegram_signup_sessions` for telegram_id 746410893 (signup_state was never `awaiting_email`).

**SCRIPT MISMATCH:** prompt assumed Telegram-first conversational signup (bot asks for email IN CHAT); reality is Telegram serves as a deep-link launcher only — the bot's first message contains a `t.me`-style button to portal `/onboarding/auth`. The Telegram-side `awaiting_email` / OTP path may exist in code (Spec 215 PR-F1b) but is NOT what `/start` triggers in the deployed prod welcome flow.

### Step 2 — Email collection at `/onboarding/auth`
- **Page renders:** heading "I've been reading about you.", subheading "There's a door. Drop your address.", textbox + button "Open the door."
- **Vocab grep on page snapshot:** 0 matches for FILE/dossier/clearance/FIELD ✓
- **User input:** `simon.yang.ch+pr438walk@gmail.com`
- **Click "Open the door."** → button changes to "Knocking…", success card renders: `"Door sent to simon.yang.ch+pr438walk@gmail.com. Check your inbox. Link is good for an hour."` + 60s "Wait" cooldown + "Different address." button.
- **Toast:** `"She's sending you a way in. Check your inbox."`
- **Screenshot:** `walk-w3-step2-auth-page.png`

### Step 3 — Magic-link retrieval
- **Gmail MCP** `search_threads(newer_than:5m)` returned thread `19dd0fa95bd76dc9` from `onboarding@silent-agents.com` subject "Confirm Your Signup" delivered to `simon.yang.ch+pr438walk@gmail.com` at 2026-04-27T22:06:15Z.
- **Email body** (extracted via `get_thread`):
  - 8-digit code `35416794` ("Enter this code in Telegram to complete registration.")
  - "Confirm Email" button URL: `https://vlvlwmolfdpzdfmtipji.supabase.co/auth/v1/verify?token=pkce_64e0c5f79b700dac5dc73b9a6c1372c6e3154ae03fc3aa8e7a060e17&type=signup&redirect_to=https%3A%2F%2Fnikita-mygirl.com%2Fauth%2Fcallback%3Fnext%3D%252Fonboarding`

**Critical finding:** the email-delivered link is the **Supabase-hosted `auth/v1/verify`** form with `token=pkce_…&redirect_to=…/auth/callback?next=/onboarding`, **NOT** the portal `/auth/confirm?token_hash=…&type=…&next=/onboarding` form that PR #438 was supposed to deliver. PR #438's diff (`nikita/api/routes/portal_auth.py:158`+) only fixes the **Telegram-delivered** magic-link path (`generate_magiclink_for_telegram_user`) — the email-delivered Supabase template path was not touched. With the deployed welcome flow funneling everyone through portal-first email submission, **the PR #438 fix is unreachable from a default new-user signup**.

### Step 4 — Magic-link landing
- Navigated to the email's "Confirm Email" URL.
- **Final URL after redirects:** `https://nikita-mygirl.com/onboarding` (the Supabase verify endpoint 302'd back through `/auth/callback?next=/onboarding`, then forwarded to `/onboarding`).
- Title: `Get Started | Nikita`. Page renders with first wizard prompt.
- **Console errors:** 1 × 404 (likely Vercel insights asset), 1 × CSP/MIME-type warn for `_vercel/insights/script.js`. No auth-redirect loop, no hydration errors, no business-logic errors.
- **Auth state:** `auth.users` row created `2026-04-27T22:06:14Z` id=`e6c55f77-8d51-49ec-8a3d-a0d083160ace`.
- **NO IS-A interstitial visible** (script expected one; landed directly in wizard).
- F.1 idempotency (re-navigate same URL): not exercised — single-shot the link to avoid invalidating it.

### Step 5 — Wizard turns

| # | User input | Nikita reply (truncated) | progress_pct | DB extracted_kinds (cumulative) |
|---|---|---|---|---|
| 0 | (initial prompt) | "hey. where do i find you on a thursday night?" | 0 | [] |
| 1 | `Zürich` | "Zürich, nice — love that city. Okay so what's the scene…" | **16%** | [location] |
| 2 | `techno, low-key vibe tonight` | "ooh techno in Zürich… are you out at a club right now, or is this more of a pregame…?" | **16%** (no advance) | [location, vibe] |
| 3 | `at home, pre-club. feels like a 4 out of 10 darkness` | "ha, 4 out of 10 — still some lamps on… so who am I actually talking to right now — what's your name?" | **33%** | [location, vibe, scene] (note: NO `darkness` slot extracted — drug_tolerance=3 was set in user_profiles silently but never appears as a `kind` in `onboarding_profile.conversation`) |
| 4 (F.9 ambiguous-identity probe) | `simon` (no age, no occupation) | "**simonsimon** — double the name, double the trouble. love it. so what's the backstory, **simonsimon** — who are you beyond a techno fan…" | **50%** | [location, vibe, scene, identity] |
| 5 (first try, FAILED) | `i'm 32, designer. used to be all about gallery openings…` | "**hold on, let me try that again.**" — backend agent emitted `converse_reply_reject` (Cloud Run WARNING log at 22:10:32). | 50% | (no advance) |
| 5 (retry) | `designer, 32. been doing this a while.` | "that shift from curated to chaotic is real… before you head out tonight, what's the best number to reach you on?" | (FE remained 50% temporarily) | [location, vibe, scene, identity, backstory] |
| 6 | `text — +41 79 123 4567 ` (trailing space required to enable button) | "got it, text only — noted. alright Simon, I think I've got what I need to set things up for tonight. get ready to lose yourself out there. 🖤" | **66% then 83%** (after FE polled) | [location, vibe, scene, identity, backstory, phone] — 6 distinct kinds |

**FE Send-button bug** (independent of E.X): button only enables when input contains a trailing space character. Filling text alone is insufficient; user must type a space before button becomes interactive. Reproducible across turns 5 and 6.

**Screenshots:** `walk-w3-step5-wizard-turn0.png`, `walk-w3-step5-wizard-final.png`.

### Step 6 — Backstory + dashboard
- `backstory_cache` query for user_id (correct column is `cache_key`-based, not user_id-based; cache row scope is per-stratum not per-user): no row created in walk window.
- Wizard never reached 100% — terminal at 83%.
- Page did NOT auto-redirect to dashboard. Manual navigation to `/dashboard` required.
- Dashboard rendered: nav bar, "Welcome to Nikita's World" empty state, "Chat on Telegram" CTA. No score ring (user has no chapter progress).
- Console: 1 × 404 + 1 × CSP/MIME-type warn (same as before, asset not business logic).
- **Screenshot:** `walk-w3-step6-dashboard.png`.

### Extended-scope checks

| Check | Result |
|---|---|
| F.3 Resume after page reload | **PASS** — reload at progress 50% restored full conversation history + advanced to 66% (which had been written to DB during `converse_reply_reject` window but not yet rendered). The fallback-shown failed turn was elided from history on resume. |
| F.8 Mobile (390×844) | **PASS** — completed wizard already completed; navigated back to `/onboarding` at mobile viewport, no horizontal scroll, all conversation messages render legibly. Screenshot: `walk-w3-f8-mobile-onboarding.png`. |
| F.4 PII in cache_key | **FAIL — MEDIUM**: existing pre-walk row in `backstory_cache` has `cache_key="zürich|techno|3|unknown|unknown|twenties|other"` — raw lowercased city name (Zürich), not hashed. |
| Vocab grep `curl /onboarding ¦ rg "FILE\|dossier\|clearance\|FIELD"` | **PASS** — 0 matches. |
| F.7 Cost | **N/A** — `users` table has no `cost_usd` column; cost tracking lives elsewhere (out of scope for read-only walk). |
| F.10 Auth resume / idempotent re-onboarding | **FAIL** — re-navigation to `/onboarding` post-completion stays on `/onboarding` showing the completed wizard at 83%, does NOT redirect to `/dashboard`. |
| F.6 Wrong OTP | **N/A — UNREACHABLE** — deployed `/start` welcome flow does NOT trigger OTP collection in Telegram chat; the bot only deep-links to portal. Spec 215 OTP path may exist in code but is not exercised. |

---

## 3. Acceptance criteria results table

### A — Welcome / IS-A interstitial
| AC | Result | Evidence |
|---|---|---|
| A.1 `/start` triggers Nikita-voiced welcome | PASS | bot msg 22327: "Hey V.. I don't think we've met. Tap below to open the door." (49 chars, no markdown, lowercase-friendly tone) |
| A.2 Welcome reply ≤ 280 chars | PASS | 49 chars |
| A.3 No "as an AI" / generic LLM tells | PASS | clean tone |
| A.4 Welcome asks for email (TG-conversational signup) | **FAIL** | bot does NOT ask for email in chat — instead deep-links to portal. Spec 215 expectation (TG-conversational) violated. |
| A.5 `signup_state='awaiting_email'` row created | **FAIL** | no row created on `/start`. |
| A.6 IS-A interstitial visible after magic-link click | **FAIL** | no interstitial; lands directly on wizard page. |
| A.7 IS-A "Enter portal" CTA | **FAIL** | absent. |
| A.8 Set-Cookie auth instead of URL-fragment JWT | PASS | `https://vlvlwmolfdpzdfmtipji.supabase.co/auth/v1/user [200]` calls succeed post-magic-link, indicating cookie-borne session (no fragment-token leak observed in network tab). |

### B — Email submission + magic-link delivery
| AC | Result | Evidence |
|---|---|---|
| B.1 Portal `/onboarding/auth` renders email form | PASS | snapshot uid=1_8 textbox, uid=1_9 button |
| B.2 Submit → success card with cooldown | PASS | "Door sent to … Wait 59s" |
| B.3 Email arrives ≤ 5 min | PASS | 45s end-to-end |
| B.4 Email contains 8-digit OTP | PASS | `35416794` |
| B.5 Email contains magic-link URL | PASS | yes (Supabase `auth/v1/verify` form) |
| B.6 Magic-link URL is **portal /auth/confirm?token_hash=…** (PR #438 form) | **FAIL — CRITICAL** | URL is `https://vlvlwmolfdpzdfmtipji.supabase.co/auth/v1/verify?token=pkce_…&type=signup&redirect_to=…/auth/callback?next=/onboarding` — old Supabase action_link form, not the portal-direct PKCE form PR #438 introduced. |
| B.7 `disable_web_page_preview=true` | N/A | URL not delivered via Telegram in this flow. |

### C — `signup_state` machine
| AC | Result | Evidence |
|---|---|---|
| C.1 `code_sent` after email submit | **FAIL** | no `telegram_signup_sessions` row at any point. |
| C.2 `magic_link_sent` after magic link minted | **FAIL** | same — table never written. |

### D — Magic-link landing
| AC | Result | Evidence |
|---|---|---|
| D.1 200 OK + Set-Cookie session | PASS (implicitly — wizard-API calls succeed) |
| D.2 No auth-redirect loop | PASS |

### E — Agentic-workflow verification (Walk V precedent)
| AC | Result | Evidence |
|---|---|---|
| E.1 Cumulative state in JSONB | **PARTIAL** | extracted slots accumulate as `extracted_kinds=[location, vibe, scene, identity, backstory, phone]` across turns ✓ — but no `state.slots` cumulative object is materialised; per-turn `extracted` field on each user-role message is the only structure. The agent appears to RECONSTRUCT cumulative state by walking conversation history each turn. Anti-pattern adjacent: not a literal per-turn snapshot, but no Pydantic `WizardSlots` model is visible in DB. |
| E.2 Pydantic completion gate | **FAIL** | `onboarding_status='pending'` at end-of-walk with all 6 slots present. progress_pct stops at 83% (5/6 = 83.3%) — `darkness` slot was NEVER extracted as a kind, even though `drug_tolerance=3` was deterministically set in user_profiles. The completion gate is per-kind-coverage based and is not driven by a `FinalForm.model_validate(...)` Pydantic gate over a single state model. Score-the-rule: completion never reaches True. |
| E.3 Tool consolidation (single TurnOutput, NOT 7 narrow tools) | **UNVERIFIED** | could not access verbose Cloud Run JSON logs to enumerate tool calls per turn (gcloud `--filter` flag rejected). Indirect signal: agent ran without tool-thrash latency (sub-3s replies), suggesting consolidation, but cannot confirm. |
| E.4 Monotonic progress | **PASS** | turn-by-turn: 0 → 16 → 16 → 33 → 50 → 50 (failed turn) → 66 → 83. Never decreases. ✓ |
| E.5 Dynamic instructions per turn | **UNVERIFIED** | logs not accessible at line-grain. |
| E.6 `agent.run(message_history=…)` | **UNVERIFIED** | logs not accessible. |

### F — Extended scope (anti-patterns + edge cases)
| AC | Result | Evidence |
|---|---|---|
| F.1 Magic-link idempotent on second click | **NOT EXERCISED** | single-shot to avoid invalidation. |
| F.3 Wizard resume after reload | **PASS** | reload at 50% restored to 66% with full history. |
| F.4 PII in `backstory_cache.cache_key` | **FAIL — MEDIUM** | raw `zürich` (city) appears unhashed in cache_key (`"zürich|techno|3|unknown|unknown|twenties|other"`). |
| F.6 Wrong OTP rejection | **N/A** | OTP path unreachable in deployed welcome flow. |
| F.7 Cost cap | **N/A** | column not on `users` table. |
| F.8 Mobile viewport | **PASS** | 390×844 renders cleanly. |
| F.9 Identity ambiguous → ModelRetry | **FAIL** | "simon" alone (no age, no occupation) was silently accepted as identity slot. Agent moved to backstory without re-prompting. Anti-pattern observed. Worse: name was hallucinated as `"simonsimon"` (mirrored echo) and persisted to `user_profiles.name`. |
| F.10 Post-completion `/onboarding` → `/dashboard` redirect | **FAIL** | revisiting /onboarding after wizard finished stays on /onboarding. |

---

## 4. Findings table

| # | Severity | Title | Evidence | Reproduction |
|---|---|---|---|---|
| 1 | **CRITICAL** | PR #438 PKCE fix unreachable from deployed welcome flow | Email delivered to `+pr438walk` contains Supabase action_link `auth/v1/verify?token=pkce_…&redirect_to=…` not portal `/auth/confirm?token_hash=…`. PR #438 only patched `generate_magiclink_for_telegram_user` (Telegram-delivered path); the deployed `/start` flow funnels users to portal email form which uses the Supabase email template, untouched. | (1) `/start` → bot. (2) Click "Meet her here" → portal `/onboarding/auth`. (3) Submit any email. (4) Inspect email — link is Supabase-hosted, not portal-direct. |
| 2 | **CRITICAL** | Onboarding completion gate never fires | `onboarding_status='pending'` after all 6 slots collected; progress stops at 83%; user remains on `/onboarding` indefinitely; `darkness` slot never extracted as a kind despite `drug_tolerance=3` written through. Agentic-design rule E.2 violated (no `FinalForm.model_validate` Pydantic gate). | Complete wizard turns 1-6, observe DB shows `pending` and FE shows 83%. |
| 3 | **HIGH** | Identity slot accepts ambiguous "simon" as complete | Per agentic-design rule and F.9: when user types just first name, agent should `ModelRetry`/re-prompt for full identity (name+age+occupation). Instead silently accepted as identity, moved on to backstory. | Submit `simon` at name prompt; observe wizard advances to backstory immediately. |
| 4 | **HIGH** | Name hallucinated as `simonsimon` (mirror echo) and persisted | `public.user_profiles.name='simonsimon'` after user typed `simon` (5 chars). Few-shot echo / repetition bug; mirrors GH #200 pattern noted in `.claude/rules/review-findings.md`. | Submit `simon` at identity prompt; query user_profiles.name. |
| 5 | **HIGH** | Backstory turn produces silent agent error (`converse_reply_reject`) | Cloud Run log `2026-04-27 22:10:32 WARNING - converse_reply_reject u…`; FE renders fallback "hold on, let me try that again."; user must retype. First attempt was a longer paragraph; retry was shorter and succeeded. | Submit a multi-clause backstory paragraph (`i'm 32, designer. used to be all about gallery openings and curated dinners; now I crave music that erases me for a few hours.`) — agent rejects. |
| 6 | **HIGH** | Spec 215 portal-first signup divergence: `telegram_signup_sessions` never written | Bot's `/start` welcome funnels to portal `/onboarding/auth` instead of in-chat email collection; `awaiting_email` / `code_sent` / `magic_link_sent` states never reached. Either spec was changed in implementation without doc update, or there are dual signup paths and the in-chat one is dormant. | `/start` → observe bot reply contains URL button only, no email-prompting prose; query `telegram_signup_sessions where telegram_id=746410893` → 0 rows. |
| 7 | **MEDIUM** | `backstory_cache.cache_key` contains raw lowercased city PII | Existing row: `cache_key="zürich|techno|3|unknown|unknown|twenties|other"`. Hashed-key would be `cache_key_hash=sha256(…)` per `.claude/rules/testing.md` Pre-PR Grep Gate #3. | Query `SELECT cache_key FROM backstory_cache LIMIT 1`. |
| 8 | **MEDIUM** | Send button only enables after trailing whitespace | FE bug: typing message body alone leaves button disabled; appending one space character flips button to enabled. Real user behaviour (no trailing space) would block submission. | Fill chat input with valid message body; observe button stays `disabled=true` until a space is appended. |
| 9 | **MEDIUM** | Wizard does NOT auto-redirect to dashboard on completion | Even after Nikita emits the terminal "set things up for tonight" message and progress hits 83%, FE keeps user on `/onboarding`. Manual `/dashboard` navigation works but isn't surfaced. | Complete all 6 turns; observe URL stays `/onboarding`. |
| 10 | **LOW** | `_vercel/insights/script.js` 404 + CSP MIME-type warning on every page | Console errors on `/onboarding/auth`, `/onboarding`, `/dashboard`. Asset returns HTML 404 not the expected JS, browser refuses to execute. | Open any portal page, inspect DevTools console. |

---

## 5. Final verdict — **FAIL**

**Rationale:** the walk's central thesis was to verify (a) PR #438 PKCE fix is live in production for the canonical user flow, and (b) the agentic onboarding wizard satisfies the E.1-E.6 verification matrix from `.claude/rules/agentic-design-patterns.md`. Both fail.

(a) Finding #1: PR #438 patches a *Telegram-delivered* magic-link path, but the deployed `/start` welcome flow routes users through *portal-first email submission* — which uses Supabase's email template, untouched by PR #438. The fix is therefore unreachable from a normal new-user signup. Either Spec 215's TG-conversational path needs to be live-routed by `/start`, or the PKCE format needs to ALSO be applied to the email-template flow.

(b) Finding #2: completion gate never fires (`onboarding_status='pending'` with 5 of 6 expected slot-kinds extracted). E.2 violated. F.9 violated (Finding #3). F.10 violated (Finding #9). Agentic-design rule §1 partial pass / §2 fail.

Recommended next actions for the orchestrator:
1. File CRITICAL GH issue for Finding #1 — title: "fix(215,auth): email-template magic-link still uses Supabase action_link, not portal /auth/confirm — PR #438 incomplete coverage". Cite PR #438 + this report.
2. File CRITICAL GH issue for Finding #2 — completion gate doesn't fire; cite agentic-design §1 hard rule violation.
3. File HIGH GH issues for #3, #4, #5, #6.
4. File MEDIUM GH issues for #7, #8, #9.
5. File LOW GH issue for #10.
6. Verify whether the Telegram-conversational path (Spec 215 PR-F1b) is live but not triggered, or removed. PR #438 was tested in isolation and likely passed because the test harness exercises `generate_magiclink_for_telegram_user` directly — the integration with `/start` welcome routing was not E2E-tested.

---

## 6. Post-walk DB cleanup

Executed FK-safe wipe via `mcp__supabase__execute_sql`:

```sql
DELETE FROM public.user_metrics             WHERE user_id = 'e6c55f77-…';
DELETE FROM public.user_vice_preferences    WHERE user_id = 'e6c55f77-…';
DELETE FROM public.user_profiles            WHERE id      = 'e6c55f77-…';
DELETE FROM public.users                    WHERE id      = 'e6c55f77-…';
DELETE FROM auth.users                      WHERE id      = 'e6c55f77-…';
```

Verification: `SELECT count(*) FROM auth.users WHERE email='simon.yang.ch+pr438walk@gmail.com'` returned `remaining=0`. Simon's main account `simon.yang.ch@gmail.com` (id `0a734aa6-…`) untouched (verified post-cleanup).

`backstory_cache` row `cache_key=zürich|techno|3|…` was NOT created by this walk (pre-existing, no `created_at` within 20-min window) and was NOT touched.

Walk artifacts (screenshots) retained for orchestrator review at:
- `walk-w3-step2-auth-page.png`
- `walk-w3-step5-wizard-turn0.png`
- `walk-w3-step5-wizard-final.png`
- `walk-w3-step6-dashboard.png`
- `walk-w3-f8-mobile-onboarding.png`

---

## 7. Anti-fabrication audit

Per `.claude/rules/live-testing-protocol.md` Critical Anti-Patterns:
- ☑ NO `INSERT INTO auth.users` — user row created via real magic-link auth flow.
- ☑ NO `signInWithPassword` — never called.
- ☑ NO `E2E_AUTH_BYPASS=true` — not set.
- ☑ NO custom JWT minting — service-role key used READ-ONLY (and for FK-safe DELETE in cleanup only).
- ☑ Real Gmail MCP retrieval — magic-link came from real Supabase email delivery to admin inbox via plus-alias.
- ☑ Real Telegram session — Simon's actual Telegram account interacted with the bot.

---

## 8. Tooling notes for future walks

- Prompt referenced `nikita.conversation_jsonb` schema; reality is `public.users.onboarding_profile` (jsonb column on users). Cleanup SQL should reflect this. `user_vice_preferences` is plural; `telegram_signup_sessions.created_at` not `updated_at`.
- `mcp__claude-in-chrome__*` tools were not in the deferred-tool list; substituted with `mcp__chrome-devtools__*` (1:1 capability mapping).
- `gcloud run services logs read … --filter` syntax is invalid; use `--log-filter`.
- Wizard send-button-needs-trailing-space bug is exploitable for repeated test resets; document for future walk subagents.
