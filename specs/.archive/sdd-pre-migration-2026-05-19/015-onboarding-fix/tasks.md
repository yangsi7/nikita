# 015-onboarding-fix: Task Breakdown (v2.0 - OTP)

## Progress Summary

| User Story | Tasks | Completed | Status |
|------------|-------|-----------|--------|
| US-015-4: OTP Registration (P1) | 5 | 0 | Not Started |
| US-015-5: Wrong Code Handling (P2) | 1 | 0 | Not Started |
| US-015-2: Double-Click Protection (P2) | 1 | 0 | Not Started |
| US-015-3: Expired Code Handling (P2) | 1 | 0 | Not Started |
| Integration & Deployment | 2 | 0 | Not Started |
| Dead Code Cleanup | 1 | 0 | Not Started |
| **Total** | **11** | **0** | **0%** |

---

## v1.0 Tasks [SUPERSEDED]

*The following tasks from v1.0 (magic link approach) are superseded by v2.0 OTP tasks:*
- T1.1: Add `get_by_email()` to PendingRegistrationRepository - SUPERSEDED
- T1.2: Refactor `/auth/confirm` Endpoint - Core Logic - SUPERSEDED
- T1.3: Add Unit Tests for Repository Method - SUPERSEDED
- T2.1: Handle User Already Exists Case - SUPERSEDED
- T3.1: Error Page for Expired/Invalid Links - SUPERSEDED
- T4.1: Integration Tests - SUPERSEDED
- T4.2: Deploy and E2E Test - SUPERSEDED

---

## v2.0: OTP Registration Flow

### US-015-4: OTP Registration (P1)

#### T2.1: Database Migration - Add chat_id and otp_state

- **Status**: [ ] Not Started
- **Priority**: P1
- **Estimate**: 15 min
- **File**: `nikita/db/models/pending_registration.py`, migration file

**Description**: Add `chat_id` and `otp_state` columns to pending_registrations table.

**Acceptance Criteria**:
- [ ] AC-T2.1.1: Migration file created: `add_chat_id_and_otp_state`
- [ ] AC-T2.1.2: `chat_id BIGINT` column added (nullable)
- [ ] AC-T2.1.3: `otp_state VARCHAR(20)` column added with default 'pending'
- [ ] AC-T2.1.4: PendingRegistration model updated with new columns
- [ ] AC-T2.1.5: `store()` method updated to accept `chat_id` and `otp_state` parameters

**Implementation**:
```sql
ALTER TABLE pending_registrations
  ADD COLUMN chat_id BIGINT,
  ADD COLUMN otp_state VARCHAR(20) DEFAULT 'pending';
```

---

#### T2.2: Auth Service - send_otp_code() Method

- **Status**: [ ] Not Started
- **Priority**: P1
- **Estimate**: 20 min
- **File**: `nikita/platforms/telegram/auth.py`

**Description**: Add method to send 6-digit OTP code via Supabase without magic link redirect.

**Acceptance Criteria**:
- [ ] AC-T2.2.1: `send_otp_code(telegram_id, chat_id, email)` method exists
- [ ] AC-T2.2.2: Calls Supabase `sign_in_with_otp` WITHOUT `emailRedirectTo`
- [ ] AC-T2.2.3: Stores pending registration with `chat_id` and `otp_state="code_sent"`
- [ ] AC-T2.2.4: Returns `{"status": "code_sent", "email": email}`
- [ ] AC-T2.2.5: Validates email format before sending

**Tests Required**:
- `test_send_otp_code_calls_supabase_without_redirect`
- `test_send_otp_code_stores_pending_with_chat_id_and_state`
- `test_send_otp_code_validates_email_format`

---

#### T2.3: Auth Service - verify_otp_code() Method

- **Status**: [ ] Not Started
- **Priority**: P1
- **Estimate**: 25 min
- **File**: `nikita/platforms/telegram/auth.py`

**Description**: Add method to verify 6-digit OTP code and complete registration.

**Acceptance Criteria**:
- [ ] AC-T2.3.1: `verify_otp_code(telegram_id, code)` method exists
- [ ] AC-T2.3.2: Retrieves pending registration by telegram_id
- [ ] AC-T2.3.3: Calls Supabase `verify_otp` with `type="email"` (not "magiclink")
- [ ] AC-T2.3.4: Creates user record with telegram_id on success
- [ ] AC-T2.3.5: Deletes pending registration after successful verification
- [ ] AC-T2.3.6: Raises ValueError on invalid/expired code

**Tests Required**:
- `test_verify_otp_code_creates_user_on_valid_code`
- `test_verify_otp_code_raises_on_invalid_code`
- `test_verify_otp_code_raises_on_expired_code`
- `test_verify_otp_code_links_existing_user`

---

#### T2.4: OTP Verification Handler

- **Status**: [ ] Not Started
- **Priority**: P1
- **Estimate**: 20 min
- **File**: `nikita/platforms/telegram/otp_handler.py` (NEW)

**Description**: Create handler to process OTP code entry in Telegram chat.

**Acceptance Criteria**:
- [ ] AC-T2.4.1: `OTPVerificationHandler` class exists
- [ ] AC-T2.4.2: `handle(telegram_id, chat_id, code)` method verifies OTP
- [ ] AC-T2.4.3: On success: sends welcome message "Perfect! You're all set up now."
- [ ] AC-T2.4.4: On invalid code: sends "That code doesn't look right"
- [ ] AC-T2.4.5: On expired code: sends "That code expired"
- [ ] AC-T2.4.6: Logs all verification attempts

**Tests Required**:
- `test_otp_handler_sends_welcome_on_success`
- `test_otp_handler_sends_error_on_invalid_code`
- `test_otp_handler_sends_error_on_expired_code`

---

