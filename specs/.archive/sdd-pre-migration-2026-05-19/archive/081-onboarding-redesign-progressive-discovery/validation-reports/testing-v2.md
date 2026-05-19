## Testing Validation Report

**Spec:** specs/081-onboarding-redesign-progressive-discovery/spec.md (v2)
**Status:** PASS
**Timestamp:** 2026-03-22T12:00:00Z

### Summary
- CRITICAL: 0
- HIGH: 0
- MEDIUM: 4
- LOW: 3

### Findings

| Severity | Category | Issue | Location | Recommendation |
|----------|----------|-------|----------|----------------|
| MEDIUM | E2E Tests | No accessibility E2E test for `/onboarding` despite detailed ARIA spec (role=radiogroup, role=slider, keyboard nav) | spec.md:1663-1678 | Add E2E-11: Verify `role="radiogroup"` on SceneSelector, `role="slider"` on EdginessSlider, keyboard arrow key interaction on slider, Tab order through all interactive elements. The spec defines 10+ ARIA requirements (lines 1073-1088) but zero E2E tests verify them. |
| MEDIUM | E2E Tests | No `prefers-reduced-motion` E2E test despite being a functional requirement in FR-002 and animation spec | spec.md:170, 1085 | Add E2E-12: Use `page.emulateMedia({ reducedMotion: 'reduce' })`, navigate to `/onboarding`, verify that score ring appears immediately without animation (no count-up, no scale-in). Playwright supports this natively. |
| MEDIUM | Unit Tests | No unit tests specified for `OnboardingProfileRequest` Pydantic model validation edge cases | spec.md:1330-1333 | The profile endpoint tests (lines 1626-1633) cover invalid scene, empty location, and out-of-range drug_tolerance, but do not cover: location with only whitespace (`"   "`), location exceeding max_length (100 chars), SQL injection strings in location, or non-string scene values. Add 3-4 edge case tests to `test_onboarding_profile.py`. |
| MEDIUM | Integration Tests | No integration test for the full OTP-to-portal-redirect flow end-to-end (Telegram side) | spec.md:1656-1661 | The integration test at line 1660 says "Full OTP verification -> magic link flow (mocked Supabase)" but this is a single test covering the entire multi-step flow. Consider splitting into: (a) OTP verify -> magic link generated -> correct button URL, (b) OTP verify -> magic link fails -> fallback URL in button. Two focused tests are more debuggable than one monolith. |
| LOW | E2E Tests | E2E-2 ("Score ring displays with animated entrance") is difficult to assert deterministically | spec.md:1670 | Animated entrance testing is inherently flaky. Consider verifying the score ring is visible and shows the expected value (75) rather than asserting animation state. The existing dashboard E2E tests (dashboard.spec.ts) follow this pattern -- assert content, not animation. |
| LOW | Unit Tests | DripManager tests (14 tests) listed under Phase 2 but counted in the ~30 unit test total | spec.md:1642-1645 | Clarify whether Phase 2 DripManager tests are part of the Phase 1 test count or deferred. If deferred, the Phase 1 unit test count drops to ~16 tests, which is still adequate for the scope. |
| LOW | Mock Strategy | Mock for `window.open()` in CTA deep link test not explicitly specified | spec.md:1676 | E2E-8 intercepts the POST request (correct), but the subsequent `window.open("tg://resolve...")` call will trigger a navigation error in Playwright. Add `page.on('dialog', ...)` or mock the `tg://` protocol handler to prevent test flakiness. Alternatively, verify only the POST body and response, then assert the button click occurred (not the protocol navigation). |

### Testing Pyramid Analysis

```
Target Pyramid:          Spec Pyramid (Phase 1):

     /\                       /\
    /E2E\  10%               /E2E\  ~22% (10 tests)
   /------\                 /------\
  / Integ  \ 20%           / Integ  \ ~13% (6 tests)
 /----------\             /----------\
/ Unit Tests \ 70%       / Unit Tests \ ~65% (30 tests, incl. Phase 2)
--------------           ---------------

Phase 1 only (excl. 14 DripManager):
  Unit: 16 tests (~52%)
  Integration: 6 tests (~19%)
  E2E: 10 tests (~32%)
```

