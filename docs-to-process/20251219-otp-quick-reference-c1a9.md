# Supabase OTP vs Magic Link - Quick Reference

## TL;DR: Why You're Getting Magic Links

**Root Cause**: Supabase email template uses default (Magic Link) instead of OTP template.

**The Fix**:
1. Dashboard → Auth → Email Templates → Magic Link
2. Replace template with: `<p>Please enter this code: {{ .Token }}</p>`
3. Save & test

**Time**: < 5 minutes

---

## The Confusion Explained

```
Method Name:    sign_in_with_otp()
├─ Sounds like: "sends OTP codes"
└─ Actually sends: Magic Links BY DEFAULT

What Determines Output:
├─ Template with {{ .ConfirmationURL }} → Magic Link (clickable)
├─ Template with {{ .Token }} → OTP Code (6 digits)
└─ Both use the SAME method name
```

**Official Quote**: "Though the method is labelled 'OTP', it sends a Magic Link by default."

---

## Nikita Code Status

✅ `send_otp_code()` - Correct
- Calls `sign_in_with_otp()` without `email_redirect_to`
- Comment notes "code-only email"

✅ `verify_otp_code()` - Correct
- Calls `verify_otp()` with `type: "email"`
- Handles invalid/expired codes properly

❌ **Problem is NOT in code** - It's in Supabase dashboard template configuration

---

## Template Variables

| Use | Variable | Template |
|-----|----------|----------|
| **OTP Code** | `{{ .Token }}` | `<p>Code: {{ .Token }}</p>` |
| **Magic Link** | `{{ .ConfirmationURL }}` | `<a href="{{ .ConfirmationURL }}">Click me</a>` |
| **Hashed Token** | `{{ .TokenHash }}` | For PKCE flow (advanced) |
| **User Email** | `{{ .Email }}` | For personalization |

---

## OTP Flow (Correct Implementation)

### Send OTP
```python
await supabase.auth.sign_in_with_otp({
    "email": "user@example.com",
    "options": {
        "should_create_user": True,
        # Don't include email_redirect_to
    }
})
```
✅ Nikita does this correctly

### Verify OTP
```python
response = await supabase.auth.verify_otp({
    "email": "user@example.com",
    "token": "123456",  # 6-digit code from email
    "type": "email"     # CRITICAL: "email" not "magiclink"
})
```
✅ Nikita does this correctly

---

## Configuration Constraints

| Setting | Default | Max | Configurable |
|---------|---------|-----|--------------|
| OTP Expiration | 1 hour | 86400s (1 day) | Yes (dashboard) |
| Rate Limit | 60 sec | - | Yes (dashboard) |
| Code Length | 6 digits | - | No |

---

## Error Messages You'll See

| Code | Meaning | User Action |
|------|---------|-------------|
| "Invalid OTP code" | Wrong 6 digits | Re-check email and try again |
| "OTP has expired" | >1 hour since sent | Request new code |
| "No pending registration" | Skipped send step | Start from /start |
| "Token has expired or is invalid" | Any verification failure | Request fresh code |

---

## Comparison: Magic Link vs OTP

| Aspect | Magic Link | OTP Code |
|--------|-----------|----------|
| **Email contains** | Clickable link | 6-digit number |
| **User experience** | 1 click to login | Paste 6 digits |
| **Security** | Susceptible to link prefetching | Resistant to automation |
| **Template variable** | `{{ .ConfirmationURL }}` | `{{ .Token }}` |
| **Verification type** | `"magiclink"` | `"email"` |
| **Best for** | Desktop email clients | Mobile + security |

---

## For Local Development (Self-Hosted)

If running Supabase locally, edit `supabase/config.toml`:

```toml
[auth.email.template.magic_link]
subject = "Your OTP Code"
content_path = "./supabase/templates/magic_link.html"
```

Then create `supabase/templates/magic_link.html`:
```html
<h2>One time login code</h2>
<p>Please enter this code: {{ .Token }}</p>
```

Restart containers: `supabase stop && supabase start`

---

## Verification Checklist

After template update:
- [ ] Request OTP via Telegram (/start)
- [ ] Check email inbox
- [ ] See 6-digit code (not clickable link)
- [ ] Try wrong code → "Invalid OTP" error
- [ ] Wait 1+ hour → "Expired" error
- [ ] Enter correct code → Login success

---

## Official Sources

- **Passwordless Flows**: https://supabase.com/docs/guides/auth/auth-email-passwordless
- **Email Templates**: https://supabase.com/docs/guides/auth/auth-email-templates
- **Python SDK**: https://supabase.com/docs/reference/python/textsearch#sign-in-a-user-through-otp

---

## Why This Matters

**Supabase design decision**: One API (`sign_in_with_otp`) for two flows
- **Pro**: Flexible, handles both use cases
- **Con**: Method name is misleading, requires template understanding
- **Solution**: Know that template controls output type, not the method

This is working as designed by Supabase. Not a bug - it's a configuration issue.

