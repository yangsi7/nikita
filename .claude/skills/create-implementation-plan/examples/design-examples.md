# Design Examples & Templates

**Purpose**: Concrete examples for research.md, data-model.md, contracts/, and quickstart.md generation.

---

## Example 1: research.md Template

### Complete Research Document Example

```markdown
# Technical Research & Decisions

**Feature**: User Authentication with OAuth
**Date**: 2025-10-23
**Planner**: create-implementation-plan skill

---

## Decision 1: OAuth Provider Libraries

**Decision**: Use @supabase/auth-helpers for OAuth integration

**Rationale**:
- Already using Supabase for backend (src/lib/supabase.ts:5)
- Native support for Google/GitHub OAuth providers
- Handles token refresh automatically
- Integrates with existing session management

**Alternatives Considered**:
1. **NextAuth.js**: Rejected
   - Reason: Adds complexity layer on top of Supabase
   - Article VI violation: Wrapper around existing framework
   - Adds ~50KB to bundle size unnecessarily

2. **Custom OAuth Implementation**: Rejected
   - Reason: Reinventing wheel, Article VI violation
   - Security risk: OAuth is complex, error-prone
   - Maintenance burden: Need to track provider API changes

**Evidence**:
- Intelligence: project-intel.mjs --search "supabase" found client at src/lib/supabase.ts:5
- MCP Ref: @supabase/auth-helpers documentation confirms Google/GitHub support
- CoD^Σ: existing_client@src/lib/supabase.ts:5 → reuse → avoid_wrapper

---

## Decision 2: Password Hashing Algorithm

**Decision**: Use bcrypt via Supabase Auth (default)

**Rationale**:
- Industry standard for password hashing
- Supabase Auth uses bcrypt by default
- Cost factor configurable for future-proofing
- Trust framework implementation (Article VI)

**Alternatives Considered**:
1. **argon2**: Rejected
   - Reason: Requires custom implementation
   - Supabase doesn't support out-of-box
   - Marginal security gain not worth complexity

2. **PBKDF2**: Rejected
   - Reason: Older standard, bcrypt preferred
   - No advantage over bcrypt in this context

**Evidence**:
- MCP Ref: Supabase Auth documentation confirms bcrypt with cost=10
- CoD^Σ: framework_default → trust → Article_VI_compliance

---

## Decision 3: Session Management Strategy

**Decision**: Use Supabase Session API with automatic refresh

**Rationale**:
- Existing session.ts at src/utils/session.ts:23 already uses Supabase
- Automatic token refresh prevents security gaps
- Integrates with existing middleware at src/middleware.ts:45

**Alternatives Considered**:
1. **Custom JWT Management**: Rejected
   - Reason: Reinventing existing functionality
   - Article VI violation: Wrapper around framework
   - Security risk: Token refresh is complex

**Evidence**:
- Intelligence: src/utils/session.ts:23 shows existing Supabase session usage
- CoD^Σ: existing_pattern@src/utils/session.ts:23 → extend → consistency

---

## Technical Constraints

1. **Browser Support**: Modern browsers (Chrome 90+, Firefox 88+, Safari 14+)
2. **OAuth Providers**: Google and GitHub initially (extensible for more)
3. **Token Expiry**: Access tokens expire in 1 hour (Supabase default)
4. **Refresh Strategy**: Automatic refresh 5 minutes before expiry
5. **Session Storage**: httpOnly cookies for security (XSS protection)

---

## Integration Points

**Existing Code**:
- src/lib/supabase.ts:5 - Supabase client initialization
- src/utils/session.ts:23 - Session management utilities
- src/middleware.ts:45 - Authentication middleware

**New Components Required**:
- src/services/auth-service.ts - OAuth flow orchestration
- src/components/auth/OAuthButton.tsx - OAuth provider buttons
- src/types/auth.ts - TypeScript interfaces for auth
```

---

## Example 2: data-model.md Template

### Complete Data Model Example