**Assessment:** The E2E percentage is higher than the 10% target, and the unit test percentage is lower than 70%. However, this is appropriate for a feature that is heavily UI-driven with a new portal page, form interactions, and scroll behavior. The E2E tests cover critical user-facing flows that cannot be adequately tested at lower levels. The pyramid deviation is justified by the feature's nature.

If Phase 2 DripManager unit tests (14 tests) are included in the Phase 1 scope, the pyramid balances to ~65/13/22 which is closer to target. Either way, the deviation is within acceptable bounds for a UI-heavy feature.

### AC Testability Analysis

| AC ID | AC Description | Testable | Test Type | Issue |
|-------|----------------|----------|-----------|-------|
| AC-1.1 | After OTP, player sees "Enter Nikita's World" button | Yes | Unit | Covered by `_offer_onboarding_choice` test (line 1617) |
| AC-1.2 | Button URL is valid Supabase magic link | Yes | Unit | Covered by `_generate_portal_magic_link` success test (line 1613) |
| AC-1.3 | Clicking button authenticates + lands on /onboarding | Partial | Integration | Covered by integration test (line 1660), but Supabase auth exchange is mocked |
| AC-1.4 | Magic link failure falls back to regular URL | Yes | Unit | Covered by fallback test (line 1618) |
| AC-2.1 | Section 1 displays ScoreRing with 75 | Yes | E2E | Covered by E2E-2 (line 1670) |
| AC-2.2 | Four metric cards appear | Yes | E2E | Covered by E2E-1 (line 1669) |
| AC-2.3 | Nikita quote explains scoring | Yes | E2E | Covered implicitly by E2E-1 section check |
| AC-2.4 | Score ring animates + respects reduced-motion | Partial | E2E | Animation tested by E2E-2; reduced-motion NOT tested (MEDIUM finding) |
| AC-3.1 | Chapter stepper with 5 chapters | Yes | E2E | Covered by E2E-3 (line 1671) |
| AC-3.2 | Chapter 1 highlighted with rose glow | Yes | E2E | Covered by E2E-3 |
| AC-3.3 | Chapters 2-5 locked with lock icons | Yes | E2E | Covered by E2E-3 |
| AC-3.4 | Chapter names + locked "???" descriptions | Yes | E2E | Covered by E2E-3 |
| AC-3.5 | Nikita quote teases journey | Yes | E2E | Implicitly covered by section rendering |
| AC-4.1 | Rules section: 4 GlassCards, 2x2 desktop / 1-col mobile | Yes | E2E | Desktop: E2E-4 (line 1672), Mobile: E2E-10 (line 1678) |
| AC-4.2 | Cards cover scoring, time, boss, vices | Yes | E2E | Covered by E2E-4 |
| AC-4.3 | Card text in Nikita's voice | No (subjective) | Manual | Voice/tone is not machine-testable; verify in code review |
| AC-4.4 | Cards have hover/tap interactions | Partial | E2E | Not explicitly tested; hover state is CSS-only, low risk |
| AC-5.1 | Profile section: location + SceneSelector + EdginessSlider | Yes | E2E | Covered by E2E-5, E2E-6, E2E-7 |
| AC-5.2 | SceneSelector: 5 cards, tap selects with rose glow | Yes | E2E | Covered by E2E-5 (line 1673) |
| AC-5.3 | EdginessSlider: 1-5, emoji previews, current display | Yes | E2E | Covered by E2E-6 (line 1674) |
| AC-5.4 | Location validates non-empty | Yes | E2E + Unit | E2E-7 (line 1675) + unit empty location test (line 1628) |
| AC-5.5 | Form data in React state, no intermediate server calls | Yes | E2E | E2E-8 verifies POST only fires on CTA click |
| AC-6.1 | Section 5 CTA "Start Talking to Nikita" | Yes | E2E | Covered by E2E-1 + E2E-8 |
| AC-6.2 | CTA submits profile then opens tg:// deep link | Yes | E2E | Covered by E2E-8 (line 1676) |
| AC-6.3 | Profile failure shows inline error | Yes | E2E | Not explicitly a separate E2E test, but E2E-7 covers validation errors |
| AC-6.4 | tg:// fallback to https://t.me/ | No (platform) | Manual | Protocol handler behavior depends on OS; not testable in headless Chromium |
| AC-6.5 | onboarding_completed_at set after profile save | Yes | Unit + Integration | Unit (line 1632) + Integration (line 1653) |
| AC-7.1 | 5-min fallback fires if no portal completion | Yes | Unit | Covered by fallback test (line 1638) |
| AC-7.2 | Fallback offers text onboarding | Yes | Unit | Covered by fallback message test (line 1640) |
| AC-7.3 | Fallback suppressed if portal completed | Yes | Unit | Covered by discard test (line 1639) |
| AC-7.4 | Text-onboarded player sees /dashboard not /onboarding | Yes | E2E | Covered by E2E-9 (line 1677) |
| AC-8.1 | Returning user redirected to /dashboard | Yes | E2E | Covered by E2E-9 (line 1677) |
| AC-8.2 | Unauthenticated user redirected to /login | Yes | E2E | Implicitly covered by existing auth-flow.spec.ts patterns |
| AC-8.3 | Redirect is server-side (no flash) | Partial | E2E | E2E-9 can verify URL change, but "no flash" is hard to assert deterministically |

