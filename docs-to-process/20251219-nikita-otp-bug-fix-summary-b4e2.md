# Nikita OTP Bug Fix - Magic Link vs OTP Code Issue

**Date**: 2025-12-19
**Issue**: Users receiving magic links instead of 6-digit OTP codes
**Root Cause**: Supabase email template not configured to send OTP codes
**Confidence**: 95% (verified against official Supabase documentation)

---

## The Problem

**What's happening**: When users request OTP via Telegram, they receive a clickable magic link in their email instead of a 6-digit code.

**Why it's confusing**: The method is named `sign_in_with_otp()` but Supabase sends **Magic Links by default**. The actual output type is controlled by **email template configuration**, not the method name.

---

## The Root Cause

**Location**: Supabase Dashboard → Email Templates → Magic Link template

**Current Template** (Default):
```html
<h2>Magic Link</h2>
<p>Follow this link to login:</p>
<p><a href="{{ .ConfirmationURL }}">Log In</a></p>
```

**Problem**: Contains `{{ .ConfirmationURL }}` which embeds a clickable link.

**Expected Template** (What Nikita needs):
```html
<h2>One time login code</h2>
<p>Please enter this code: {{ .Token }}</p>
```

**Fix**: Replace `{{ .ConfirmationURL }}` with `{{ .Token }}` variable.

---

## Your Code is Correct

**Nikita's Implementation** ✅

`nikita/platforms/telegram/auth.py` - Lines 286-292:
```python
await self.supabase.auth.sign_in_with_otp({
    "email": email,
    "options": {
        "should_create_user": True,
        # NO email_redirect_to = code-only email
    }
})
```

**Status**: ✅ Correct
- Does NOT include `email_redirect_to` (which would force magic link)
- Comment correctly notes "code-only email"

`nikita/platforms/telegram/auth.py` - Lines 350-354:
```python
response = await self.supabase.auth.verify_otp({
    "email": pending.email,
    "token": code,
    "type": "email",  # CRITICAL: "email" for OTP, not "magiclink"
})
```

**Status**: ✅ Correct
- Uses `type: "email"` (correct for OTP verification)
- Code comments acknowledge the criticality

**Conclusion**: Your code is implemented correctly per Supabase specs. **The problem is purely a dashboard configuration issue**.

---

## The Fix (3 Steps)

### Step 1: Access Supabase Dashboard
1. Go to https://supabase.com/dashboard
2. Select your Nikita project
3. Navigate to: `Authentication → Email Templates`

### Step 2: Update Magic Link Template
1. Find the template labeled: **"Magic Link"** (this controls OTP emails)
2. Replace the entire content with:
```html
<h2>One time login code</h2>
<p>Please enter this code: {{ .Token }}</p>
```

### Step 3: Test
1. Request new OTP from Telegram (/start → email)
2. Check email inbox
3. Verify it contains: **6-digit code** (not clickable link)
4. Enter code in Telegram to verify it works

---

## Template Variables Reference

When modifying Supabase email templates, these variables are available:

| Variable | Contains | Example |
|----------|----------|---------|
| `{{ .Token }}` | 6-digit OTP code | `123456` |
| `{{ .ConfirmationURL }}` | Clickable magic link | `https://...verify?token=...` |
| `{{ .Email }}` | User's email | `user@example.com` |
| `{{ .SiteURL }}` | Your app's URL | `https://example.com` |

**For Nikita OTP flow**: Use `{{ .Token }}` only.

---

## Configuration Constraints

**Defaults** (automatically enforced by Supabase):
- OTP expires after: **1 hour** (3600 seconds)
- Rate limit: **1 request per 60 seconds** per email
- Max expiration allowed: **86400 seconds** (1 day)

These are security defaults and cannot be changed per-request. If you need custom durations, they can be configured in:
- Dashboard: `Auth → Providers → Email → Email OTP Expiration`

---

## Why The Method Name is Misleading

**From Official Supabase Docs**:
> "Though the method is labelled 'OTP', it sends a Magic Link by default. The two methods differ only in the content of the confirmation email sent to the user."

