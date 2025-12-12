# 015-onboarding-fix: Telegram Registration Flow Fix

## Overview

**Feature**: Fix broken Telegram registration flow where users cannot complete onboarding after clicking magic link.

**Type**: Bug Fix / Critical Path

**Priority**: P0 (Blocking - users cannot use the system)

**Dependencies**: 002-telegram (existing platform)

## Problem Statement

Users attempting to register via Telegram experience an infinite loop:
1. User sends `/start` → prompts for email ✅
2. User sends email → magic link sent ✅
3. User clicks magic link → success page displayed ✅
4. User returns to Telegram → "You need to register first" ❌
5. Loop back to step 1

### Root Cause Analysis

The `/api/v1/telegram/auth/confirm` endpoint (telegram.py:304-523):
- **IGNORES** the PKCE `code` parameter sent by Supabase
- **NEVER** exchanges the code for a session
- **NEVER** creates the user record
- Only displays static HTML success/error pages

The `TelegramAuth.verify_magic_link()` method exists but is never called.

### Impact

- **100% of new Telegram users** cannot complete registration
- **Voice agent (007)** cannot be tested without working Telegram flow
- **Portal-to-Telegram linking** is broken

## Solution Architecture

### Approach: Email Lookup Pattern

When the magic link is clicked, Supabase redirects with a PKCE `code` parameter. The challenge is recovering `telegram_id` without exposing it in the URL.

**Solution**: Look up `telegram_id` from `pending_registrations` table using `email` obtained from Supabase after code exchange.

```
User clicks magic link with ?code=XXX
    ↓
Exchange code with Supabase → get {email, user.id}
    ↓
pending_registrations.get_by_email(email) → telegram_id
    ↓
user_repository.create_with_metrics(user_id, telegram_id)
    ↓
pending_registrations.delete(telegram_id)
    ↓
Show success page
```

### Security Considerations

- `telegram_id` never exposed in URLs
- PKCE codes are single-use (enforced by Supabase)
- Pending registrations expire after 10 minutes
- Only email owner can complete registration

## Functional Requirements

### FR-015-001: Email Lookup in Pending Registrations
The system must support looking up pending registrations by email address to recover `telegram_id` during magic link verification.

**Acceptance Criteria**:
- AC-015-001.1: `get_by_email(email)` returns pending registration if exists and not expired
- AC-015-001.2: Returns `None` if email not found or registration expired
- AC-015-001.3: Query is performant (uses appropriate index)

### FR-015-002: Magic Link Verification Flow
The `/auth/confirm` endpoint must exchange the PKCE code and create the user record.

**Acceptance Criteria**:
- AC-015-002.1: Endpoint accepts `code` query parameter from Supabase redirect
- AC-015-002.2: Exchanges code for session via `supabase.auth.exchange_code_for_session()`
- AC-015-002.3: Extracts email and user_id from Supabase response
- AC-015-002.4: Looks up telegram_id via `pending_repo.get_by_email(email)`
- AC-015-002.5: Creates user record with linked telegram_id
- AC-015-002.6: Deletes pending registration after successful creation
- AC-015-002.7: Shows success page with "Return to Telegram" button

### FR-015-003: Error Handling
The endpoint must handle all error cases gracefully.

**Acceptance Criteria**:
- AC-015-003.1: Invalid/expired code → shows error page with "Start over with /start" message
- AC-015-003.2: No pending registration found → shows error with instructions
- AC-015-003.3: User already exists (double-click) → shows success page
- AC-015-003.4: Missing code parameter → shows error page
- AC-015-003.5: Supabase API failure → shows generic error with retry instructions

### FR-015-004: Idempotency
The verification flow must handle duplicate requests safely.

**Acceptance Criteria**:
- AC-015-004.1: Second magic link click when user exists → shows success (no error)
- AC-015-004.2: Concurrent requests for same user → only one creates record
- AC-015-004.3: Pending registration already deleted → handled gracefully

## Non-Functional Requirements

### NFR-015-001: Performance
- Magic link verification completes in <2 seconds
- Database queries use indexes

### NFR-015-002: Reliability
- Atomic user creation (user + metrics in single transaction)
- No orphaned records on partial failure

### NFR-015-003: Observability
- Log all verification attempts (success/failure)
- Include correlation IDs for debugging

## User Stories

### US-015-1: New User Registration (P1)
**As a** new Telegram user,
**I want to** complete registration by clicking the magic link,
**So that** I can start chatting with Nikita.

**Acceptance Criteria**:
- Given I sent my email to the bot
- When I click the magic link in my email
- Then I see a success page
- And when I return to Telegram, I can chat with Nikita

### US-015-2: Double-Click Protection (P2)
**As a** user who accidentally clicked the magic link twice,
**I want to** see a success page on both clicks,
**So that** I don't get confused by error messages.

**Acceptance Criteria**:
- Given I already completed registration
- When I click the magic link again
- Then I see a success page (not an error)

### US-015-3: Expired Link Handling (P2)
**As a** user who waited too long to click the magic link,
**I want to** see a clear error message,
**So that** I know to request a new link.

**Acceptance Criteria**:
- Given my magic link has expired (>60 seconds for Supabase, >10 minutes for pending registration)
- When I click the link
- Then I see an error page explaining the link expired
- And I see instructions to return to Telegram and type /start

## Technical Specifications

### Files to Modify

| File | Change Type | Description |
|------|-------------|-------------|
| `nikita/db/repositories/pending_registration_repository.py` | Add method | `get_by_email()` |
| `nikita/api/routes/telegram.py` | Refactor | `auth_confirm` endpoint (lines 304-523) |
| `tests/api/routes/test_telegram_auth_confirm.py` | New file | Unit tests |

### Database Changes

None required - `email` column already exists in `pending_registrations` table.

Optional performance optimization:
```sql
CREATE INDEX idx_pending_registrations_email
ON pending_registrations(email)
WHERE expires_at > NOW();
```

### API Changes

**Endpoint**: `GET /api/v1/telegram/auth/confirm`

**New Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `code` | string | No | PKCE authorization code from Supabase |
| `error` | string | No | Error type from Supabase |
| `error_code` | string | No | Specific error code |
| `error_description` | string | No | Human-readable error message |

**Response**: HTML page (success or error)

## Test Plan

### Unit Tests
- `test_get_by_email_found` - Returns registration when email exists
- `test_get_by_email_not_found` - Returns None when email doesn't exist
- `test_get_by_email_expired` - Returns None when registration expired
- `test_auth_confirm_success` - Creates user on valid code
- `test_auth_confirm_double_click` - Returns success when user exists
- `test_auth_confirm_no_pending` - Returns error when no pending registration
- `test_auth_confirm_invalid_code` - Returns error on invalid code
- `test_auth_confirm_missing_code` - Returns error when code missing

### Integration Tests
- E2E flow: /start → email → magic link → success → can chat

### Manual Testing
- Test with real Telegram bot and email (simon.yang.ch@gmail.com)
- Verify Portal flow still works (unaffected)

## Rollout Plan

1. Implement and test locally
2. Deploy to Cloud Run (staging)
3. Manual E2E test with test account
4. Deploy to production
5. Verify with real user registration

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-12 | Claude | Initial specification |
