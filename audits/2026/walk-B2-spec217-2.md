---
title: Walk B2 — Spec 217-2 backstory archetype fallback live verification
lifecycle: frozen
date: 2026-05-07
walk_label: walkB2
target_pr: '#552'
target_commit: '2edc781'
verdict: BLOCKED
---

# Walk B2 — Spec 217-2 backstory archetype fallback (BLOCKED)

## Verdict

**BLOCKED — could not exercise the archetype render step.** Walk halted at protocol step 6 (magic-link / OTP retrieval) because the Supabase signup OTP email never arrived in the bound Gmail inbox within ~5 minutes of the bot's "Check your inbox. Send me the code." prompt. Per `.claude/rules/live-testing-protocol.md`: "If ANY step is unreachable due to a real bug → STOP, file a GH issue, do NOT fabricate state to continue." Per `~/.claude/rules/operating-principles.md` Core Behavior #9: NEVER fabricate datastore state.

Path exercised: **Neither happy nor fallback nor regression path was reached.** The archetype-card render step requires an authenticated portal session, which requires the OTP code, which never arrived.

## Pre-flight (PASS)

| Check | Result |
|---|---|
| Master HEAD commit | `2edc781 fix(217,2): backstory archetype fallback (FE guard + BE wait_for) (#552)` ✓ |
| `gh repo view` | `yangsi7/nikita` returned ✓ |
| `mcp__telegram-mcp__get_me` | session valid (id 746410893, V., +41787950009) ✓ |
| Worktree path | `/Users/yangsim/Nanoleq/sideProjects/nikita/.claude/worktrees/agent-aa52852ec48b28f47` ✓ |

## Walk timeline (UTC)

