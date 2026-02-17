# Deep Audit Report — Nikita Repository

**Date**: 2026-02-14
**Scope**: Full codebase audit (Python backend, Next.js portal, tests, deployment, game mechanics)
**Method**: 7-agent parallel audit (5 discovery + 1 adversarial + 1 on-call researcher)
**Agents**: backend-auditor, frontend-auditor, e2e-auditor, tot-mapper, journey-reviewer, devils-advocate

---

## Executive Summary

35 unique findings identified across all agents. After adversarial review:
- **1 CRITICAL** (must-fix immediately)
- **3 HIGH** (must-fix before launch)
- **5 MEDIUM** (should-fix)
- **14 LOW** (nice-to-fix / feature gaps)
- **6 DISMISSED** (by design or false positive)
- **1 NEEDS-RESEARCH** (type mismatch verification)

**#1 Priority**: BUG-BOSS-1 + BACK-02 combo — boss encounters crash AND have no timeout, creating a **guaranteed permanent stuck state** for any player who reaches a boss threshold.

---

## Findings Table (Post-Adversarial Review)

### CRITICAL (1)

| ID | Title | File:line | Impact | Fix Complexity |
|----|-------|-----------|--------|----------------|
| BUG-BOSS-1 | `UserRepository()` instantiated without session in boss.py | `boss.py:142` | ALL boss pass/fail outcomes crash with TypeError. Players stuck in boss_fight forever (combined with no timeout). Core game mechanic non-functional. | LOW — inject session param |

**Details**: `_get_user_repo()` at `boss.py:142` returns `UserRepository()` with no `session` argument. `UserRepository.__init__` requires `session: AsyncSession`. Called by `process_pass()` (line 159) and `process_fail()` (line 180). Every boss judgment result (pass, fail, game_over, won) triggers this crash path.

**Combined with BACK-02**: Boss fight has NO timeout. Decay skips boss_fight users. Once a player enters boss_fight, the judgment crashes, and they are frozen in that state indefinitely — no decay, no normal message handling, no progression.

---

### HIGH (3)

| ID | Title | File:line | Impact | Fix Complexity |
|----|-------|-----------|--------|----------------|
| BACK-01 | `set_game_status()` doesn't exist on UserRepository | `message_handler.py:1225` | Engagement-based game-over silently fails. Caught by try/except — no crash but game_over never set. | LOW — rename to `update_game_status()` |
| BACK-02 | No boss_fight timeout mechanism | N/A (absent) | Users in boss_fight stay frozen forever if judgment crashes or they stop responding. Decay skips them. | MEDIUM — add pg_cron timeout job |
| BACK-05 | Voice HMAC hardcoded fallback secret | `voice.py:372,847`, `inbound.py:191`, `server_tools.py:287`, `service.py:366` | If `ELEVENLABS_WEBHOOK_SECRET` env var missing, HMAC uses `"default_voice_secret"` — forgeable. 5+ files affected. | LOW — remove fallback, fail if not set |

**BACK-01 Details**: `_handle_engagement_game_over()` calls `self.user_repository.set_game_status(user.id, "game_over")`. Only `update_game_status(user_id, status)` exists at `user_repository.py:333`. Reachability requires 7+ consecutive CLINGY days or 10+ DISTANT days — unlikely but possible. Silently swallowed by outer try/except.

**BACK-02 Details**: `DecayProcessor` (processor.py:21) skips `boss_fight` users via `SKIP_STATUSES`. No pg_cron job, no task endpoint, and no background process handles stale boss_fight states. The `process-conversations` job detects stale *conversations* but not stale *game_statuses*.

**BACK-05 Details**: Pattern `settings.elevenlabs_webhook_secret or "default_voice_secret"` appears in 5 files. Additionally `onboarding.py:189` uses `"default_secret"`. Must verify Cloud Run has the env var set. Fix: raise error if not configured instead of fallback.

---

### MEDIUM (5)

| ID | Title | File:line | Impact | Fix Complexity |
|----|-------|-----------|--------|----------------|
| FRONT-01 | deleteAccount() missing `?confirm=true` | `portal.ts:30` | Account deletion always returns 400 from backend. Feature non-functional. | LOW — add query param |
| BACK-06 | Task auth reuses telegram secret + None bypass | `tasks.py:50` | If `telegram_webhook_secret` is None, task endpoints are unauthenticated. Secret sharing increases blast radius. | LOW — separate secret |
| FRONT-02 | Admin role check mismatch (metadata vs email) | `middleware.ts:34` vs `auth.py:95` | Frontend uses `user_metadata.role`, backend uses email domain. Confusing UX for admins with mismatched config. Not a security hole (backend authoritative). | MEDIUM — unify mechanism |
| FRONT-07 | Most hooks don't surface errors to UI | All hooks in `portal/src/hooks/` | Silent failures — loading spinners never resolve, stale data shown. | MEDIUM — add error boundaries |
| FRONT-04 | 13 TypeScript/Pydantic type mismatches | `portal/src/lib/api/types.ts` | Field name mismatches (tone vs emotional_tone, conversation_count vs conversations_count), nullability gaps. Some may cause runtime display issues. | MEDIUM — align types |

