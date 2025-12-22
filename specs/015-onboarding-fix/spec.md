# 015-onboarding-fix: Telegram OTP Registration Flow

## Overview

**Feature**: Replace magic link authentication with OTP code entry for Telegram registration.

**Type**: Architecture Redesign (v2.0)

**Priority**: P0 (Blocking - users cannot complete registration)

**Dependencies**: 002-telegram (existing platform), Supabase Auth

## Problem Statement

### Original Problem (v1.0 - Magic Link)
Users attempting to register via Telegram experience an infinite loop:
1. User sends `/start` → prompts for email
2. User sends email → magic link sent
3. User clicks magic link → success page displayed
4. User returns to Telegram → "You need to register first"
5. Loop back to step 1

### Root Cause (v1.0)
The `/api/v1/telegram/auth/confirm` endpoint was not exchanging PKCE codes or creating user records.

### v1.0 Fix Status: SUPERSEDED
The magic link approach was implemented but has a **fatal UX flaw**:
- User clicks magic link → lands on web page
- User clicks "Open Telegram" → opens bot PROFILE page, not existing chat
- User confused: "Now what? Am I registered?"
- **Database operations work correctly**, but UX continuation is broken

### v2.0 Solution: OTP Code Entry
Replace magic links with 6-digit OTP code entry directly in Telegram chat:
- User stays in Telegram throughout registration
- No browser context switch required
- Immediate conversation continuation after verification

## Solution Architecture

### v2.0 Approach: OTP State Machine

User enters 6-digit code directly in Telegram chat. No web redirects.

```
User: /start in Telegram
Bot: "What's your email?"
User: user@example.com
Bot: "Check your email for a 6-digit code. Enter it here."
[Supabase sends email with code: 847291]
User: 847291
Bot: "Perfect! You're all set. What's on your mind?"
[CONVERSATION BEGINS IMMEDIATELY]
```

### Why OTP > Magic Links for Telegram
| Aspect | Magic Link | OTP Code |
|--------|------------|----------|
| Context | Leaves Telegram → Browser → Return | Stays in Telegram |
| Friction | 3+ context switches | 1 action (enter code) |
| Mobile UX | Terrible (opens browser) | Excellent (stays in app) |
| Continuation | Dead-end page | Immediate conversation |
| Implementation | Complex redirect handling | Simple state machine |

### Supabase OTP Pattern
```python
# Step 1: Send OTP (no redirect)
await supabase.auth.sign_in_with_otp({
    "email": email,
    # NO emailRedirectTo = code-only email
    "options": {"should_create_user": True}
})

# Step 2: Verify OTP
response = await supabase.auth.verify_otp({
    "email": email,
    "token": "847291",
    "type": "email",  # CRITICAL: "email" not "magiclink"
})
```

### Security Considerations
- OTP codes expire after 1 hour (Supabase default)
- Rate limit: 1 request per 60 seconds per email
- `telegram_id` never exposed in URLs
- `chat_id` stored to enable state tracking
- Only email owner can complete registration

---

## Functional Requirements

### FR-015-001: Email Lookup in Pending Registrations [SUPERSEDED by v2.0]
*v1.0 requirement - kept for audit trail*

### FR-015-002: Magic Link Verification Flow [SUPERSEDED by v2.0]
*v1.0 requirement - kept for audit trail*

### FR-015-003: Error Handling [SUPERSEDED by v2.0]
*v1.0 requirement - kept for audit trail*

### FR-015-004: Idempotency [SUPERSEDED by v2.0]
*v1.0 requirement - kept for audit trail*

---

### FR-015-005: OTP Code Delivery (v2.0)
The system must send a 6-digit OTP code via email when user provides email in Telegram.

**Acceptance Criteria**:
- AC-015-005.1: `send_otp_code(telegram_id, chat_id, email)` sends 6-digit code via Supabase
- AC-015-005.2: Supabase `sign_in_with_otp` called WITHOUT `emailRedirectTo` (code-only mode)
- AC-015-005.3: Pending registration stored with `chat_id` and `otp_state="code_sent"`
- AC-015-005.4: Bot responds with "Check your email for a 6-digit code. Enter it here."
- AC-015-005.5: Rate limiting: max 1 OTP per email per 60 seconds

### FR-015-006: OTP Code Verification (v2.0)
The system must verify OTP codes entered in Telegram chat and complete registration.

**Acceptance Criteria**:
- AC-015-006.1: Webhook detects 6-digit numeric message when `otp_state="code_sent"`
- AC-015-006.2: `verify_otp_code(telegram_id, code)` calls Supabase `verify_otp` with `type="email"`
- AC-015-006.3: On success: create user record with `telegram_id`, delete pending registration
- AC-015-006.4: On success: bot responds with welcome message and conversation begins
- AC-015-006.5: On invalid code: bot responds with "That code doesn't look right. Check your email?"
- AC-015-006.6: On expired code: bot responds with "That code expired. Send your email again?"

### FR-015-007: OTP State Machine (v2.0)
The webhook handler must track OTP verification state.

**Acceptance Criteria**:
- AC-015-007.1: `pending_registrations` table has `chat_id BIGINT` column
- AC-015-007.2: `pending_registrations` table has `otp_state VARCHAR(20)` column
- AC-015-007.3: `otp_state` values: 'pending', 'code_sent', 'verified', 'expired'
- AC-015-007.4: Non-6-digit messages during `code_sent` state remind user to enter code
- AC-015-007.5: `/start` during `code_sent` state offers to resend code

### FR-015-008: Backward Compatibility (v2.0)
The system must handle existing magic links during transition.

