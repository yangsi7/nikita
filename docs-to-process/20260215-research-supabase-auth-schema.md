# Supabase Auth Schema Research: auth.users & auth.identities

**Research Date**: 2026-02-15
**Purpose**: Document exact behavior of Supabase auth tables for magic link (`signInWithOtp`) and admin user creation flows

---

## Executive Summary

### Critical Findings

1. **Token Columns MUST be Empty String**: 4-6 token columns in `auth.users` MUST be `''` not `NULL` (GoTrue limitation)
2. **signInWithOtp Auto-Creates Users**: Magic link flow creates both `auth.users` AND `auth.identities` records if user doesn't exist
3. **admin.create_user() May NOT Create Identity**: Known bug where non-email providers don't create `auth.identities` rows
4. **Provider ID Required**: Recent Supabase versions require `provider_id` in `auth.identities`

---

## 1. auth.users Table Schema

### Complete Schema (from GitHub discussion #5043)

| Column | Type | Default/Required Value | Notes |
|--------|------|----------------------|-------|
| `id` | uuid | `gen_random_uuid()` | Primary key |
| `instance_id` | uuid | `'00000000-0000-0000-0000-000000000000'` | Fixed for self-hosted |
| `aud` | text | `'authenticated'` | Required for JWT |
| `role` | text | `'authenticated'` | User role |
| `email` | text | User's email | Nullable if phone-based |
| `encrypted_password` | text | bcrypt hash | From `crypt(password, gen_salt('bf'))` |
| `email_confirmed_at` | timestamptz | `now()` or `NULL` | Auto-set if `email_confirm: true` |
| `invited_at` | timestamptz | `NULL` | Set by `invite_user_by_email()` |
| `confirmation_token` | text | **`''` (empty string)** | ⚠️ MUST NOT BE NULL |
| `confirmation_sent_at` | timestamptz | `NULL` | When OTP/magic link sent |
| `recovery_token` | text | **`''` (empty string)** | ⚠️ MUST NOT BE NULL |
| `recovery_sent_at` | timestamptz | `NULL` | When recovery email sent |
| `email_change_token_new` | text | **`''` (empty string)** | ⚠️ MUST NOT BE NULL |
| `email_change` | text | **`''` (empty string)** | ⚠️ MUST NOT BE NULL |
| `email_change_sent_at` | timestamptz | `NULL` | When email change initiated |
| `email_change_token_current` | text | `''` (empty string) | May also need to be `''` |
| `phone` | text | `NULL` | User's phone number |
| `phone_confirmed_at` | timestamptz | `NULL` | Set if `phone_confirm: true` |
| `phone_change` | text | `''` (empty string) | Likely needs `''` |
| `phone_change_token` | text | `''` (empty string) | Likely needs `''` |
| `reauthentication_token` | text | `''` (empty string) | Likely needs `''` |
| `raw_app_meta_data` | jsonb | `'{"provider":"email","providers":["email"]}'` | System metadata |
| `raw_user_meta_data` | jsonb | `'{}'` | User-defined metadata |
| `is_super_admin` | boolean | `false` | Admin flag |
| `created_at` | timestamptz | `now()` | Creation timestamp |
| `updated_at` | timestamptz | `now()` | Last update timestamp |
| `last_sign_in_at` | timestamptz | `NULL` | Set on first login |

### Token Column Requirements (CRITICAL)

**From GitHub Issue #1940**: GoTrue cannot handle `NULL` in these columns (causes 500 error):

1. `confirmation_token` → **MUST BE `''`**
2. `email_change` → **MUST BE `''`**
3. `email_change_token_new` → **MUST BE `''`**
4. `recovery_token` → **MUST BE `''`**
5. `email_change_token_current` → Likely **MUST BE `''`** (mentioned in comments)
6. `phone_change_token` → Likely **MUST BE `''`**
7. `reauthentication_token` → Likely **MUST BE `''`**

**Error Pattern**: `"Scan error on column confirmation_token: converting NULL to string is unsupported"`

**Solution**: Always set to empty string `''` when manually creating users.

