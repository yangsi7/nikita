# Next Steps
Feature: 081-onboarding-redesign-progressive-discovery
After Phase: 7 (Audit — PASS)
Generated: 2026-03-22T14:00:00Z

## Immediate Next
Phase 8 (Implementation): TDD per user story, starting with US-1 (magic link auth bridge)

## Resume Command
`/sdd implement 081` or `/implement`

## Context Summary
- Portal-first cinematic onboarding replaces current Telegram-only flow
- 33 tasks across 8 user stories (~65hr estimate)
- 3 parallel work streams: A=backend, B=portal, C=post-merge
- All gates passed: GATE 1 (spec), GATE 2 v2 (12 validators), GATE 3 (audit)
- Key files to read first: spec.md, plan.md, tasks.md in specs/081-*/

## Critical Files for Implementation
- `nikita/platforms/telegram/otp_handler.py` — Replace voice/text choice with magic link (~line 326)
- `nikita/platforms/telegram/auth.py` — Add generate_portal_magic_link() method
- `nikita/api/routes/onboarding.py` — Add POST /profile endpoint (file exists)
- `portal/src/app/onboarding/` — New route (cinematic scroll experience)
- `portal/src/components/onboarding/` — New components (ChapterStepper, SceneSelector, EdginessSlider, RuleCard, ProfileForm)
- `portal/src/app/auth/callback/route.ts` — Verify ?next= param works
