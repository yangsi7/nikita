# 015-onboarding-fix: Implementation Plan

## Overview

Fix the broken Telegram registration flow by implementing proper magic link verification in the `/auth/confirm` endpoint.

## Architecture Decision

### Selected Approach: Email Lookup Pattern

**Why this approach**:
- Minimal code changes (1 new method + 1 endpoint refactor)
- No schema migrations needed (email column exists)
- Secure (telegram_id never in URL)
- Clean separation of concerns

**Alternatives considered**:
1. **Verification token in URL** - Requires schema migration, token in URL
2. **Two-step verification** - Poor UX, extra user step
3. **Callback webhook** - Complex, requires Supabase configuration

## Component Breakdown

### Component 1: PendingRegistrationRepository Enhancement

**Purpose**: Add email-based lookup for recovering telegram_id

**File**: `nikita/db/repositories/pending_registration_repository.py`

**Method**:
```python
async def get_by_email(self, email: str) -> PendingRegistration | None:
    """Get pending registration by email (for magic link verification).

    Used during magic link verification when we have email from Supabase
    but need to recover telegram_id.

    Args:
        email: Email address to look up.

    Returns:
        PendingRegistration if found and not expired, None otherwise.
    """
    stmt = select(PendingRegistration).where(
        PendingRegistration.email == email,
        PendingRegistration.expires_at > utc_now(),
    )
    result = await self._session.execute(stmt)
    return result.scalar_one_or_none()
```

**Dependencies**: None

**Risks**: Low (simple query addition)

### Component 2: Auth Confirm Endpoint Refactor

**Purpose**: Complete magic link verification and create user

**File**: `nikita/api/routes/telegram.py` (lines 304-523)

**Current state**: Shows static HTML pages, ignores `code` parameter

**Target state**:
1. Accept `code` parameter from Supabase PKCE redirect
2. Exchange code for session with Supabase
3. Extract email from Supabase response
4. Look up pending registration by email
5. Create user with telegram_id
6. Delete pending registration
7. Show success/error HTML

**Pseudocode**:
```python
@router.get("/auth/confirm", response_class=HTMLResponse)
async def auth_confirm(
    request: Request,
    code: str | None = None,
    error: str | None = None,
    error_code: str | None = None,
    error_description: str | None = None,
    session: AsyncSession = Depends(get_async_session),
) -> str:
    # Handle Supabase errors first
    if error or error_code:
        return render_error_page(error, error_code, error_description)

    # Must have code for PKCE flow
    if not code:
        return render_error_page("missing_code", None, "No authorization code")

    try:
        # Get Supabase client
        supabase = get_supabase_client()

        # Exchange code for session
        response = await supabase.auth.exchange_code_for_session({"code": code})

        email = response.user.email
        supabase_user_id = UUID(response.user.id)

        # Initialize repositories
        pending_repo = PendingRegistrationRepository(session)
        user_repo = UserRepository(session)

        # Look up pending registration by email
        pending = await pending_repo.get_by_email(email)

        if pending is None:
            # Check if user already exists (double-click case)
            existing = await user_repo.get(supabase_user_id)
            if existing:
                return render_success_page()

            # No pending and no user - must start over
            return render_error_page(
                "no_pending",
                None,
                "No pending registration found. Return to Telegram and send /start."
            )

        telegram_id = pending.telegram_id

        # Check if user already exists (race condition protection)
        existing = await user_repo.get_by_telegram_id(telegram_id)
        if existing:
            await pending_repo.delete(telegram_id)
            return render_success_page()

        # Create user with telegram_id
        await user_repo.create_with_metrics(
            user_id=supabase_user_id,
            telegram_id=telegram_id,
        )

        # Clean up pending registration
        await pending_repo.delete(telegram_id)

        # Commit transaction
        await session.commit()

        return render_success_page()

    except Exception as e:
        logger.error(f"Auth confirm failed: {e}")
        return render_error_page("verification_failed", None, str(e))
```

**Dependencies**:
- Supabase async client
- PendingRegistrationRepository
- UserRepository
- Database session

**Risks**:
- Medium: Supabase API changes (mitigated by research)
- Low: Database transaction handling (existing patterns)

### Component 3: Test Suite

**Purpose**: Ensure reliability and prevent regression

**File**: `tests/api/routes/test_telegram_auth_confirm.py` (new)

**Test cases**:
| Test | Description | Priority |
|------|-------------|----------|
| `test_auth_confirm_success` | Valid code creates user | P1 |
| `test_auth_confirm_double_click` | Second click shows success | P1 |
| `test_auth_confirm_no_pending` | No pending shows error | P1 |
| `test_auth_confirm_invalid_code` | Invalid code shows error | P1 |
| `test_auth_confirm_missing_code` | Missing code shows error | P2 |
| `test_get_by_email_found` | Email lookup works | P1 |
| `test_get_by_email_expired` | Expired not returned | P1 |

## Implementation Sequence

```
Phase 1: Repository (30 min)
├── Add get_by_email() method
└── Add unit tests

Phase 2: Endpoint (2 hours)
├── Add dependencies (Supabase client, repos)
├── Implement verification logic
├── Update error/success HTML templates
└── Add integration tests

Phase 3: Verification (1 hour)
├── Run full test suite
├── Deploy to Cloud Run
└── E2E test with real account
```

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ Magic Link Click                                                │
│ GET /api/v1/telegram/auth/confirm?code=ABC123                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Supabase: exchange_code_for_session(code)                       │
│ → Returns: {user: {id: UUID, email: "user@example.com"}}       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Database: pending_registrations.get_by_email("user@example.com")│
│ → Returns: {telegram_id: 123456789, email: "...", expires_at} │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Database: users.create_with_metrics(                            │
│   user_id=supabase_uuid,                                       │
│   telegram_id=123456789                                        │
│ )                                                               │
│ → Creates: users + user_metrics records                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Database: pending_registrations.delete(telegram_id)             │
│ → Cleanup                                                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Response: HTML Success Page                                     │
│ "Email Verified! Return to Telegram to start chatting."        │
└─────────────────────────────────────────────────────────────────┘
```

## Error Handling Matrix

| Error Condition | Detection | User Message | Log Level |
|-----------------|-----------|--------------|-----------|
| Missing code param | `code is None` | "No authorization code provided" | WARNING |
| Invalid/expired code | Supabase exception | "Link expired or invalid" | WARNING |
| No pending registration | `pending is None and user is None` | "Return to Telegram and send /start" | INFO |
| User already exists | `existing is not None` | (Show success page) | DEBUG |
| Database error | SQLAlchemy exception | "Verification failed, please try again" | ERROR |
| Supabase API error | httpx exception | "Service unavailable" | ERROR |

## Rollback Plan

If issues are discovered after deployment:
1. Previous endpoint just showed HTML - users see success page (confusing but not harmful)
2. No database schema changes to rollback
3. Can redeploy previous version instantly via Cloud Run revisions

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| New user registration success rate | >95% | Logs: auth_confirm success/failure |
| Magic link click-to-chat time | <5 seconds | User experience |
| Error rate | <5% | Monitoring |

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-12 | Claude | Initial plan |
