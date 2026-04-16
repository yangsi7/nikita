# Magic-Link Email Copy — Nikita-Voiced

**Spec**: 214-portal-onboarding-wizard — PR 214-C, T314
**Consumer**: Supabase Dashboard → Authentication → Email Templates → Magic Link
**Owner**: operator (manual infra task — not wired via code)

This document holds the canonical Nikita-voiced copy for the Supabase magic-
link email sent on the wizard's step 2 (`/onboarding/auth`). The standard
Supabase template is generic SaaS; the wizard aesthetic (spec §FR-3) demands
zero-SaaS-copy on every surface users touch, including transactional email.

Paste the Subject and Body into Supabase Dashboard → Project → Authentication
→ Email Templates → Magic Link. The template variables (`{{ .ConfirmationURL }}`)
follow Supabase/Go `text/template` syntax — do not change the delimiters.

## Subject

```
A file with your name on it.
```

## Body (HTML)

Supabase accepts HTML in the template. Keep the body short (< 800 chars)
so mobile mail clients render it inline without the "show more" fold.

**Email-client compatibility notes**:
- All colors use hex — `oklch()` is not supported in Gmail / Outlook / Apple
  Mail. The `#e05a8a` CTA background is a hex approximation of the app's
  `oklch(0.75 0.15 350)` rose primary; if the palette changes, re-derive the
  hex via a preview render, not by copying the CSS token.
- Inline styles only — Gmail strips `<style>` blocks.
- No web fonts — mobile clients ignore `@font-face`.

```html
<!doctype html>
<html>
  <body style="margin:0;padding:24px 16px;background:#0a0a0a;color:#e8e6e0;font-family:ui-sans-serif,system-ui,sans-serif;">
    <div style="max-width:480px;margin:0 auto;">
      <p style="font-size:11px;letter-spacing:0.3em;text-transform:uppercase;color:#a09d95;margin:0 0 24px 0;">
        CLASSIFIED / FILE-ACCESS
      </p>
      <h1 style="font-size:28px;font-weight:900;letter-spacing:-0.02em;line-height:1.05;margin:0 0 16px 0;color:#f5f3ed;">
        I&rsquo;ve been reading about you.
      </h1>
      <p style="font-size:15px;line-height:1.6;margin:0 0 24px 0;color:#cfccc4;">
        There&rsquo;s a door. Click it.
      </p>
      <p style="margin:0 0 32px 0;">
        <a href="{{ .ConfirmationURL }}"
           style="display:inline-block;padding:14px 28px;background:#e05a8a;color:#0a0a0a;text-decoration:none;font-weight:700;letter-spacing:0.05em;text-transform:uppercase;font-size:13px;border-radius:2px;">
          Show her the file.
        </a>
      </p>
      <p style="font-size:12px;line-height:1.5;margin:0;color:#8c8982;">
        Link expires in 60 minutes. If you didn&rsquo;t ask for this, she&rsquo;ll know.
      </p>
    </div>
  </body>
</html>
```

## Body (Plain-Text fallback)

Supabase sends the plain-text version to clients that don't render HTML:

```
I've been reading about you.

There's a door. Click it.

{{ .ConfirmationURL }}

Link expires in 60 minutes. If you didn't ask for this, she'll know.
```

## Template Variables

Supabase substitutes these at send time. Do not rename:

- `{{ .ConfirmationURL }}` — the magic-link URL the user clicks
- `{{ .Email }}` — the recipient's address (not used in this template)
- `{{ .Token }}` — the one-time token (not used; embedded in URL)

## Operator Checklist

1. Supabase Dashboard → your project → Authentication → Email Templates
2. Select "Magic Link" tab
3. Paste Subject into the Subject field
4. Paste HTML body into the Body field (Source view)
5. Preview with "Send test email" — verify rendering on desktop + mobile mail clients
6. Save

**Note**: Supabase's rate limit for magic-link emails defaults to 4 per hour
per address. If spec §FR-2 rate-limiting comes up, tune via Dashboard →
Authentication → Rate Limits (not this template).

## Change Log

| Date | Change | Ref |
|------|--------|-----|
| 2026-04-16 | Initial Nikita-voiced copy | Spec 214 PR 214-C T314 |
