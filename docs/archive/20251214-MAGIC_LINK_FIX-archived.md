# Magic Link Authentication Fix

## Issue Summary

**Problem:** Magic links from Telegram registration were expiring (60s timeout) and showing unhelpful error messages when users clicked expired links.

**Root Causes:**
1. Supabase magic links expire after 60 seconds
2. No error handling for expired/invalid links on `/auth/confirm` endpoint
3. Errors sent in URL fragment (`#error=...`) not displayed to user

## Fixes Applied

### 1. Enhanced Error Handling (`nikita/api/routes/telegram.py`)

**Location:** `/api/v1/telegram/auth/confirm` endpoint (line 304)

**Changes:**
- Added query parameters: `error`, `error_code`, `error_description`
- JavaScript to extract errors from URL fragment and reload as query params
- User-friendly error page with red gradient background
- Specific error messages for:
  - `otp_expired`: "Magic link expired (60 second timeout)"
  - `otp_disabled`: "Magic link has already been used"
  - `access_denied`: "Invalid or expired authentication link"
- Clear instructions to request new link via `/start` in Telegram

### 2. Portal URL Support (`nikita/config/settings.py`)

**Location:** Line 69-73

**Changes:**
- Added `portal_url` field for Vercel deployment URL
- Optional field (defaults to `None`)
- Example: `https://nikita-portal.vercel.app`

### 3. Dual Registration Flow Support (`nikita/platforms/telegram/auth.py`)

**Location:** `TelegramAuth.register_user()` method (line 48)

**Changes:**
- Added `registration_source` parameter (`"telegram"` or `"portal"`)
- Dynamic redirect URL selection:
  - **Telegram flow**: Redirects to `backend/api/v1/telegram/auth/confirm` (shows instruction page)
  - **Portal flow**: Redirects to `portal_url/auth/callback` (exchanges code for session)

## Environment Variables

Add to Cloud Run deployment:

```bash
# Optional - for portal login flow
PORTAL_URL=https://nikita-portal.vercel.app
```

## Deployment Steps

### 1. Deploy Backend Changes

```bash
# Build and deploy to Cloud Run
gcloud run deploy nikita-api \
  --source . \
  --region us-central1 \
  --project gcp-transcribe-test \
  --set-env-vars "PORTAL_URL=https://nikita-portal.vercel.app"
```

### 2. Test with Fresh Magic Link

```bash
# 1. Go to Telegram bot
# 2. Send: /start
# 3. Follow email registration flow
# 4. Click magic link within 60 seconds
# 5. Should see "Email Verified!" page
# 6. Return to Telegram to complete registration
```

### 3. Test Expired Link

```bash
# 1. Request magic link via Telegram
# 2. Wait 61+ seconds
# 3. Click link
# 4. Should see red error page with clear instructions
```

## Files Changed

1. `nikita/api/routes/telegram.py` - Error handling for auth endpoint
2. `nikita/config/settings.py` - Added `portal_url` field
3. `nikita/platforms/telegram/auth.py` - Dual registration flow support

## User Experience Improvements

**Before:**
- Expired link shows generic JSON error
- User confused about next steps
- No guidance on how to fix

**After:**
- Expired link shows user-friendly error page
- Clear error message with reason
- Step-by-step instructions to request new link
- Telegram link button for easy return

## Future Enhancements

1. **Increase OTP timeout** - Consider configuring Supabase to extend magic link validity beyond 60s
2. **Email retry** - Add "Resend magic link" button on error page
3. **Portal registration** - When portal is deployed, add registration form that sets `registration_source="portal"`
4. **Rate limiting** - Prevent magic link spam by limiting requests per email/telegram_id

## Notes

- Magic links are single-use (clicking twice will show "already used" error)
- Users must complete registration in Telegram even after email verification
- Portal flow will require separate registration form (not yet implemented)