#### T2.5: Webhook OTP State Detection

- **Status**: [ ] Not Started
- **Priority**: P1
- **Estimate**: 20 min
- **File**: `nikita/api/routes/telegram.py`

**Description**: Add OTP state detection in webhook handler to intercept 6-digit codes.

**Acceptance Criteria**:
- [ ] AC-T2.5.1: Webhook checks `pending.otp_state == "code_sent"` before normal flow
- [ ] AC-T2.5.2: 6-digit numeric messages routed to OTPVerificationHandler
- [ ] AC-T2.5.3: Non-6-digit messages get reminder "I'm still waiting for that code"
- [ ] AC-T2.5.4: Returns WebhookResponse after handling OTP state

**Tests Required**:
- `test_webhook_intercepts_6_digit_code_when_awaiting`
- `test_webhook_reminds_user_on_non_code_message`
- `test_webhook_normal_flow_when_not_awaiting`

---

### US-015-5: Wrong Code Handling (P2)

#### T2.6: Invalid Code Error Handling

- **Status**: [ ] Not Started
- **Priority**: P2
- **Estimate**: 10 min
- **File**: `nikita/platforms/telegram/otp_handler.py`

**Description**: Handle invalid OTP codes with helpful error messages.

**Acceptance Criteria**:
- [ ] AC-T2.6.1: Invalid code returns "That code doesn't look right. Check your email?"
- [ ] AC-T2.6.2: User can retry entering code
- [ ] AC-T2.6.3: Pending registration not deleted on failed attempt

**Tests Required**:
- `test_invalid_code_shows_helpful_error`
- `test_invalid_code_allows_retry`

---

### US-015-2: Double-Click Protection (P2)

#### T2.7: Idempotent Verification

- **Status**: [ ] Not Started
- **Priority**: P2
- **Estimate**: 15 min
- **File**: `nikita/platforms/telegram/auth.py`

**Description**: Handle duplicate verification attempts gracefully.

**Acceptance Criteria**:
- [ ] AC-T2.7.1: Second code entry when user exists returns success
- [ ] AC-T2.7.2: No duplicate user records created
- [ ] AC-T2.7.3: Conversation continues normally after double verification

**Tests Required**:
- `test_double_verification_shows_success`
- `test_no_duplicate_users_on_concurrent_verification`

---

### US-015-3: Expired Code Handling (P2)

#### T2.8: Expired Code Error Handling

- **Status**: [ ] Not Started
- **Priority**: P2
- **Estimate**: 10 min
- **File**: `nikita/platforms/telegram/otp_handler.py`

**Description**: Handle expired OTP codes with clear instructions.

**Acceptance Criteria**:
- [ ] AC-T2.8.1: Expired code returns "That code expired. Send your email again?"
- [ ] AC-T2.8.2: User can restart by sending email again
- [ ] AC-T2.8.3: Expired state doesn't block new registration attempt

**Tests Required**:
- `test_expired_code_shows_clear_error`
- `test_expired_code_allows_restart`

---

## Integration & Deployment

### T2.9: Registration Handler Update

- **Status**: [ ] Not Started
- **Priority**: P1
- **Estimate**: 15 min
- **File**: `nikita/platforms/telegram/registration_handler.py`

**Description**: Update registration handler to use OTP flow instead of magic link.

**Acceptance Criteria**:
- [ ] AC-T2.9.1: `handle_email_input()` calls `send_otp_code()` instead of `register_user()`
- [ ] AC-T2.9.2: Bot message updated to "I sent a 6-digit code to your email. Enter it here!"
- [ ] AC-T2.9.3: Error handling for OTP send failures

**Tests Required**:
- `test_email_input_triggers_otp_send`
- `test_email_input_shows_code_prompt`

---

### T2.10: Deploy and E2E Test

- **Status**: [ ] Not Started
- **Priority**: P1
- **Estimate**: 30 min

**Description**: Deploy to Cloud Run and test with real Telegram + email.

**Acceptance Criteria**:
- [ ] AC-T2.10.1: Deploy via `gcloud run deploy nikita-api --source .`
- [ ] AC-T2.10.2: Test /start → email → code → conversation flow
- [ ] AC-T2.10.3: Verify user created in Supabase after OTP verification
- [ ] AC-T2.10.4: Verify wrong code shows error message
- [ ] AC-T2.10.5: Verify conversation begins immediately after verification

---

## Dead Code Cleanup

### T2.11: Remove Magic Link Dead Code

- **Status**: [ ] Not Started
- **Priority**: P2
- **Estimate**: 30 min

**Description**: Remove deprecated magic link code after OTP rollout.

**Acceptance Criteria**:
- [ ] AC-T2.11.1: Delete `tests/api/routes/test_telegram_auth_confirm.py`
- [ ] AC-T2.11.2: Delete or rewrite `tests/e2e/test_auth_flow.py`
- [ ] AC-T2.11.3: Add deprecation warning to `auth_confirm` endpoint
- [ ] AC-T2.11.4: Remove magic link helper code from `tests/e2e/helpers/gmail_helper.py`
- [ ] AC-T2.11.5: Archive `MAGIC_LINK_FIX.md` to `docs/archive/`

---

## Definition of Done

- [ ] All unit tests pass (new OTP tests)
- [ ] All integration tests pass
- [ ] Deployed to Cloud Run
- [ ] E2E test successful with real account
- [ ] Event stream updated
- [ ] No regressions in existing functionality
- [ ] Dead code cleaned up
- [ ] Documentation updated

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-12 | Claude | Initial task breakdown (magic link approach) |
| 1.1 | 2025-12-12 | Claude | Marked v1.0 tasks complete (7/7) |
| 2.0 | 2025-12-14 | Claude | Redesigned for OTP flow, v1.0 tasks superseded |