```markdown
# Data Model Specification

**Feature**: User Authentication with OAuth
**Technology-Agnostic**: Entity attributes without implementation types

---

## Entity: User

**Purpose**: Represents authenticated system user with support for email/password and OAuth authentication.

**Attributes**:
- **id**: Unique identifier for user
- **email**: Email address (unique, validated format)
- **password_hash**: Hashed password (for email/password auth)
  - Never store plaintext passwords
  - Use bcrypt algorithm
- **oauth_provider**: OAuth provider name (optional)
  - Allowed values: null, "google", "github"
- **oauth_id**: Provider-specific user identifier (optional)
  - Required if oauth_provider is set
- **display_name**: User's display name (optional)
- **avatar_url**: Profile picture URL (optional)
- **email_verified**: Email verification status
- **created_at**: Registration timestamp
- **updated_at**: Last profile update timestamp
- **last_login_at**: Most recent successful login

**Relationships**:
- **Has many**: Sessions (active login sessions)
- **Has many**: UserRoles (for authorization)

**Validation Rules**:
1. **email**: Must be valid email format (RFC 5322)
2. **password_hash**: Required only if oauth_provider is null
3. **oauth_provider + oauth_id**: Both required together or both null
4. **Uniqueness**:
   - email must be unique across all users
   - (oauth_provider, oauth_id) combination must be unique

**Invariants**:
- User MUST have either (password_hash) OR (oauth_provider + oauth_id)
- email_verified MUST be true for oauth users (provider handles verification)
- last_login_at updated on every successful authentication

---

## Entity: Session

**Purpose**: Represents an active user session with automatic token refresh.

**Attributes**:
- **id**: Unique session identifier
- **user_id**: Reference to User entity
- **access_token**: JWT access token (short-lived)
- **refresh_token**: JWT refresh token (long-lived)
- **expires_at**: Access token expiration timestamp
- **created_at**: Session creation timestamp
- **last_activity_at**: Most recent session activity
- **user_agent**: Browser/device information
- **ip_address**: IP address at session creation

**Relationships**:
- **Belongs to**: User (user_id → User.id)

**Validation Rules**:
1. **expires_at**: Must be in the future when session created
2. **access_token**: JWT format, signed by Supabase
3. **refresh_token**: JWT format, longer expiry than access_token

**Lifecycle**:
1. **Created**: On successful login (email/password or OAuth)
2. **Refreshed**: When access_token within 5 minutes of expiry
3. **Expired**: When expires_at passes and no refresh occurs
4. **Revoked**: On logout or security event

---

## Entity: OAuthState

**Purpose**: Temporary storage for OAuth CSRF protection during authentication flow.

**Attributes**:
- **state**: Random state token (UUID)
- **provider**: OAuth provider name
- **redirect_url**: Post-auth redirect destination
- **created_at**: State creation timestamp
- **expires_at**: State expiration (5 minutes from creation)

**Relationships**: None (ephemeral, cleaned up after use)

**Validation Rules**:
1. **state**: Must be cryptographically random UUID
2. **expires_at**: Auto-set to created_at + 5 minutes
3. **provider**: Must match User.oauth_provider allowed values

**Lifecycle**:
1. **Created**: When user clicks OAuth button
2. **Consumed**: When OAuth callback returns with matching state
3. **Expired**: Automatically cleaned up after 5 minutes

---

## Relationships Diagram (Conceptual)

```
User (1) ←→ (many) Session
User (1) ←→ (many) UserRole

OAuthState (ephemeral, no FK relationships)
```

---

## Validation Summary

| Entity | Critical Validations |
|--------|---------------------|
| User | Email format, password XOR oauth, uniqueness |
| Session | Token format, expiry future, user_id exists |
| OAuthState | State randomness, 5-min expiry, provider allowed |
```

---

## Example 3: API Contracts Template

### Complete Contract Example: contracts/auth-endpoints.md