---

### LOW (14)

| ID | Title | Impact |
|----|-------|--------|
| BACK-09 | Stale session detector processes game_over users | Wasted pipeline resources |
| BACK-10 | Boss response no concurrent message lock | Theoretical race condition |
| BACK-11 | Won users get canned response forever | Feature gap — no post-game content |
| BACK-12 | Voice pipeline blocks webhook response | Performance risk if pipeline slow |
| FRONT-03 | No Telegram unlink option | Feature gap — both frontend and backend |
| FRONT-05 | No game_over/won interstitial in dashboard | UX gap — just a badge, no explanation |
| FRONT-06 | Settings email always shows empty | Backend returns None for email |
| FRONT-08 | API client uses getSession() not getUser() | Stale token possible, not a security hole |
| FRONT-09 | No global 401 redirect handler | JSON error instead of login redirect |
| FRONT-10 | No request timeout on API client | Theoretical hang on slow backend |
| FRONT-11 | Potential duplicate thoughts on pagination | Minor UX glitch |
| FRONT-12 | Linked Telegram has no actions | Feature gap |
| G-7 | Voice delivery is TODO stub | Proactive voice calls don't work |
| G-10 | Voice scoring may not write to score_history | Need deeper check |
| GAP-DECAY-NOTIFY | Decay game-over sends no notification | User discovers on next message |

---

### DISMISSED (6)

| ID | Reason |
|----|--------|
| BACK-04 | Voice inbound DOES check game_status via availability check — defense-in-depth exists |
| BACK-07 | Critical stages 0-retry is intentional design — retrying bad LLM output doesn't help |
| BACK-08 | meta_prompt_model IS actively used — not dead config |
| G-1 | Voice not triggering boss encounters is BY DESIGN — bosses are text challenges |
| G-2 | Voice not updating engagement is BY DESIGN — engagement tracks message frequency |
| G-6 | Distant users who stop messaging still decay to 0 via pg_cron — engagement check is additive |

---

### NEEDS-RESEARCH (1)

| ID | Research Needed |
|----|-----------------|
| FRONT-04 | Verify which of 13 type mismatches cause actual runtime errors vs theoretical. Test with real API responses. |

---

## Test Coverage Gaps (from e2e-auditor)

| Code Path | Status | Severity |
|-----------|--------|----------|
| `_handle_engagement_game_over()` | UNTESTED | HIGH |
| Boss judgment outcome processing | UNTESTED for crash path | HIGH |
| Boss fight timeout/stale recovery | UNTESTED | MEDIUM |
| 7/20 portal endpoints (stats, metrics, engagement, vices, summaries, conversation detail, decay) | UNTESTED | MEDIUM |
| Voice → pipeline post-processing E2E | PARTIAL | LOW |

---

## Infrastructure Findings

| Finding | Severity | Detail |
|---------|----------|--------|
| pg_cron not version-controlled | MEDIUM | Schedules only in Supabase dashboard SQL, not in migrations |
| No .dockerignore | LOW | Production image may include tests, specs, docs |
| No .env.example | LOW | Env vars documented only in settings.py |

---

## Remediation Priority

### Immediate Hotfixes (< 30 min)
1. **BUG-BOSS-1**: Fix `boss.py:142` — pass session to UserRepository
2. **BACK-01**: Fix `message_handler.py:1225` — rename to `update_game_status()`
3. **FRONT-01**: Fix `portal.ts:30` — add `?confirm=true`
4. **BACK-05**: Remove hardcoded fallback secrets, fail if env var missing

### Spec 048: Game Mechanics Remediation (8-14h)
- Boss timeout mechanism (pg_cron or background check)
- BreakupManager wiring decision (wire or remove dead code)
- Won state post-game content
- Engagement background check (optional, since decay covers distant users)

### Spec 049: Portal Fixes (8-14h)
- Admin role unification
- Type alignment (13 mismatches)
- Error handling in hooks
- Game over/won interstitials
- Telegram unlink (frontend + backend)
- Global 401 handler
- Request timeouts

### Spec 050: Voice Pipeline Polish (4-8h)
- Verify voice scoring writes to score_history
- Voice delivery stub completion
- Voice webhook async pipeline option

### Spec 051: Infrastructure Cleanup (4-8h)
- Separate task auth secret
- pg_cron version control (SQL migration)
- .dockerignore
- .env.example
- Remove dead code (BreakupManager if not wiring)
