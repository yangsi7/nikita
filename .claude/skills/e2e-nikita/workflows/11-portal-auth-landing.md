# Phase 11: Portal Auth & Landing

## Scope

Authentication flows, landing page verification, bridge auth, sign-out, and onboarding cinematic.
Portal URL: `https://portal-phi-orcin.vercel.app`

## Scenarios Covered

**Auth (S-PL)**: S-PL-001–S-PL-008
**Landing (S-PL)**: S-PL-009–S-PL-016
**Onboarding (S-PL)**: S-PL-017–S-PL-025

---

## Section A: Magic Link Login

### Steps

1. Navigate to `/login`
2. Verify: Login card visible with email input and submit button
3. Enter email: `simon.yang.ch@gmail.com`
4. Click "Send Magic Link" button
5. Wait 15s for email delivery
6. Via Gmail MCP, find the magic link email:
   ```
   mcp__gmail__search_emails(
     query="subject:sign in to Nikita OR subject:magic link from:noreply",
     max_results=3
   )
   ```
7. Read the email body, extract callback URL matching `https://.*(/auth/callback\?.*)`
   ```
   mcp__gmail__read_email(email_id="<id>")
   ```
8. Navigate to the extracted callback URL
9. Wait 5s for redirect

### Verification

- [ ] Page redirects to `/dashboard`
- [ ] Sidebar visible with player nav items (data-testid: `nav-sidebar`)
- [ ] No error toasts visible
- [ ] Session cookie set (subsequent navigation to `/dashboard` succeeds without re-login)

### DB Cross-check
```sql
SELECT id, payload->>'action' as action, created_at
FROM auth.audit_log_entries
WHERE payload->>'actor_id' IS NOT NULL
ORDER BY created_at DESC LIMIT 3;
```
**Verify**: Recent `token_exchanged` or `user_signedin` action present.

---

## Section B: Bridge Auth Flow

### Prerequisites

Generate a bridge token via Supabase or use a known test token.

```sql
-- Check for existing bridge token
SELECT token, user_id, expires_at
FROM auth_bridge_tokens
WHERE user_id = (SELECT id FROM auth.users WHERE email = 'simon.yang.ch@gmail.com')
AND expires_at > NOW()
LIMIT 1;
```

If no token exists, create one via the backend:
```bash
curl -s -X POST https://nikita-api-1040094048579.us-central1.run.app/api/v1/auth/bridge-token \
  -H "Content-Type: application/json" \
  -d '{"telegram_id": "746410893"}'
```

### Steps

1. Copy the bridge token value
2. Navigate to `/auth/bridge?token=<TOKEN>`
3. Wait 5s for auth exchange

### Verification

- [ ] Redirected to `/dashboard` (not `/login`)
- [ ] Session active (sidebar visible)
- [ ] Bridge token consumed (re-navigating to same URL fails or redirects to dashboard if session exists)

---

## Section C: Sign Out

### Prerequisites

Active authenticated session from Section A or B.

### Steps

1. From `/dashboard`, locate sign-out button in sidebar
2. Click the sign-out button
3. Wait 3s for redirect

### Verification

- [ ] Redirected to `/login`
- [ ] Navigate to `/dashboard` → redirected back to `/login` (session cleared)
- [ ] Navigate to `/admin` → redirected to `/login` (no lingering session)

---

## Section D: Landing Page (Spec 208)

### D1: Unauthenticated View

#### Steps

1. Ensure no active session (sign out first, or use incognito)
2. Navigate to `/`

#### Verification

- [ ] H1 contains "Dumped" (hero section)
- [ ] 5 sections visible: HeroSection, PitchSection, PortalShowcase, StakesSection, CtaSection
- [ ] CTA buttons contain text "Start Relationship" (unauthenticated variant)
- [ ] Sticky nav (LandingNav) appears after scrolling past hero
- [ ] Chapter timeline dots visible (data-testid: `chapter-dot`)
- [ ] Telegram mockup message bubbles visible (data-testid: `message-bubble`)

### D2: Authenticated View

#### Steps

1. Log in via magic link (Section A)
2. Navigate to `/`

#### Verification

- [ ] Landing page still renders (not redirected — `/` is public for all users)
- [ ] CTA buttons say "Go to Dashboard" (authenticated variant)
- [ ] LandingNav shows authenticated state

### D3: Auth Redirect from /login

#### Steps

1. While authenticated, navigate to `/login`

#### Verification

- [ ] Redirected to `/dashboard` (player) or `/admin` (admin user)
- [ ] Does NOT show login form

---

## Section E: Onboarding (Spec 081) — New Users Only

> **CAUTION**: Only run this section with a fresh test user or after DB wipe. Running with existing user may disrupt game state.

### Prerequisites

- Fresh user with no `onboarding_states` record, OR
- DB wipe has been performed (Phase 00)

### Steps

1. Navigate to `/onboarding`
2. Verify: 5 scroll sections render:
   - data-testid: `section-chapters` (Chapter Stepper)
   - data-testid: `section-score` (Score Ring explanation)
   - data-testid: `section-rules` (Rules)
   - data-testid: `section-profile` (Profile form)
   - data-testid: `section-mission` (Mission + submit)
3. Scroll through sections to reveal each
4. Fill profile form in `section-profile`:
   - City: "Zurich"
   - Scene select: choose any (e.g., "techno")
   - Intensity slider: set to 3
5. Scroll to `section-mission`
6. Click submit button (data-testid: `onboarding-submit-btn`)
7. Wait 5s

### Verification

- [ ] "Opening Telegram..." overlay appears after submit
- [ ] MoodOrb component renders (data-testid: `onboarding-mood-orb`)
- [ ] Chapter stepper shows 5 chapters (data-testid: `onboarding-chapter-stepper`)

### DB Cross-check
```sql
SELECT onboarded_at, city, scenario_name
FROM user_profiles
WHERE id = (SELECT id FROM auth.users WHERE email = 'simon.yang.ch@gmail.com');
```
**Verify**: `onboarded_at` is set (not null), city = 'Zurich', scenario populated.

---

## Portal Accuracy Recording

```xml
<portal_check phase="11-auth-landing">
  <route path="/login">
    <field name="email_input" visible="true|false"/>
    <field name="submit_button" visible="true|false"/>
  </route>
  <route path="/dashboard" note="post-login redirect">
    <field name="sidebar" visible="true|false"/>
    <field name="session_active" value="true|false"/>
  </route>
  <route path="/">
    <field name="hero_h1_contains_dumped" match="true|false"/>
    <field name="sections_count" expected="5" actual="..."/>
    <field name="cta_text" expected="Start Relationship|Go to Dashboard" actual="..."/>
  </route>
  <route path="/onboarding" note="new users only">
    <field name="scroll_sections" expected="5" actual="..."/>
    <field name="submit_fires_api" match="true|false"/>
  </route>
</portal_check>
```

---

## Decision Gate

- All auth flows work (magic link + bridge + sign out) → **continue to Phase 12**
- Auth broken → **CRITICAL finding, stop portal simulation**
- Landing page rendering issues → **MEDIUM finding, continue**
- Onboarding skipped (existing user) → log as OBSERVATION, continue