---

## 2. auth.identities Table Schema

### Complete Schema (from official docs + GitHub discussion)

| Column | Type | Purpose | Notes |
|--------|------|---------|-------|
| `id` | uuid | Unique identity ID | `gen_random_uuid()` |
| `user_id` | uuid | Foreign key to `auth.users.id` | REFERENCES auth.users ON DELETE CASCADE |
| `provider_id` | text | Provider's user ID | For OAuth: provider's user ID. For email/phone: same as `user_id` |
| `provider` | text | Provider name | `'email'`, `'phone'`, `'google'`, `'sso:<uuid>'`, etc. |
| `identity_data` | jsonb | Provider-specific claims | Format: `{"sub":"<user_id>","email":"<email>"}` |
| `email` | text | Generated column | References `identity_data->>'email'` |
| `last_sign_in_at` | timestamptz | Last auth with this identity | `now()` on creation |
| `created_at` | timestamptz | Creation timestamp | `now()` |
| `updated_at` | timestamptz | Last update timestamp | `now()` |

### identity_data JSON Structure

**For email provider**:
```json
{
  "sub": "00000000-0000-0000-0000-000000000000",
  "email": "user@example.com"
}
```

**For OAuth providers** (Google, GitHub, etc.): Contains provider-specific claims (varies by provider)

**For SAML providers**: Contains SAML attributes from IdP

### Provider Values

- **Email**: `'email'`
- **Phone**: `'phone'`
- **OAuth**: `'google'`, `'github'`, `'apple'`, etc.
- **SSO/SAML**: `'sso:<uuid-of-provider>'` (ID contains NameID)

---

## 3. signInWithOtp Behavior (Magic Link Flow)

### What Happens When Called

**API**: `supabase.auth.signInWithOtp({ email: "user@example.com" })`

### User Creation (if user doesn't exist)

From official docs:
> "If the user doesn't exist, `signInWithOtp()` will signup the user instead."

**To disable**: Set `shouldCreateUser: false` in options

### Database Records Created

#### auth.users Record
```python
{
    "id": "<generated-uuid>",
    "email": "user@example.com",
    "aud": "authenticated",
    "role": "authenticated",
    "email_confirmed_at": None,  # NOT confirmed yet
    "encrypted_password": None,  # Passwordless
    "confirmation_token": "",  # Empty string
    "recovery_token": "",
    "email_change_token_new": "",
    "email_change": "",
    "raw_app_meta_data": {"provider": "email", "providers": ["email"]},
    "raw_user_meta_data": {},
    "created_at": "2026-02-15T...",
    "updated_at": "2026-02-15T...",
}
```

#### auth.identities Record
```python
{
    "id": "<generated-uuid>",
    "user_id": "<auth.users.id>",
    "provider_id": "<same as user_id>",  # For email provider
    "provider": "email",
    "identity_data": {
        "sub": "<user_id>",
        "email": "user@example.com"
    },
    "email": "user@example.com",  # Generated column
    "created_at": "2026-02-15T...",
    "updated_at": "2026-02-15T...",
    "last_sign_in_at": None,  # Set on successful OTP verification
}
```

### Email Confirmation Flow

1. User calls `signInWithOtp({ email })`
2. If user doesn't exist → creates `auth.users` + `auth.identities`
3. Sets `confirmation_token` in `auth.users` (GoTrue internal, not exposed)
4. Sends email with magic link: `{{ .ConfirmationURL }}` or OTP: `{{ .Token }}`
5. User clicks link or enters OTP
6. GoTrue verifies token → sets `email_confirmed_at` to `now()`
7. Returns session with access token

---

## 4. admin.create_user() Behavior (Backend Registration)

### What Happens When Called

**API**: `supabase.auth.admin.create_user({ email, password, email_confirm: true })`

### User Creation

From official docs:
> "`create_user()` will not send a confirmation email to the user."

**Use `invite_user_by_email()` if email notification is needed.**

### Database Records Created

