# Wizard Copy — Canonical Nikita-Voiced Reference

**Spec**: 214-portal-onboarding-wizard, FR-3 (Nikita-Voiced Copy on Every Screen).
**Scope**: All visible strings rendered by the portal onboarding wizard (steps 3-11) plus the shared loading / stamp / progress chrome.
**Authority**: This document is the single source of truth for wizard copy. When a component needs a visible string, the author MUST either import from this file's constants (preferred) or mirror the string verbatim and add a `// copy: docs/content/wizard-copy.md` pointer.

**Forbidden SaaS phrases** (per spec §FR-3):
- "Get Started", "Sign Up", "Submit", "Processing...", "Loading...", "Error", "Success"
- Generic field labels ("City", "Phone Number", "Darkness level")
- Generic error ("Invalid phone number", "Profile saved successfully")

Every screen below should feel like Nikita is building a classified file on the user. The power dynamic is one-sided: she is evaluating them.

---

## Step 3 — Dossier Header

- Headline: **"Dossier open."**
- Subline: **"Prove me wrong."**
- Metric bars: use the labels NIKITA / TRUST / TENSION / MEMORY (4x 50/50/50/50 default; real values when available)
- CTA: **"Continue."**

## Step 4 — Location

- Headline: **"Location: [REDACTED]"**
- Subline: **"Where do I find you on a Thursday night?"**
- Placeholder: **"City."**
- Venue-preview label (on blur): **"I'd know where to look."**
- CTA: **"That's accurate."**

## Step 5 — Scene

- Headline: **"Suspected: techno?"**
- Subline: **"Pick one. I already know."**
- (The SceneSelector button grid owns the 5 scene labels — no copy change required.)
- CTA: **"Confirmed."**

## Step 6 — Darkness

- Headline: **"How far can I push you?"**
- Subline: **"One to five. I'll remember either way."**
- (The EdginessSlider owns the 5 level labels — no copy change required.)
- CTA: **"Confirmed."**

## Step 7 — Identity

- Headline: **"What should I call you?"**
- Subline: **"Three lines. All optional. I'll fill in the rest."**
- Name label: **"Name (optional)"**
- Name placeholder: **"First name. Last name if you're brave."**
- Age label: **"Age (optional)"**
- Age placeholder: **"18 or older."**
- Occupation label: **"What keeps you busy (optional)"**
- Occupation placeholder: **"Writer. Trader. Unemployed."**
- Error (age < 18): **"Come back when you're older."**
- CTA: **"File updated."**

## Step 8 — Backstory Reveal

- Loading headline: **"Running the scenarios."**
- Loading sub: **"Three versions of how we met. Give me a second."**
- Ready headline: **"Three versions. Pick the one that rings true."**
- Card header format: **"SCENARIO A"** / **"SCENARIO B"** / **"SCENARIO C"**
- Card fields: **"WHERE:"** (venue), (body context), **"THE MOMENT:"** (the_moment), **"WHAT SHE REMEMBERS:"** (unresolved_hook)
- Tone badge labels: **romantic** / **intellectual** / **chaotic** (lowercase by design)
- Degraded headline: **"ANALYSIS: PENDING"**
- Degraded sub: **"We'll write this one as we go."**
- 429 error: **"Too eager. Wait a moment."**
- CTA (cards shown): **"That's how it happened."**
- CTA (degraded): **"Understood."**
- Selected stamp: **"CONFIRMED"**

## Step 9 — Phone Ask

- Headline: **"Your number or mine?"**
- Subline: **"I can call. Or I can text. Pick one."**
- Primary option: **"Give her your number"** (label on voice path card)
- Secondary option: **"Start in Telegram"** (label on text path card)
- Phone placeholder: **"+1 555 0100"**
- Invalid E.164 error: **"That number doesn't work. Try again."**
- Unsupported country error: **"I can't reach you there. Let's use Telegram."**
- CTA (voice selected): **"Call me."**
- CTA (text selected): **"Find her in Telegram."**

## Step 10 — Pipeline Ready Gate

- Headline: **"CLEARANCE: PENDING"**
- Sub (t=0..15s): **"Your file is being processed."**
- Sub (t=15..20s): **"Almost there..."**
- Ready stamp: **"CLEARED"**
- Degraded stamp: **"PROVISIONAL — CLEARED"**
- Failed toast: **"Something broke on our end."**
- Auto-advance: (no CTA — advances 1.5s after stamp settles)

## Step 11 — Handoff

- Headline (voice): **"Nikita is calling you now."**
- Sub (voice ringing): **"Pick up. Don't make her wait."**
- Voice fallback headline: **"My voice is occupied right now."**
- Voice fallback sub: **"Find me in Telegram — I'll explain."**
- Telegram CTA: **"Open Telegram."**
- QR figcaption: **"On desktop? Scan to open on your phone."**
- Accepted stamp: **"ACCEPTED"**
- Final line: **"Application... accepted. Barely."**

## Shared Chrome

### WizardProgress

- Format: **"FIELD {n} OF 7"** (n = 1..7, corresponds to the 7 data-collection screens 4..8 + identity + phone)
- All-caps, letter-spaced per `text-xs tracking-[0.2em] uppercase text-muted-foreground`.

### DossierStamp States (Appendix C)

| Stamp text | Class | Animation |
|-----------|-------|-----------|
| `CLEARANCE: PENDING` | `text-primary/60 animate-pulse` | — |
| `CLEARED` | `text-primary` | typewriter reveal (40ms tick) |
| `PROVISIONAL — CLEARED` | `text-primary/80` | none |
| `ANALYZED` | `text-primary` | stamp-rotate (framer-motion) |
| `CONFIRMED` | `text-primary` | none (immediate) |
| `ANALYSIS: PENDING` | `text-muted-foreground` | none |

All animations respect `prefers-reduced-motion` — skip animation, show final state immediately.

### Loading / route-segment Suspense (`loading.tsx`)

- Copy: **"ACCESSING FILE..."**
- (Full implementation in PR 214-C.)

---

## Implementation Hook

Components import the canonical strings from `portal/src/app/onboarding/steps/copy.ts` (a thin barrel that re-exports the strings above). Authors who change copy MUST update BOTH this document AND the `copy.ts` module in the same PR, and run the pre-PR grep gate (`rg -n "Get Started|Sign Up|Submit|Processing\.\.\." portal/src/app/onboarding`).