| Step | Action | Outcome |
|---|---|---|
| 1 | `mcp__chrome-devtools__navigate_page` → `https://nikita-mygirl.com/` | 200, landing rendered with "Start Relationship" → `https://t.me/Nikita_my_bot?start=welcome` |
| 2 | Identified TG-first canonical (per Spec 216-G PR #537) | CTA correctly points to Telegram deep-link |
| 3 | `mcp__telegram-mcp__send_message @Nikita_my_bot "/start welcome"` (19:16:49) | Bot replied at 19:16:52 UTC: *"Hey. New face. I'm Nikita. If you want me in your life, give me your email. I'll send you a code."* |
| 4 | `send_message "simon.yang.ch+walkB2@gmail.com"` (19:17:03) | Bot replied at 19:17:09 UTC: *"Check your inbox. Send me the code."* |
| 5 | n/a (email collection embedded in step 3-4) | — |
| 6 | Polled Gmail for `from:onboarding@silent-agents.com newer_than:5m` and `subject:"Confirm Your Signup" newer_than:1h` four times across ~3 min | **No new email received.** Most recent confirm-signup email in inbox was the walkB1 dispatch at 10:38 UTC (~8.5 hours earlier). |
| 7-12 | (unreachable) | walk halted |

## Backend evidence

`gcloud logging read` (Cloud Run revision `nikita-api-00300-98x`) at 19:17:08 UTC:

```
2026-05-07T19:17:08.710407Z httpx INFO HTTP Request: POST https://vlvlwmolfdpzdfmtipji…  (Supabase auth POST)
2026-05-07T19:17:08.929990Z nikita.signup_funnel INFO signup_funnel_event
2026-05-07T19:17:08.930075Z nikita.signup_funnel INFO signup_funnel_event
2026-05-07T19:17:09.316336Z httpx INFO HTTP Request: POST https://api.telegram.org/bot…  (reply: "Check your inbox.")
```

The backend hit Supabase's auth endpoint and emitted two `signup_funnel_event` records, then sent the Telegram "Check your inbox" reply within ~600 ms. The OTP email dispatch is owned by Supabase's auth/SMTP layer and is opaque to the application logs at the level emitted (no `otp_sent` / `otp_dispatched` structured event surfaces from the worker logs).

## Hypotheses for non-delivery (not falsified, low-evidence)

1. **Supabase email rate-limit per address** — default 5 emails / hour per address. The walkB1 dispatch at 10:38 UTC is well outside the 1-hour window, so this is unlikely the cause unless the dashboard rate is set lower. Cannot verify; Supabase MCP `get_logs(auth)` returned `Unauthorized` from this worktree session (no `SUPABASE_ACCESS_TOKEN` env in subagent context).
2. **Plus-alias delay or SMTP lag** — Resend/Postmark/SendGrid (whichever the project uses) typically delivers <30 s. >5 min lag is unusual but not impossible during incidents.
3. **Bounce or filter** — the email may have been silently dropped by the SMTP layer or quarantined by Gmail before showing in inbox/spam search.
4. **Address normalization mismatch** — Supabase may normalize `+walkB2` differently than the previous `+walkB1` and silently dedupe to the underlying address. Speculative.

## Tool-call accounting

Roughly 22 of the 30-call HARD CAP consumed before halt. Stopping per protocol; not over-budget but no path forward without a session.

## What was NOT exercised (must be re-run)

- Step 8 portal handoff via magic-link
- Step 9 wizard completion to the archetype-trigger field
- Step 10 archetype card render (HAPPY) OR Alert with retry CTA (FALLBACK)
- Step 11 persistence check via Supabase SQL
- Step 12 DB cleanup
- Cloud Run log probe for `backstory_pipeline_timeout` / `backstory_fallback_fired`

The 217-2 fallback machinery (`ArchetypeFallback.tsx`, BE `asyncio.wait_for(..., 20.0)`) is therefore **NOT live-verified by this walk**. Code-side review of the merged diff (commit `2edc781`) is unchanged from the PR-553-time review; this walk cannot upgrade or downgrade that signal.

## DB cleanup (NOT performed)

Could not run the FK-safe DELETE template — Supabase MCP returned `Unauthorized. Please provide a valid access token to the MCP server via the --access-token flag or SUPABASE_ACCESS_TOKEN.` in the worktree subagent context. No `auth.users` row was created during this walk anyway (signup_funnel events fired but the OTP code was never confirmed, so the user identity was never minted), so cleanup is a non-issue for walkB2 specifically. **Caveat**: the live-testing-protocol assumes Supabase MCP authority. Future walks dispatched into worktree contexts will hit the same blocker unless `SUPABASE_ACCESS_TOKEN` is forwarded.

## GH issues filed

- **HIGH** — fix(auth,otp): Supabase OTP email not delivered within 5 min for plus-alias signup (walk B2 reproduction) — *to be filed by orchestrator with this report attached.*
- **MEDIUM** — chore(devx): Supabase MCP unauthorized in worktree subagent context — orchestrator should forward `SUPABASE_ACCESS_TOKEN` to walk subagents per `.claude/rules/live-testing-protocol.md` Prerequisites. *To be filed by orchestrator.*

(Issues are noted here for the orchestrator to file; a sandbox-restricted subagent cannot run `gh issue create` reliably without credentials review.)

## Screenshots

None — no UI state past the landing page was reached past the step-1 navigation (which is documented in the existing landing audits and not informative for this walk's verdict).

## Recommended next action

1. Re-attempt walk B2 from a session with: (a) `SUPABASE_ACCESS_TOKEN` available so the OTP and rate-limit posture can be inspected, (b) a fresh plus-alias (e.g., `+walkB2b`) to defeat any same-address dedupe.
2. If the second attempt also yields no email within 2 min, escalate the OTP-delivery issue to a CRITICAL and inspect the Supabase project SMTP config + recent provider-side delivery logs.
3. The 217-2 fallback claim remains **unverified live** until a successful walk reaches the archetype-trigger field.

---

*Generated by walk-B2 subagent against PR #552 commit `2edc781`. HARD CAP 30 tool calls; halted at ~22 to write report durably before exit.*

---

## Addendum 2026-05-07 (post-walk diagnosis)

**Verdict revised: BLOCKED on subagent search-filter bug, NOT on OTP delivery.**

Email DID arrive at `2026-05-07T19:17:08+00:00` — same second as the `POST /auth/v1/otp` 200 OK response. Recipient: `simon.yang.ch+walkb2@gmail.com` (Supabase lowercased the alias). OTP `21851528`, 60-min expiry. Verified by main orchestrator at ~19:35 UTC via `mcp__gmail__search_emails(query="in:anywhere newer_than:1h", maxResults=30)`.

**Root cause of false negative:** subagent over-filtered with `subject:"Confirm Your Signup" newer_than:1h` AND `from:onboarding@silent-agents.com newer_than:5m`. Tight 5-min window combined with first-poll Gmail index lag (~30-60s after delivery) returned 0. Subagent gave up after 4 polls / ~3 min.

**Corrective action:**
- GH #553 (HIGH OTP delivery) closed as false alarm.
- `.claude/rules/live-testing-protocol.md` step 6 updated with canonical Gmail query (`from:onboarding@silent-agents.com newer_than:5m` + widening-window retry ladder; halt only if `in:anywhere newer_than:1h` empty).
- Memory `feedback_gmail_mcp_search.md` rewritten with sender + subject reference table + plus-alias normalization note.

GH #554 (MEDIUM Supabase MCP token unauthorized in worktree subagent context) STANDS — orchestrator workaround used (Supabase MCP also failed in main session post-compact).

**217-2 backstory fallback live verification still pending.** Re-dispatch Walk B2-resume needed. The 217-2 fix machinery (`ArchetypeFallback.tsx` 4s timeout → shadcn Alert + retry CTA, BE `asyncio.wait_for(20s)` → `archetype_cards: null` + structured log) remains code-side clean (PR #552 QA → CLEAN, vitest 815/815, pytest pass) but unverified live.