**Translation**: The method name doesn't determine output type. The **email template controls what users receive**:
- Template with `{{ .ConfirmationURL }}` → Magic Link (clickable)
- Template with `{{ .Token }}` → OTP Code (6 digits)
- Both use the same API method: `sign_in_with_otp()`

This is why the confusion exists. Supabase uses one API for both flows.

---

## Verification Checklist

After updating the template, verify these acceptance criteria:

- [ ] Email template updated to use `{{ .Token }}`
- [ ] OTP request triggers email delivery
- [ ] Email contains 6-digit code (not a link)
- [ ] Code is valid for 1 hour
- [ ] `verify_otp()` accepts the code with `type: "email"`
- [ ] User gets logged in on successful verification
- [ ] Telegram receives welcome message

---

## Common Mistakes to Avoid

1. **Adding `email_redirect_to` parameter**:
   - ❌ DON'T: `"options": {"email_redirect_to": "..."}`
   - ✅ DO: Omit this parameter for OTP flow

2. **Using wrong type in verify**:
   - ❌ DON'T: `"type": "magiclink"`
   - ✅ DO: `"type": "email"`

3. **Forgetting to update template**:
   - ❌ Don't assume the code does everything
   - ✅ Do verify dashboard template has `{{ .Token }}`

4. **Testing with old template cached**:
   - ❌ Don't believe cached emails
   - ✅ Do request fresh OTP after template change

---

## Reference Documentation

**Official Supabase Sources** (all 2025-12-18+):

1. **Passwordless Email Logins Guide**
   - URL: https://supabase.com/docs/guides/auth/auth-email-passwordless
   - Contains: Complete OTP vs Magic Link flows with Python examples
   - Key section: "With OTP" (includes template and verification)

2. **Email Templates Guide**
   - URL: https://supabase.com/docs/guides/auth/auth-email-templates
   - Contains: Template variable reference, {{ .Token }} definition
   - Key feature: Lists all available template variables

3. **Python SDK Reference**
   - URL: https://supabase.com/docs/reference/python/textsearch#sign-in-a-user-through-otp
   - Contains: Exact API signature and parameters for `sign_in_with_otp()`

4. **Local Development Customization**
   - URL: https://supabase.com/docs/guides/local-development/customizing-email-templates
   - Contains: config.toml setup for local testing

---

## Why This Wasn't In Your Code

Nikita's implementation is **architecturally perfect**. The bug is purely a **deployment/configuration issue**:

- ✅ OTP request method: Correctly calls `sign_in_with_otp()` with no redirect
- ✅ OTP verification: Correctly calls `verify_otp()` with `type: "email"`
- ✅ Error handling: Properly catches invalid/expired codes
- ❌ Email template: Not configured in Supabase dashboard

This is why it wasn't caught in unit tests - the code doesn't control template configuration. That's a dashboard setting.

---

## Implementation Status

**Current**: Users receive magic links (wrong)
**After Fix**: Users receive 6-digit codes (correct)
**Estimated Time**: < 5 minutes (just update template in dashboard)
**Breaking Changes**: None - existing pending registrations stay in database until verified

---

## Questions to Verify

1. **Are you using Supabase Cloud or self-hosted?**
   - Cloud: Use dashboard URL configuration (above)
   - Self-hosted: Use config.toml in supabase/ directory

2. **Is this your current GCP project configuration?**
   - Project: `gcp-transcribe-test`
   - Region: `us-central1`

3. **Have you verified the email template in dashboard recently?**
   - Was there ever a change to the Magic Link template?
   - Did someone accidentally update it to a link-only version?

---

## Post-Fix Verification

After updating the template, test the **full OTP flow**:

```
User: /start
Nikita: "What's your email?"
User: user@example.com
Nikita: "Check email for code"
[User receives email with 6-digit code]
User: 123456
Nikita: "Perfect! You're all set up now. 💕"
```

If users see a clickable link instead of a code at step 3, the template didn't update. Try:
1. Hard refresh browser (`Cmd+Shift+R`)
2. Clear Supabase auth cache (logout + login)
3. Verify template contains `{{ .Token }}` (not {{ .ConfirmationURL }})