#### auth.users Record
```python
{
    "id": "<generated-uuid>",
    "email": "user@example.com",
    "aud": "authenticated",
    "role": "authenticated",
    "email_confirmed_at": "2026-02-15T..." if email_confirm else None,
    "encrypted_password": "<bcrypt-hash>",
    "confirmation_token": "",  # Empty string
    "recovery_token": "",
    "email_change_token_new": "",
    "email_change": "",
    "raw_app_meta_data": {"provider": "email", "providers": ["email"]},
    "raw_user_meta_data": {},  # Or custom metadata
    "created_at": "2026-02-15T...",
    "updated_at": "2026-02-15T...",
}
```

#### auth.identities Record (IMPORTANT CAVEAT)

**From GitHub Issue #1577**:
> "POST /admin/users does not really respect provider fields when they are not email."

**Behavior**:
- If `email` is provided → `auth.identities` row **MAY** be created with `provider='email'`
- If only `phone` provided → `auth.identities` row **MAY NOT** be created (known bug)
- Some users report identity is created, others report it's not

**Workaround**: Manually insert into `auth.identities` if needed:
```sql
INSERT INTO auth.identities (id, user_id, identity_data, provider, provider_id, created_at, updated_at)
VALUES (
    gen_random_uuid(),
    '<user_id>',
    format('{"sub":"%s","email":"%s"}', '<user_id>', 'user@example.com')::jsonb,
    'email',
    '<user_id>',
    now(),
    now()
);
```

---

## 5. Relationship Between auth.users.id and auth.identities.user_id

### Foreign Key Relationship

```sql
auth.identities.user_id REFERENCES auth.users.id ON DELETE CASCADE
```

**Cardinality**: One-to-Many
- One `auth.users` record can have **multiple** `auth.identities` (email + OAuth + phone)
- One `auth.identities` record belongs to **exactly one** `auth.users`

### Provider ID vs User ID

| Provider | provider_id | identity_data.sub |
|----------|-------------|-------------------|
| Email | Same as `user_id` | Same as `user_id` |
| Phone | Same as `user_id` | Same as `user_id` |
| OAuth (Google) | Google's user ID | Google's user ID |
| SAML | NameID from IdP | NameID from IdP |

### Anonymous Users

From official docs:
> "A user can have more than one identity. Anonymous users have no identity until they link an identity to their user."

**Anonymous user**:
- Has record in `auth.users` with `is_anonymous=true`
- **NO** record in `auth.identities` until identity is linked

---

## 6. Practical Implications

### For Portal Login (signInWithOtp)

**Expected Records**:
1. `auth.users` with `email`, `email_confirmed_at` set after OTP verification
2. `auth.identities` with `provider='email'`, `provider_id=user_id`

**Token Columns**: All set to `''` by Supabase automatically

### For Backend Registration (admin.create_user)

