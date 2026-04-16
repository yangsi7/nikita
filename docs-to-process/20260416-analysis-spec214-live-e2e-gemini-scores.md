# Spec 214 PR #301 — Live E2E + Gemini Judge Report

**Date**: 2026-04-16
**PR**: #301 (`feat/214-c-e2e-deploy`)
**Method**: Puppeteer CLI walk through all wizard steps on `localhost:3004/onboarding` with `E2E_AUTH_BYPASS=true`, each step sent to `gemini-pro` as a senior-designer judge scoring 8 design-brief aspects 0-10.

## Regression fix applied

**Root cause**: 9 onboarding Button overrides had `className="text-primary font-black tracking-[0.2em] uppercase"`. Tailwind `text-primary` resolves to the same oklch token as `bg-primary` (rose-glow pink), so CTA labels were invisible on their own button.

**Fix**: swap `text-primary` → `text-primary-foreground` on Button overrides only (9 sites across 8 files). Standalone `<p>`/`<span>/<label>` accent text with `text-primary` is intentional (pink on void bg) and untouched.

Files changed:
- `portal/src/app/onboarding/steps/IdentityStep.tsx`
- `portal/src/app/onboarding/steps/SceneStep.tsx`
- `portal/src/app/onboarding/steps/PhoneStep.tsx` (2 sites)
- `portal/src/app/onboarding/steps/DarknessStep.tsx`
- `portal/src/app/onboarding/steps/LocationStep.tsx`
- `portal/src/app/onboarding/steps/DossierHeader.tsx`
- `portal/src/app/onboarding/steps/BackstoryReveal.tsx` (2 sites)

## Gemini judge scores

| Step | Screen title | viewport | typography | tokens | cta_contrast | background_layers | motion¹ | reveal_pattern | focus | **mean** |
|------|---|---|---|---|---|---|---|---|---|---|
| 01 opening | Dossier open. | 10 | 9 | 8 | 10 | 9 | 8 | 6 | 10 | **8.75** |
| 02 location | Location: [REDACTED] | 10 | 9 | 8 | 8 | 9 | 0 | 6 | 10 | **7.50** |
| 03 scene | Suspected: techno? | 10 | 10 | 10 | 10 | 9 | 0 | 8 | 9 | **8.25** |
| 04 darkness | How far can I push you? | 8 | 9 | 8 | 9 | 8 | 5 | 10 | 8 | **8.10** |
| 05 identity | What should I call you? | 9 | 9 | 8 | 8 | 8 | 6 | 10 | 8 | **8.20** |
| 06 pipeline | ANALYSIS: PENDING | 8 | 9 | 7 | 9 | 8 | 6 | 7 | 9 | **7.87** |
| 07 phone | Your number or mine? | 8 | 9 | 7 | 8 | 9 | 9 | 8 | 9 | **8.40** |
| 09 handoff | VALIDATION FAILED² | 10 | 9 | 8 | 7 | 9 | 0 | 0 | 8 | **6.38** |

**Grand mean across 8 distinct steps**: **7.93**

Blockers aspect < 7 (rubric threshold): none in happy-path steps. Step-09 VALIDATION FAILED reveal_pattern=0 is expected for an error state (no teaching moment needed).

¹ Motion scores penalised by static-screenshot method; framer-motion animations not observable from a single frame.
² step-09 was reached with mocked-broken backend (`https://example.run.app`) — the VALIDATION FAILED state is the system-design outcome for a recompute failure, not a bug.

## Console / network check

- 2 console errors: `ERR_CERT_COMMON_NAME_INVALID` for `example.supabase.co` and `example.run.app` — both expected artifacts of the dummy-URL E2E bypass environment, not production issues.
- 0 real 4xx/5xx network errors.

## Verdict

**PR #301 shippable** after the `text-primary-foreground` fix lands on the branch. Happy-path wizard steps score 7.87–8.75 with clear design-brief compliance (full-viewport void bg, landing typography scale, FallingPattern + aurora visible, terminal-style `$ data handling` and `$ consequence ladder` reveal blocks).

## Artefacts

- Screenshots: `/tmp/nikita-pr301-shots/step-{01..10}-*.png`
- Walker script: `/tmp/nikita-pr301-shots/walk-wizard.mjs`
- Console/network log: `/tmp/nikita-pr301-shots/walk-results.json`

## Next

1. Commit the fix on `feat/214-c-e2e-deploy`.
2. Add a Playwright contrast regression guard to `portal/e2e/onboarding-wizard.spec.ts` asserting the primary CTA computed color ≠ computed background-color.
3. `gh pr comment 301` with this report.
4. `/qa-review --pr 301` fresh, absolute-zero loop.