```markdown
# Authentication API Contracts

**Feature**: User Authentication with OAuth
**Base Path**: /api/auth

---

## POST /api/auth/register

**Purpose**: Create new user account with email/password.

**Authentication**: None (public endpoint)

**Request Body**:
```json
{
  "email": "string (required, valid email format)",
  "password": "string (required, min 8 chars, must include: uppercase, lowercase, number, special char)",
  "display_name": "string (optional, max 100 chars)"
}
```

**Success Response (201 Created)**:
```json
{
  "user": {
    "id": "uuid",
    "email": "string",
    "display_name": "string or null",
    "email_verified": false,
    "created_at": "ISO 8601 timestamp"
  },
  "session": {
    "access_token": "JWT string",
    "refresh_token": "JWT string",
    "expires_at": "ISO 8601 timestamp"
  }
}
```

**Error Responses**:
- **400 Bad Request**: Invalid email format or password too weak
  ```json
  {
    "error": "validation_error",
    "message": "Password must include uppercase, lowercase, number, and special character",
    "field": "password"
  }
  ```
- **409 Conflict**: Email already registered
  ```json
  {
    "error": "email_exists",
    "message": "An account with this email already exists"
  }
  ```
- **500 Internal Server Error**: Server-side error
  ```json
  {
    "error": "internal_error",
    "message": "An unexpected error occurred"
  }
  ```

**Rate Limiting**: 5 requests per minute per IP address

---

## POST /api/auth/login

**Purpose**: Authenticate user with email/password.

**Authentication**: None (public endpoint)

**Request Body**:
```json
{
  "email": "string (required)",
  "password": "string (required)"
}
```

**Success Response (200 OK)**:
```json
{
  "user": {
    "id": "uuid",
    "email": "string",
    "display_name": "string or null",
    "last_login_at": "ISO 8601 timestamp"
  },
  "session": {
    "access_token": "JWT string",
    "refresh_token": "JWT string",
    "expires_at": "ISO 8601 timestamp"
  }
}
```

**Error Responses**:
- **401 Unauthorized**: Invalid credentials
  ```json
  {
    "error": "invalid_credentials",
    "message": "Email or password is incorrect"
  }
  ```
- **429 Too Many Requests**: Rate limit exceeded
  ```json
  {
    "error": "rate_limit_exceeded",
    "message": "Too many login attempts. Please try again in 5 minutes."
  }
  ```

**Rate Limiting**: 5 requests per minute per IP address

---

## GET /api/auth/oauth/{provider}

**Purpose**: Initiate OAuth authentication flow.

**Authentication**: None (public endpoint)

**Path Parameters**:
- **provider**: string (required) - OAuth provider name
  - Allowed values: "google", "github"

**Query Parameters**:
- **redirect_url**: string (optional) - URL to redirect after auth
  - Default: "/" (home page)
  - Must be same-origin for security

**Success Response (302 Redirect)**:
- Redirects to OAuth provider's authorization page
- Sets CSRF state token in httpOnly cookie

**Error Responses**:
- **400 Bad Request**: Invalid provider
  ```json
  {
    "error": "invalid_provider",
    "message": "Provider must be 'google' or 'github'"
  }
  ```

---

## GET /api/auth/oauth/callback

**Purpose**: Handle OAuth provider callback after user authorization.

**Authentication**: None (public endpoint, validates state token)

**Query Parameters**:
- **code**: string (required) - Authorization code from provider
- **state**: string (required) - CSRF protection token

**Success Response (302 Redirect)**:
- Redirects to redirect_url (from initial request)
- Sets session tokens in httpOnly cookies

**Error Responses**:
- **400 Bad Request**: Missing or invalid parameters
- **401 Unauthorized**: Invalid state token (CSRF attempt)
- **500 Internal Server Error**: OAuth provider API error

---

## POST /api/auth/refresh

**Purpose**: Refresh access token using refresh token.

**Authentication**: Refresh token in request body

**Request Body**:
```json
{
  "refresh_token": "JWT string (required)"
}
```

**Success Response (200 OK)**:
```json
{
  "access_token": "JWT string",
  "refresh_token": "JWT string (new token)",
  "expires_at": "ISO 8601 timestamp"
}
```

**Error Responses**:
- **401 Unauthorized**: Invalid or expired refresh token

---

## POST /api/auth/logout

**Purpose**: End user session and revoke tokens.

**Authentication**: Bearer token (access_token) required

**Request Headers**:
```
Authorization: Bearer <access_token>
```

**Success Response (204 No Content)**: Empty response body

**Error Responses**:
- **401 Unauthorized**: Missing or invalid access token
```

---

## Example 4: quickstart.md Template

### Complete Quickstart Example

```markdown
# Quickstart Validation Scenarios

**Feature**: User Authentication with OAuth
**Purpose**: Manual test scenarios for validating implementation

---

## Scenario 1: User Registration (P1 Story)

**Objective**: Verify new user can register with email/password

**Setup**:
1. Clear browser cookies and localStorage
2. Navigate to /register page
3. Have valid email ready (not previously registered)

**Test Steps**:
1. Enter email: `test-user-$(date +%s)@example.com`
2. Enter password: `SecurePass123!`
3. Enter display name: `Test User`
4. Click "Register" button

**Expected Outcome**:
- HTTP 201 response returned
- User created in database
- Session tokens set in httpOnly cookies
- Redirected to /dashboard
- Welcome message displays: "Welcome, Test User!"

**Verification Commands**:
```bash
# Check database
psql -c "SELECT id, email, display_name, email_verified FROM users WHERE email='test-user-XXX@example.com';"

# Check browser cookies
document.cookie  # Should include session tokens

# Check localStorage
localStorage.getItem('user_id')  # Should have user UUID

