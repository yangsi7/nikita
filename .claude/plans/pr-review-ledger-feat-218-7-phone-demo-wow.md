# Review Ledger — feat/218-7-phone-demo-wow

## Meta
- PR: #590
- Scope: PR diff (13 changed files)
- Iteration: 1 / 5
- Severity threshold: important (pr-workflow.md requires 0 at ALL severities)
- Mode: fix
- Review type: self (iter 0) + external fresh-context (iter 1)

## Findings

| ID | File | Line | Category | Severity | Status | Iter | Reviewer |
|----|------|------|----------|----------|--------|------|----------|
| R1 | nikita/api/routes/portal_onboarding_v2.py | PhoneDemoConsentRequest | Security | important | FIXED | 0 | self |
| R2 | nikita/api/routes/portal_onboarding_v2.py | consent endpoint docstring | Style | nitpick | FIXED | 0 | self |
| R3 | nikita/api/routes/portal_onboarding_v2.py | end-call endpoint docstring | Style | nitpick | FIXED | 0 | self |
| R4 | portal/src/app/onboarding/v2/phone_demo_takeover.tsx | 82-84 | Correctness | important | FIXED | 0 | self |
| R5 | portal/src/__tests__/app/onboarding/v2/ | — | Testing | nitpick | OPEN | 0 | self |
| R6 | nikita/api/routes/voice.py | 489 | Correctness | nitpick | ACCEPTED | 0 | self |

## Fix Log

### Iteration 0 (initial self-review)
- R1: Added `pattern=r"^\+[1-9]\d{7,14}$"` to PhoneDemoConsentRequest.phone_e164 Field()
- R2: Removed stale "Stub — GREEN phase provides full implementation." from consent endpoint docstring
- R3: Removed stale "Stub — GREEN phase provides full implementation." from end-call endpoint docstring
- R4: Fixed ceiling_timeout Realtime status mapping — three-way ternary now maps "ceiling_timeout" → "ceiling_timeout" instead of "ended_error"
- R5: No behavioral tests for PhoneDemoTakeover component (Realtime subscription, ceiling timer, End early POST). pr-workflow.md 0-findings gate includes nitpicks. OPEN — needs resolution.
- R6: `status="ended_success"` hardcoded in webhook piggyback (voice.py:489). ACCEPTED as design: `post_call_transcription` fires only on successful call completion (busy/no-answer produce `call_initiation_failure`/`call_ended`, not this event). Correct by construction.
- Fixes committed at 5e71795, pushed to remote

### Iteration 1 (external fresh-context re-review)
- In progress