**Acceptance Criteria**:
- AC-015-008.1: `auth_confirm` endpoint remains functional but deprecated
- AC-015-008.2: Existing magic links (clicked before OTP rollout) still work
- AC-015-008.3: Deprecation warning logged when `auth_confirm` is used

---

## Non-Functional Requirements

### NFR-015-001: Performance
- OTP code delivery completes in <3 seconds
- OTP verification completes in <2 seconds
- Database queries use indexes

### NFR-015-002: Reliability
- Atomic user creation (user + metrics in single transaction)
- No orphaned records on partial failure
- Graceful handling of Supabase API failures

### NFR-015-003: Observability
- Log all OTP attempts (send/verify success/failure)
- Include telegram_id and email (masked) in logs
- Track conversion rate: OTP sent → verified

---

## User Stories

### US-015-1: New User Registration (P1) [SUPERSEDED by US-015-4]
*v1.0 user story - kept for audit trail*

### US-015-2: Double-Click Protection (P2) [STILL VALID]
**As a** user who accidentally submitted the code twice,
**I want to** see a success message on both attempts,
**So that** I don't get confused by error messages.

**Acceptance Criteria**:
- Given I already completed registration
- When I enter the same code again OR send a new message
- Then I can chat normally (not prompted to register)

### US-015-3: Expired Code Handling (P2) [UPDATED for v2.0]
**As a** user who waited too long to enter the code,
**I want to** see a clear error message,
**So that** I know to request a new code.

**Acceptance Criteria**:
- Given my OTP code has expired (>1 hour)
- When I enter the expired code
- Then I see "That code expired. Send your email again?"
- And I can send my email to get a new code

### US-015-4: OTP Registration (P1) [NEW in v2.0]
**As a** new Telegram user,
**I want to** complete registration by entering a 6-digit code in chat,
**So that** I can start chatting with Nikita without leaving Telegram.

**Acceptance Criteria**:
- Given I sent my email to the bot
- When I receive the 6-digit code in my email
- And I enter the code in Telegram chat
- Then I see a welcome message
- And I can immediately start chatting with Nikita

### US-015-5: Wrong Code Handling (P2) [NEW in v2.0]
**As a** user who mistyped the code,
**I want to** see a helpful error message,
**So that** I can try again.

**Acceptance Criteria**:
- Given I entered an incorrect 6-digit code
- When the verification fails
- Then I see "That code doesn't look right. Check your email?"
- And I can enter the correct code

---

## Technical Specifications

### Database Changes

**Migration: add_chat_id_and_otp_state**
```sql
ALTER TABLE pending_registrations
  ADD COLUMN chat_id BIGINT,
  ADD COLUMN otp_state VARCHAR(20) DEFAULT 'pending';
```

### Files to Modify

| File | Change Type | Description |
|------|-------------|-------------|
| `nikita/db/models/pending_registration.py` | Modify | Add `chat_id`, `otp_state` columns |
| `nikita/db/repositories/pending_registration_repository.py` | Modify | Update `store()` to include `chat_id` |
| `nikita/platforms/telegram/auth.py` | Modify | Add `send_otp_code()`, `verify_otp_code()` |
| `nikita/platforms/telegram/otp_handler.py` | New file | OTP verification handler |
| `nikita/platforms/telegram/registration_handler.py` | Modify | Use OTP instead of magic link |
| `nikita/api/routes/telegram.py` | Modify | Add OTP state detection in webhook |
| `tests/platforms/telegram/test_auth.py` | Modify | Add OTP tests |
| `tests/platforms/telegram/test_otp_handler.py` | New file | OTP handler tests |

### Files to Delete (Dead Code Cleanup)

| File | Reason |
|------|--------|
| `tests/api/routes/test_telegram_auth_confirm.py` | Tests magic link endpoint |
| `tests/e2e/test_auth_flow.py` | Tests magic link E2E flow |
| Lines 313-747 in `nikita/api/routes/telegram.py` | `auth_confirm` endpoint (after deprecation period) |

### API Changes

**New State in Webhook Handler**:
- Check `pending_registrations.otp_state` before processing messages
- Intercept 6-digit codes when `otp_state="code_sent"`

**Deprecated Endpoint** (kept for backward compatibility):
- `GET /api/v1/telegram/auth/confirm` - log deprecation warning

---

## Test Plan

### Unit Tests
- `test_send_otp_code_calls_supabase_without_redirect`
- `test_send_otp_code_stores_pending_with_chat_id`
- `test_verify_otp_code_creates_user_on_valid_code`
- `test_verify_otp_code_returns_error_on_invalid_code`
- `test_verify_otp_code_returns_error_on_expired_code`
- `test_webhook_intercepts_6_digit_code`
- `test_webhook_reminds_user_on_non_code_message`
- `test_otp_handler_sends_welcome_on_success`
- `test_otp_handler_sends_error_on_failure`
- `test_double_verification_shows_success`

### Integration Tests
- E2E flow: /start → email → code → conversation

### Manual Testing
- Test with real Telegram bot and email
- Verify Supabase email template shows code
- Test expired code scenario (wait >1 hour)

---

## Rollout Plan

1. Deploy database migration (additive, non-breaking)
2. Deploy OTP code with feature flag (default: enabled)
3. Monitor OTP send/verify success rate
4. After 1 week: deprecate `auth_confirm` endpoint
5. After 2 weeks: delete `auth_confirm` endpoint and magic link tests

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-12 | Claude | Initial specification (magic link approach) |
| 2.0 | 2025-12-14 | Claude | Redesigned for OTP code entry (magic link superseded) |