### Test Scenario Inventory

**E2E Scenarios:**
| Scenario | Priority | User Flow | Status |
|----------|----------|-----------|--------|
| E2E-1: All 5 sections render | P1 | New player visits /onboarding | Specified |
| E2E-2: Score ring displays | P1 | Section 1 content verification | Specified |
| E2E-3: Chapter stepper (5 chapters, Ch.1 active) | P1 | Section 2 content verification | Specified |
| E2E-4: Rules section (4 glass cards) | P1 | Section 3 content verification | Specified |
| E2E-5: Scene card selection | P1 | Profile form interaction | Specified |
| E2E-6: Edginess slider value change | P1 | Profile form interaction | Specified |
| E2E-7: Form validation (empty location, no scene) | P1 | Error handling | Specified |
| E2E-8: CTA submits profile POST | P1 | Critical path: profile save | Specified |
| E2E-9: Returning user redirect | P1 | Returning user redirect to /dashboard | Specified |
| E2E-10: Mobile layout | P2 | Responsive design verification | Specified |
| E2E-11: Accessibility (ARIA roles, keyboard) | P2 | Accessibility compliance | MISSING (MEDIUM) |
| E2E-12: Reduced motion compliance | P2 | prefers-reduced-motion | MISSING (MEDIUM) |

**Integration Test Points:**
| Component | Integration Point | Mock Required |
|-----------|-------------------|---------------|
| Profile endpoint -> user_profiles table | DB write via ProfileRepository | Real DB (integration) |
| Profile endpoint -> users.onboarding_completed_at | DB write via UserRepository | Real DB (integration) |
| Profile endpoint idempotency | DB upsert behavior | Real DB (integration) |
| OTP handler -> scheduled_events table | DB write via ScheduledEventRepository | Real DB (integration) |
| OTP handler -> magic link -> button URL | Supabase Admin API | Mocked Supabase client |
| Fallback event -> onboarding check -> delivery | scheduled_events + users table | Real DB (integration) |

