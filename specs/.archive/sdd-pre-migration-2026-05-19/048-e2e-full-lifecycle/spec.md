# Spec 048: Full-Lifecycle E2E Test

**Status**: IN PROGRESS
**Priority**: P1
**Created**: 2026-02-14

---

## Overview

Comprehensive end-to-end test covering the ENTIRE player lifecycle from account creation through Chapter 5 victory, using real production infrastructure. Validates all 44 integrated specs work together as a cohesive system.

## Scope

- Account creation via Telegram OTP
- Text onboarding (5-question flow)
- Chapter 1-5 gameplay with natural messaging
- Boss encounters at each chapter boundary (55-75% thresholds)
- Victory path (game_status='won')
- Game-over path (3 boss failures)
- Background jobs (decay, deliver, summary, cleanup, process)
- Portal dashboard verification (9 pages)
- Edge cases (rate limiting, decay)

## Tools

- **Telegram MCP**: Bot interactions (@Nikita_my_bot)
- **Gmail MCP**: OTP email retrieval
- **Supabase MCP**: Data manipulation, verification queries
- **Chrome DevTools MCP**: Portal screenshots
- **gcloud CLI**: Health checks, deployment verification

## Constraints

- Admin endpoints require JWT from `@silent-agents.com` — use Supabase SQL instead
- Natural scoring yields +1 to +3/message — use SQL acceleration to reach boss thresholds
- Pipeline processes every 15 min via pg_cron — manually trigger via curl
- Neo4j cold starts take 60-120s — allow 180s timeout

## CRITICAL: No SQL Fallback for User Creation (GH #72 Lesson)

**NEVER create auth.users records via raw SQL INSERT.** GoTrue (Supabase auth, written in Go) uses `string` types (not `*string`) for 8 token columns. Raw SQL leaves them as NULL, which crashes Go's `database/sql` scanner with: `converting NULL to string is unsupported`.

**Mandatory rules:**
1. **User creation MUST go through Telegram registration flow** (`/start` → email → OTP → account). No exceptions.
2. **If OTP send fails**: Debug the OTP failure. Do NOT fall back to SQL INSERT.
3. **If SQL INSERT is absolutely unavoidable** (e.g., test data seeding), ALL 8 token columns MUST be set to empty strings `''`:
   - `confirmation_token`, `recovery_token`, `email_change`, `email_change_token_new`
   - `email_change_token_current`, `phone_change_token`, `phone_change`, `reauthentication_token`
4. **auth.identities row MUST also be created** alongside any auth.users record.
5. **Verification after any SQL user creation**: `SELECT recovery_token, email_change_token_new FROM auth.users WHERE email = '...'` — must return `''`, never NULL.

**Root cause (GH #72)**: E2E session created user via SQL fallback → NULL tokens → GoTrue `findUser()` crashed → portal login returned 500 "Database error finding user".

---

## Functional Requirements

### FR-001: User Cleanup
Delete all existing data for test user (`simon.yang.ch@gmail.com`) across all tables including `auth.users`.
- **AC-001.1**: All user-related rows deleted from 15+ tables (FK order respected)
- **AC-001.2**: `auth.users` entry deleted
- **AC-001.3**: Verification query returns 0 rows

### FR-002: Registration via Telegram
New user registers through `/start` → email → OTP code → account creation. (Note: Telegram uses OTP codes for registration; portal uses magic links for login — different auth flows.)
- **AC-002.1**: `/start` returns email prompt
- **AC-002.2**: Email submission triggers OTP code email within 120s
- **AC-002.3**: OTP code accepted, `users` row created (score=50, chapter=1, game_status='active')
- **AC-002.4**: `user_metrics` initialized (50/50/50/50)
- **AC-002.5**: `pending_registrations` cleaned up

### FR-003: Text Onboarding
User completes 5-question onboarding flow and receives first Nikita message.
- **AC-003.1**: Inline keyboard offers Text/Voice choice
- **AC-003.2**: 5 questions asked in sequence (LOCATION, LIFE_STAGE, SCENE, INTEREST, DRUG_TOLERANCE)
- **AC-003.3**: `user_profiles` created with correct values
- **AC-003.4**: `user_backstories` generated (non-empty)
- **AC-003.5**: 8 `user_vice_preferences` rows initialized
- **AC-003.6**: `onboarding_status = 'completed'`
- **AC-003.7**: First Nikita message references backstory context

### FR-004: Chapter 1 Gameplay
5 natural messages sent, pipeline processes, scoring verified.
- **AC-004.1**: 3+ responses received (ch1 skip rate 25-40%)
- **AC-004.2**: Conversations created and processed (status='processed')
- **AC-004.3**: Score delta positive
- **AC-004.4**: `score_history` entries exist
- **AC-004.5**: `engagement_states` row exists
- **AC-004.6**: `generated_prompts` exist (2000-3000 tokens)
- **AC-004.7**: No markdown asterisks in responses

### FR-005: Boss Encounter (per chapter)
Score accelerated via SQL, boss triggered, judgment evaluated.
- **AC-005.1**: `game_status` transitions: active → boss_fight → active
- **AC-005.2**: Boss opening matches chapter theme
- **AC-005.3**: BossJudgment evaluates PASS for quality response
- **AC-005.4**: Chapter advances (N → N+1)
- **AC-005.5**: `boss_attempts` resets to 0
- **AC-005.6**: `score_history` records boss event

### FR-006: Victory
After Chapter 5 boss pass, game completes.
- **AC-006.1**: `game_status = 'won'` after final boss
- **AC-006.2**: All 4 metrics significantly above 50 baseline

### FR-007: Background Jobs
5 pg_cron jobs verified active and functional.
- **AC-007.1**: 5 pg_cron jobs active (decay, deliver, summary, cleanup, process)
- **AC-007.2**: Manual trigger of each returns OK
- **AC-007.3**: Decay respects grace period

### FR-008: Portal Dashboard
9 portal pages load correctly with accurate data.
- **AC-008.1**: OTP auth flow completes in browser
- **AC-008.2**: 9 pages load without JS errors
- **AC-008.3**: Displayed score matches DB value
- **AC-008.4**: Chapter name correct
- **AC-008.5**: Conversation list populated

### FR-009: Rate Limiting
21st rapid message gets rate-limited.
- **AC-009.1**: 20 messages accepted
- **AC-009.2**: 21st gets rate-limit response

### FR-010: Game Over Path
3 failed boss attempts trigger game over.
- **AC-010.1**: `boss_attempts` increments 0→1→2→3
- **AC-010.2**: After 3 failures: `game_status = 'game_over'`
- **AC-010.3**: Subsequent messages get canned game-over response
- **AC-010.4**: `score_history` records all 3 `boss_fail` events

---

## Non-Functional Requirements

### NFR-001: Execution Time
Total E2E test completes within 5 hours (including cold starts and retries).

### NFR-002: Evidence
All verification queries logged with actual SQL results. Screenshots saved to `test-screenshots/`.

### NFR-003: Idempotency
Test can be re-run by executing Phase 0 cleanup first.