# Check redirect
window.location.pathname === '/dashboard'  # Should be true
```

**Cleanup**:
```bash
# Delete test user
psql -c "DELETE FROM users WHERE email='test-user-XXX@example.com';"
```

---

## Scenario 2: User Login (P1 Story)

**Objective**: Verify existing user can login with email/password

**Setup**:
1. Use existing test user (from Scenario 1) OR create one:
   ```bash
   # Create test user via API
   curl -X POST http://localhost:3000/api/auth/register \
     -H "Content-Type: application/json" \
     -d '{"email":"login-test@example.com","password":"SecurePass123!","display_name":"Login Test"}'
   ```
2. Clear browser cookies
3. Navigate to /login page

**Test Steps**:
1. Enter email: `login-test@example.com`
2. Enter password: `SecurePass123!`
3. Click "Login" button

**Expected Outcome**:
- HTTP 200 response
- Session tokens set in cookies
- Redirected to /dashboard
- User's display name shows in header: "Login Test"

**Verification Commands**:
```bash
# Check last_login_at updated
psql -c "SELECT email, last_login_at FROM users WHERE email='login-test@example.com';"
# last_login_at should be recent timestamp

# Check active session
psql -c "SELECT * FROM sessions WHERE user_id=(SELECT id FROM users WHERE email='login-test@example.com') ORDER BY created_at DESC LIMIT 1;"
```

---

## Scenario 3: Google OAuth Login (P2 Story)

**Objective**: Verify user can authenticate via Google OAuth

**Setup**:
1. Have Google account credentials ready
2. Clear browser cookies
3. Navigate to /login page

**Test Steps**:
1. Click "Sign in with Google" button
2. Redirected to Google authorization page
3. Enter Google credentials
4. Grant permission to application
5. Redirected back to application

**Expected Outcome**:
- HTTP 302 redirect to Google
- User grants permission
- HTTP 302 redirect back to app
- New user created OR existing user logged in
- Session tokens set
- Redirected to /dashboard

**Verification Commands**:
```bash
# Check user created with OAuth
psql -c "SELECT id, email, oauth_provider, oauth_id, email_verified FROM users WHERE oauth_provider='google' ORDER BY created_at DESC LIMIT 1;"
# email_verified should be TRUE (Google verifies emails)

# Check state token cleaned up
psql -c "SELECT COUNT(*) FROM oauth_states WHERE created_at < NOW() - INTERVAL '5 minutes';"
# Should be 0 (expired states auto-deleted)
```

**Security Checks**:
- State parameter validated (CSRF protection)
- OAuth callback only accepts valid state tokens
- Email automatically verified for OAuth users

---

## Scenario 4: Session Refresh (P1 Story)

**Objective**: Verify access token automatically refreshes before expiry

**Setup**:
1. Login as test user (from Scenario 2)
2. Wait for access token to be within 5 minutes of expiry
   - Or manually set expires_at to near-future in DB

**Test Steps**:
1. Make authenticated API request: `GET /api/user/profile`
2. Observe response includes refreshed token

**Expected Outcome**:
- Request succeeds (200 OK)
- Response headers include new access_token
- New expires_at is 1 hour from now
- User session remains active

**Verification Commands**:
```bash
# Check token refresh in session
psql -c "SELECT user_id, expires_at, last_activity_at FROM sessions WHERE user_id=(SELECT id FROM users WHERE email='login-test@example.com') ORDER BY created_at DESC LIMIT 1;"
# expires_at should be ~1 hour in future
# last_activity_at should be recent
```

---

## Scenario 5: Logout (P1 Story)

**Objective**: Verify user can logout and session is revoked

**Setup**:
1. Login as test user (active session)
2. Navigate to any authenticated page

**Test Steps**:
1. Click "Logout" button in navigation
2. Observe redirect to homepage

**Expected Outcome**:
- HTTP 204 response from logout endpoint
- Session tokens cleared from cookies
- Session marked as revoked in database
- Redirected to / (homepage)
- User cannot access authenticated pages

**Verification Commands**:
```bash
# Check session revoked
psql -c "SELECT id, user_id, expires_at FROM sessions WHERE user_id=(SELECT id FROM users WHERE email='login-test@example.com') ORDER BY created_at DESC LIMIT 1;"
# Session should be deleted or marked as revoked

# Try accessing authenticated endpoint (should fail)
curl -X GET http://localhost:3000/api/user/profile \
  -H "Authorization: Bearer <old_access_token>"
# Should return 401 Unauthorized
```

**Cleanup**:
```bash
# Delete all test users
psql -c "DELETE FROM users WHERE email LIKE '%test%';"
```

---

## Summary

Total Scenarios: 5
- **P1 Stories**: Scenarios 1, 2, 4, 5 (core authentication)
- **P2 Stories**: Scenario 3 (OAuth integration)

Each scenario tests specific acceptance criteria from plan.md and can be executed independently.
```
