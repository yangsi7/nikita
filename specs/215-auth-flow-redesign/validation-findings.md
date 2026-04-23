# Spec 215 — Validation Findings Manifest

## GATE 2 iter-1 disposition (2026-04-24)

Six parallel `sdd-*-validator` agents ran against `spec.md` v1 (commit pre-iter-2) and returned: **1 CRITICAL + 14 HIGH + 31 MEDIUM + 22 LOW**. This document records disposition per severity tier per the SDD GATE 2 Analyze-Fix Loop (CLAUDE.md SDD Enforcement #7).

---

## CRITICAL (1)

| ID | Validator | Finding | Disposition |
|---|---|---|---|
| C1 | data-layer | (Resolved upstream — see PR #414) | **RESOLVED via PR #414 commit `0cef586`.** Closed prior to iter-2 dispatch. |

---

## HIGH (14)

All 14 HIGH findings are **RESOLVED inline in `spec.md`** via the iter-2 commit on this branch (`spec/215-auth-flow-redesign`). See the iter-2 dispatch for the validator re-run; on re-validation PASS, this section flips to "RESOLVED + re-validated PASS."

| ID | Validator | Finding (1-line) | Inline fix in spec.md |
|---|---|---|---|
| API-H1 | api | Admin endpoint `generate_magiclink_for_telegram_user` lacks Pydantic request/response models | New §7.6 declares `GenerateMagiclinkRequest` + `GenerateMagiclinkResponse` with service-role auth note |
| API-H2 | api | Semantic conflict at `/auth/confirm`: T-E23 (idempotent) vs T-E27 (single-use replay block) | T-E27 reframed to TTL-only; T-E23 idempotency wins; FR-6 gains AC-6.7 + AC-6.8 + "Idempotency contract" subsection |
| DATA-H1 | data-layer | Migration must preserve `chat_id` column (FR-11c E1/E2/E3 routing) | §7.2 table now lists `chat_id BIGINT NOT NULL` as RETAINED with explicit migration step note |
| DATA-H2 | data-layer | `otp_state`/`otp_attempts` (existing) vs new `signup_state`/`attempts` | Migration ops now `RENAME` the existing columns (one source of truth); §7.2 columns annotated |
| DATA-H3 | data-layer | D6 destructive reset SQL needs FK-safe cascade order | §9.2 rewritten to follow `.claude/rules/live-testing-protocol.md` template (auth.users last) |
| DATA-H4 | data-layer | FSM transitions need explicit compare-and-swap predicates | New §7.2.1 "FSM Atomic Transitions" with 4 CAS UPDATE statements + fail-loud semantics |
| DATA-H5 | data-layer | `magic_link_token` storage contract unclear (raw URL vs hashed_token?) | §7.2 column comment + §7.6 handler contract clarify: hashed_token ONLY, never raw action_link |
| FE-H1 | frontend | IS-A interstitial visual contract missing (tokens, layout, ARIA) | New FR-6a "Visual Contract: IS-A Interstitial" with Tailwind allowlist, ASCII layout, shadcn refs, ARIA |
| FE-H2 | frontend | `/login` redesign visual contract missing; risk of code-input field re-introduction | New FR-10a "Visual Contract: /login Redesign" + FR-10 "No code-input field" clause + AC-10.6 |
| TEST-H1 | testing | No test for `disable_web_page_preview=True` on Telegram dispatch | §8.7 declares `tests/platforms/telegram/test_signup_handler_link_preview.py` with positive + negative-control ACs |
| TEST-H2 | testing | No test asserting `verification_type` passthrough (no hardcoded literal) | §8.7 declares `tests/api/routes/test_portal_auth_admin.py` with grep-based regression guard |
| TEST-H3 | testing | Missing T-E22/T-E23/T-E24/T-E27 coverage in portal route | §8.7 declares `portal/tests/app/auth/confirm/route.test.ts` with all 4 scenarios |
| TEST-H4 | testing | iOS Safari interstitial automation strategy unclear | §8.7 commits to UA-spoof unit test (`interstitial.test.tsx`); manual real-iPhone walk = OPTIONAL secondary |
| TEST-H5 | testing | No per-event Pydantic models / no PII assertions for FR-Telemetry-1 | §8.7 declares `tests/monitoring/test_signup_funnel_events.py` with 9-event table + grep gate for raw PII kwargs |

**Re-validation criterion**: iter-2 sdd-*-validator dispatch must return `0 HIGH` for this section to flip to "PASS." Per SDD Enforcement #7, max 3 iterations before escalation.

---

## MEDIUM (31)

Per CLAUDE.md SDD Enforcement #7(c): MEDIUM findings get a **GH issue** (track for v1.1 / fix in scope where cheap) OR an **explicit accept/defer decision**.

### Flagged for GH issue creation in next session (10)

These represent quality gaps with clear remediation paths. To be filed as `medium` GH issues against the Spec 215 milestone before Phase D `/plan` begins:

1. **Cookie scope** — `/auth/confirm` must set Supabase session cookies with `SameSite=Lax; Secure; HttpOnly; Domain=.nikita-mygirl.com` (or apex-only?) — needs explicit decision and test.
2. **CSRF same-origin guard** — confirm `/auth/confirm` cannot be invoked cross-origin via prefetch; add same-origin check or `Sec-Fetch-Site` header validation.
3. **T-E10 atomic rebind** — "email already bound to different telegram_id" needs an atomic SELECT-FOR-UPDATE pattern documented (currently only escape-hatch documented in FR-15).
4. **GDPR audit trail** — telegram_id ↔ auth.uid binding is a personal-data linkage event; must log to a tamper-evident audit table (or at least a structured log channel) per GDPR Art. 30.
5. **ARIA-live region for code-input feedback** — Telegram bot copy doesn't apply, but the `/login` error state needs `role="alert" aria-live="polite"` (already added in FR-10a; this MEDIUM tracks audit completeness for the broader auth page-set).
6. **IAB UA detection regex** — the Telegram in-app browser UA pattern needs to be a centralized constant (not duplicated per component) with regression tests against known-Telegram-IAB UA strings.
7. **Hydration boundary at `/auth/confirm`** — server route handler returns interstitial Client Component; document the hydration boundary explicitly (Suspense, `next/dynamic`, or none) and test for hydration mismatches.
8. **RLS policy text** — `telegram_signup_sessions` RLS policy needs full SQL written into the migration file, not just "service-role only" English.
9. **pg_cron prune timing** — code TTL purge cadence (currently implied "promptly") needs explicit cron schedule + jitter to avoid thundering-herd at minute boundaries.
10. **Schema indexes** — `telegram_signup_sessions(telegram_id)` and `(email)` need explicit `CREATE INDEX` statements in migration; verify query plans for FSM CAS UPDATEs use the index.

### Accepted — non-blocking, log only (21)

The remaining 21 MEDIUM findings are accepted as non-blocking quality nits. They are logged here for traceability and may be picked up opportunistically during Phase E `/implement`. Examples include: doc cross-link polish, prose tightening in FR-3/FR-4 acceptance bullets, additional T-E* edge cases (T-E20, T-E21 placeholders), additional ARIA polish on landing CTAs (FR-1), additional Pydantic Field descriptions, etc. Full text per validator report archived in `validation-reports/iter-1/`.

---

## LOW (22)

ACCEPTED — non-blocking, log only. All 22 LOW findings are wording/style/nit-level. Full text archived in `validation-reports/iter-1/`. No remediation tracked.

---

## User Approval

- [ ] User approved proceeding to Phase D `/plan`

(Unchecked. Awaiting iter-2 sdd-*-validator dispatch + analyze-fix loop closure per CLAUDE.md SDD Enforcement #7(e).)