**Expected Records**:
1. `auth.users` with `email`, `encrypted_password`, `email_confirmed_at` if `email_confirm=true`
2. `auth.identities` **MAY OR MAY NOT** be created (see Issue #1577)

**Token Columns**: MUST manually set to `''` if using SQL fallback

### SQL Fallback Pattern (Most Reliable)

From GitHub Discussion #5043:

```sql
-- 1. Create user in auth.users
INSERT INTO auth.users (
    instance_id, id, aud, role, email, encrypted_password,
    email_confirmed_at, raw_app_meta_data, raw_user_meta_data,
    created_at, updated_at,
    confirmation_token, email_change, email_change_token_new, recovery_token
) VALUES (
    '00000000-0000-0000-0000-000000000000',
    gen_random_uuid(),
    'authenticated',
    'authenticated',
    'user@example.com',
    crypt('password123', gen_salt('bf')),
    now(),
    '{"provider":"email","providers":["email"]}'::jsonb,
    '{}'::jsonb,
    now(),
    now(),
    '', '', '', ''  -- ⚠️ CRITICAL: Empty strings, not NULL
) RETURNING id;

-- 2. Create identity in auth.identities
INSERT INTO auth.identities (
    id, user_id, identity_data, provider, provider_id,
    last_sign_in_at, created_at, updated_at
) VALUES (
    gen_random_uuid(),
    '<user_id_from_above>',
    format('{"sub":"%s","email":"%s"}', '<user_id>', 'user@example.com')::jsonb,
    'email',
    '<user_id>',
    now(),
    now(),
    now()
);
```

---

## 7. Common Pitfalls & Solutions

### Pitfall 1: NULL Token Columns

**Error**: `"Scan error on column confirmation_token: converting NULL to string is unsupported"`

**Cause**: Token columns set to `NULL` instead of `''`

**Solution**: Always use `''` for these columns:
```sql
confirmation_token = '',
recovery_token = '',
email_change = '',
email_change_token_new = '',
email_change_token_current = '',
phone_change_token = '',
reauthentication_token = ''
```

### Pitfall 2: Missing auth.identities Record

**Symptom**: User can't log in, 500 error: `"error finding user: Database error querying schema"`

**Cause**: `auth.users` exists but no corresponding `auth.identities` row

**Solution**: Always verify identity exists after user creation:
```sql
SELECT COUNT(*) FROM auth.identities WHERE user_id = '<user_id>';
```

If missing, manually insert (see SQL pattern above)

### Pitfall 3: Wrong provider_id

**Symptom**: User created but can't authenticate

**Cause**: `provider_id` doesn't match expected value for provider

**Solution**:
- Email/phone: `provider_id` = `user_id`
- OAuth: `provider_id` = OAuth provider's user ID
- SAML: `provider_id` = NameID from IdP

---

## 8. Verification Checklist

When debugging auth issues, verify:

- [ ] `auth.users.id` exists and is valid UUID
- [ ] `auth.identities.user_id` matches `auth.users.id`
- [ ] `auth.identities.provider` matches expected value (`'email'`, `'phone'`, etc.)
- [ ] `auth.identities.provider_id` is correct for provider type
- [ ] `auth.identities.identity_data` contains valid JSON with `sub` and `email`/`phone`
- [ ] All token columns in `auth.users` are `''` not `NULL`
- [ ] `auth.users.aud` = `'authenticated'`
- [ ] `auth.users.role` = `'authenticated'`
- [ ] `auth.users.email_confirmed_at` is set if user should be verified
- [ ] `auth.users.raw_app_meta_data` contains `{"provider":"email","providers":["email"]}`

---

## Sources

1. [Identities | Supabase Docs](https://supabase.com/docs/guides/auth/identities)
2. [Python: Create a user](https://supabase.com/docs/reference/python/auth-admin-createuser)
3. [Python API Reference | signInWithOtp](https://supabase.com/docs/reference/python/auth-signinwithotp)
4. [Error 500: Database error querying schema - Issue #1940](https://github.com/supabase/auth/issues/1940)
5. [Programmatically create new users - Discussion #5043](https://github.com/orgs/supabase/discussions/5043)
6. [Should admin create user handler create identities - Issue #1577](https://github.com/supabase/auth/issues/1577)
7. [User Management | Supabase Docs](https://supabase.com/docs/guides/auth/managing-user-data)
8. [Troubleshooting | Scan error on confirmation_token](https://supabase.com/docs/guides/troubleshooting/scan-error-on-column-confirmation_token-converting-null-to-string-is-unsupported-during-auth-login-a0c686)

---

## Research Confidence

**Overall**: 90%

| Topic | Confidence | Notes |
|-------|-----------|-------|
| Token column requirements | 95% | Well-documented in issues + troubleshooting |
| auth.identities schema | 95% | Official docs + verified in discussions |
| signInWithOtp behavior | 90% | Official docs clear, but implementation details sparse |
| admin.create_user behavior | 75% | Known bugs (Issue #1577), inconsistent reports |
| auth.users complete schema | 85% | Reverse-engineered from GitHub discussion, not official |

**Gaps**:
- Exact default values for all `auth.users` columns (Supabase doesn't publish complete schema)
- Whether newer Supabase versions fixed Issue #1577 (admin.create_user identity creation)
- Complete list of columns affected by NULL vs empty string requirement (confirmed 4, suspected 3 more)