**Unit Test Coverage:**
| Module | Functions | Coverage Target |
|--------|-----------|------------------|
| `otp_handler.py` | `_generate_portal_magic_link`, `_offer_onboarding_choice`, `_schedule_onboarding_fallback` | >= 90% (critical path) |
| `routes/onboarding.py` | `save_onboarding_profile` | >= 90% (critical path) |
| `onboarding/fallback.py` | Event handler: fire vs. discard logic | >= 85% |
| `onboarding/drip_manager.py` | `evaluate_user` (Phase 2) | >= 85% |
| `api/schemas/portal.py` | `OnboardingProfileRequest` validation | >= 85% |

### TDD Readiness Checklist
- [x] ACs are specific -- 32 ACs with clear pass/fail criteria
- [x] ACs are measurable -- quantifiable outcomes (button URL format, field values, redirect targets)
- [x] Test types clear per AC -- spec maps each AC to unit, integration, or E2E
- [x] Red-green-refactor path clear -- TDD task structure explicitly defined (lines 1689-1695) with 2-commit minimum per story

### Coverage Requirements
- [x] Overall target specified -- >= 85% line coverage for all new code (line 1606)
- [x] Critical path coverage -- >= 90% for profile endpoint and magic link generation (line 1606)
- [x] Branch coverage -- implicitly covered by edge case tests (invalid scene, empty location, fallback paths)
- [ ] Exclusions documented -- no explicit exclusions listed; recommend documenting that Phase 2 DripManager tests may be deferred

### Recommendations

1. **Add accessibility E2E test (MEDIUM)**: Create E2E-11 in `portal/e2e/onboarding.spec.ts` that verifies: `role="radiogroup"` on SceneSelector, `role="slider"` on EdginessSlider with correct `aria-valuemin`/`aria-valuemax`, keyboard Left/Right arrow changes slider value, Tab order reaches all interactive elements. The spec defines 10+ ARIA requirements (lines 1073-1088) that should have at least one E2E smoke test. Pattern: follow `portal/e2e/accessibility.spec.ts` if it has existing patterns.

2. **Add reduced-motion E2E test (MEDIUM)**: Create E2E-12 using Playwright's `page.emulateMedia({ reducedMotion: 'reduce' })`. Navigate to `/onboarding`, verify ScoreRing renders immediately with the value "75" visible (no animation delay). This covers the `prefers-reduced-motion: reduce` requirement at spec line 170 and 1085.

3. **Add Pydantic validation edge case unit tests (MEDIUM)**: Add to `test_onboarding_profile.py`: (a) whitespace-only location `"   "` should be rejected by `min_length=1` after strip, (b) location exceeding 100 chars returns 422, (c) non-enum scene value like `"invalid_scene"` returns 400. This hardens the validation boundary tested by TDD.

4. **Split monolithic OTP integration test (MEDIUM)**: The test at spec line 1660 ("Full OTP verification -> magic link flow") covers too much in one test. Split into two focused tests: success path (verify magic link URL in button) and failure path (verify fallback URL in button). Each test is independently debuggable if CI fails.

5. **Handle `tg://` protocol in E2E-8 (LOW)**: The CTA test will trigger `window.open("tg://resolve?domain=Nikita_my_bot")` which fails in headless Chromium. Pre-empt this by stubbing `window.open` via `page.addInitScript(() => { window.open = () => null })` before the test, then assert the POST request body only. This matches the pattern of testing the contract (API call) rather than the side effect (protocol handler).

6. **Clarify Phase 2 test scope boundary (LOW)**: Add a note in the spec's Testing Strategy section that the 14 DripManager unit tests (lines 1642-1645) are deferred to Phase 2 implementation and are NOT required for Phase 1 GATE passage. This prevents confusion during task planning.

7. **Document E2E mock additions needed (LOW)**: The E2E tests will need `mockApiRoutes` in `portal/e2e/fixtures/api-mocks.ts` to be extended with: (a) `**/api/v1/onboarding/profile` POST route mock returning `{ status: "ok", user_id: "e2e-player-id" }`, (b) a variant of `**/api/v1/portal/stats` that returns `onboarding_completed_at: null` for the onboarding page tests. Document this in the spec's mock strategy section so implementers know upfront.
