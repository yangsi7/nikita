---
title: Voice Onboarding Archive — Spec 028 Superseded
lifecycle: archived
---

# Voice Onboarding Archive (Spec 028 — Superseded)

**Status**: HISTORICAL ARTIFACT. DO NOT CONSULT.

## Archived

Date: 2026-05-18. Driving PR: Spec 219 C4 (feature/219-legacy-telegram-cleanup).

## Reason

Spec 028 voice onboarding (Meta-Nikita ElevenLabs agent) was superseded by the portal wizard (`nikita/api/routes/portal_onboarding_v2.py`) introduced in Spec 214/216. The ElevenLabs Meta-Nikita agent, its server tools, and the voice flow are no longer exercised in any live path. The `/api/v1/onboarding/*` router was unmounted from `nikita/api/main.py`.

## Where to find current canonical

| Topic | Current canonical |
|-------|------------------|
| Onboarding flow | `nikita/api/routes/portal_onboarding_v2.py` |
| Onboarding handoff (still live) | `nikita/onboarding/handoff.py` |
| Onboarding contracts (still live) | `nikita/onboarding/contracts.py` |
| Voice agent (Nikita, not Meta-Nikita) | `nikita/agents/voice/` |
| Portal wizard routes | `nikita/api/routes/portal_onboarding_v2.py` |

## Archived files

| File | Original path |
|------|--------------|
| `onboarding-route.py` | `nikita/api/routes/onboarding.py` |
| `voice_flow.py` | `nikita/onboarding/voice_flow.py` |
| `meta_nikita.py` | `nikita/onboarding/meta_nikita.py` |
| `server_tools.py` | `nikita/onboarding/server_tools.py` |
| `test_routing.py` | `tests/platforms/telegram/test_routing.py` |
| `test_telegram.py` | `tests/api/routes/test_telegram.py` |
| `test_registration_handler.py` | `tests/platforms/telegram/test_registration_handler.py` |
| `test_otp_handler.py` | `tests/platforms/telegram/test_otp_handler.py` |
| `test_otp_handler_onboarding.py` | `tests/platforms/telegram/test_otp_handler_onboarding.py` |

## Top staleness items

- Meta-Nikita ElevenLabs agent ID `agent_4801kewekhxgekzap1bqdr62dxvc` may have been deleted from the dashboard
- Server tool route `/api/v1/onboarding/server-tool` no longer exists in production
- The `onboarding_status` column in `users` table is still present; portal wizard writes to it via `handoff.py`
