## Testing Validation Report

**Spec:** specs/081-onboarding-redesign-progressive-discovery/spec.md
**Status:** FAIL
**Timestamp:** 2026-03-22T12:00:00Z

### Summary
- CRITICAL: 2
- HIGH: 5
- MEDIUM: 4
- LOW: 2

### Findings

| Severity | Category | Issue | Location | Recommendation |
|----------|----------|-------|----------|----------------|
| CRITICAL | Test Strategy | **No testing section exists in the spec.** The 1,216-line spec defines 6 FRs, 8 user stories, 28 ACs, detailed technical architecture, and UI wireframes but contains zero mentions of test strategy, test types, coverage targets, or TDD approach. | spec.md (entire file) | Add a `## Testing Strategy` section defining test types (unit, integration, E2E), coverage targets, testing tools (pytest, Playwright), mock strategy, and TDD task structure. See Recommendations #1. |
| CRITICAL | Testing Pyramid | **No testing pyramid defined.** Without any testing section, there is no allocation of unit vs. integration vs. E2E tests. The spec cannot be implemented via TDD because implementers have no guidance on what to test at which level. | spec.md (entire file) | Define a testing pyramid with approximate distribution: ~70% unit (DripManager logic, rate limiting, template selection, welcome message scheduling), ~20% integration (check-drips endpoint, portal stats API, magic link generation, scheduled_events interaction), ~10% E2E (Playwright welcome page flow, portal first-visit redirect). See Recommendations #2. |
| HIGH | E2E Tests | **No E2E test scenarios defined for the portal welcome page (FR-004).** The welcome page is a new interactive page with animations, step navigation, skip functionality, and a CTA that writes to the database. The project has 10 existing Playwright spec files covering dashboard, auth, admin, etc., but no E2E scenarios are specified for `/dashboard/welcome`. | spec.md FR-004 (lines 113-129) | Define Playwright E2E scenarios: (1) first-visit redirect from `/dashboard` to `/dashboard/welcome`, (2) welcome page renders score ring + chapter roadmap + rule cards, (3) "Go to Dashboard" CTA sets `welcome_completed=true` and redirects, (4) "Skip" link sets flag and redirects, (5) subsequent visit bypasses welcome. See Recommendations #3. |
| HIGH | E2E Tests | **No E2E test scenarios for magic link auth flow (FR-003).** AC-4.1 through AC-4.4 describe magic link authentication behavior but no test approach is defined. Magic link flows involve Supabase external service calls that need explicit mock/stub strategy. | spec.md US-4 (lines 177-183) | Define E2E scenarios for magic link: (1) valid magic link token redirects to portal authenticated, (2) expired token redirects to `/login` with message, (3) no-email user gets regular portal link. Specify that Supabase auth admin API must be mocked in tests. |
| HIGH | Unit Tests | **No unit test requirements for DripManager (FR-002).** DripManager is the core new class (7 drip definitions, trigger evaluation, rate limiting, template selection, magic link generation) but no unit tests are specified. This class has high cyclomatic complexity with 7 distinct trigger conditions. | spec.md lines 712-778 | Define unit tests for: `evaluate_user()` (7 trigger conditions x pass/fail = 14 test cases minimum), `_is_rate_limited()` (within window, outside window, empty drips_delivered, edge at exactly 2h), `_select_template()` (5 darkness levels x 7 drips), `deliver_drip()` (success, Telegram failure, magic link fallback). |
| HIGH | Integration Tests | **No integration test requirements for check-drips endpoint.** The `POST /api/v1/tasks/check-drips` endpoint orchestrates DripManager, database sessions, job execution tracking, and error handling but has no test specification. | spec.md lines 886-925 | Define integration tests: (1) endpoint returns correct statistics, (2) endpoint requires task auth secret, (3) endpoint handles DripManager errors gracefully, (4) job execution is tracked in job_executions table, (5) idempotency -- re-running does not duplicate deliveries. |
| HIGH | Coverage Targets | **No coverage targets specified.** The project has 5,318+ backend tests and existing onboarding tests reference ">85% coverage" (test_infrastructure.py line 13). This spec defines no target for the new code. | spec.md (absent) | Set explicit coverage targets: DripManager >= 90% (critical path), handoff welcome messages >= 85%, check-drips endpoint >= 85%, portal welcome page components >= 80%. Overall new code >= 85%. |
| MEDIUM | Mock Strategy | **No mock/stub strategy for external services.** The spec introduces 2 new external service dependencies: (1) Supabase Auth Admin API for magic link generation, (2) Telegram Bot API for inline keyboard message delivery. Neither has a defined mocking approach for tests. | spec.md FR-003 (lines 99-111), FR-002 (lines 85-97) | Define mock strategy: (a) Supabase admin client -- mock `supabase.auth.admin.generate_link()` to return a fake action_link, (b) Telegram Bot API -- mock `bot.send_message()` with inline keyboard, matching existing patterns in `tests/onboarding/test_handoff.py`. |
| MEDIUM | Test Data | **No test data/fixture strategy for drip trigger conditions.** The 7 drip triggers require specific user states (first conversation processed, score < 50, chapter > 1, boss threshold proximity, etc.) but no factory/fixture approach is defined for constructing these states. | spec.md Drip Definitions (lines 999-1009) | Define test fixture factories for: user with first conversation processed, user with decay event in score_history, user at chapter 2+, user within 5 points of boss threshold, user with resolved boss encounter, user at 24h post-onboarding. Reference existing factory patterns in `portal/e2e/fixtures/factories.ts` and `tests/onboarding/test_handoff.py`. |
| MEDIUM | CI/CD Integration | **No CI/CD test execution plan.** The project runs backend-ci.yml (pytest) and portal-ci.yml (Playwright) but no mention of how the new tests integrate. The check-drips endpoint tests need to be excluded from E2E/integration markers or included appropriately. | spec.md (absent) | Specify: backend unit/integration tests run in `backend-ci.yml`, portal Playwright tests for `/dashboard/welcome` run in `portal-ci.yml`, new integration tests use `pytest.mark.integration` with Supabase skip guard (matching project convention in `tests/db/integration/`). |
| MEDIUM | NFR Testing | **Non-functional requirements have no test approach.** NFR-001 (drip latency <5 min), NFR-002 (welcome message <60s), NFR-004 (rate limiting 2h window), and NFR-005 (failure isolation) are all testable but have no associated test specifications. | spec.md lines 1142-1167 | Add tests for: (a) NFR-004 rate limiting via unit test on `_is_rate_limited()`, (b) NFR-005 failure isolation via integration test verifying handoff succeeds when welcome message scheduling fails, (c) NFR-001/002 timing via unit test verifying scheduled_at timestamps fall within spec ranges. |
| LOW | Test Organization | **No test file structure defined.** The existing onboarding tests are in `tests/onboarding/` (12 files, 4,584 lines) and Telegram handler tests in `tests/platforms/telegram/`. New tests need clear placement. | N/A | Recommend: `tests/onboarding/test_drip_manager.py` (unit), `tests/onboarding/test_welcome_messages.py` (unit), `tests/api/test_check_drips.py` (integration), `portal/e2e/welcome.spec.ts` (E2E), `portal/src/app/dashboard/welcome/__tests__/` (vitest component tests). |
| LOW | Accessibility Testing | **No accessibility test requirements for welcome page.** The spec defines accessibility requirements (WCAG AA, aria labels, keyboard nav, reduced motion) in lines 693-702 but no tests verify compliance. | spec.md lines 693-702 | Add Playwright accessibility assertions: `toHaveAttribute('role', 'img')` on score ring, `toHaveAttribute('aria-current', 'step')` on chapter stepper, keyboard tab-through test, `prefers-reduced-motion` media query test. Existing `portal/e2e/accessibility.spec.ts` provides a pattern. |

### Testing Pyramid Analysis

```
Target Pyramid:          Spec Defines:

    /\                       /\
   /E2E\  ~10%              /  \   0%  E2E
  /------\                 /    \
 / Integ. \ ~20%          /      \  0%  Integration
/----------\             /        \
/   Unit    \ ~70%      /          \ 0%  Unit
/____________\         /____________\

VERDICT: Complete absence of testing pyramid. 0% defined at all levels.
```

### AC Testability Analysis

| AC ID | AC Description | Testable | Test Type | Issue |
|-------|----------------|----------|-----------|-------|
| AC-1.1 | Welcome msg 1 within 60s of first message | Yes | Unit + Integration | Timing is testable via scheduled_at verification. Need mock for scheduled_events repo. |
| AC-1.2 | Welcome msg 2 within 5min of msg 1 | Yes | Unit + Integration | Same as AC-1.1 -- verify scheduled_at delta is 180-300s. |
| AC-1.3 | Messages match darkness level (1-5) | Yes | Unit | Test `_get_welcome_template(msg_num, darkness_level)` for all 10 combinations (2 msgs x 5 levels). |
| AC-1.4 | Delivery failure does not block handoff | Yes | Integration | Mock scheduled_event_repo to raise, verify handoff still succeeds. Critical failure isolation test. |
| AC-2.1 | Drip 1 delivered after first conversation processed | Yes | Unit + Integration | Unit: test `evaluate_user()` with first conversation trigger. Integration: test check-drips endpoint. |
| AC-2.2 | Drip 1 includes inline keyboard with magic link | Yes | Unit | Test `deliver_drip()` output includes InlineKeyboardButton with magic link URL. |
| AC-2.3 | Magic link auth + redirect to welcome or dashboard | Partial | E2E | Full auth flow requires Supabase interaction. Testable with mocked auth callback. Redirect logic testable in Playwright. |
| AC-3.1 | Drip 3 on first decay (score < 50) | Yes | Unit | Test `evaluate_user()` with score < 50 and decay event in score_history. |
| AC-3.2 | Decay message in Nikita voice, no game terms | Partial | Unit | Template content is static -- verify template does not contain "decay", "score", "metric". Subjective voice quality is not automatable. |
| AC-3.3 | Drip includes portal deep link to /dashboard | Yes | Unit | Test URL construction in `deliver_drip()`. |
| AC-4.1 | Portal links contain valid magic link token | Yes | Integration | Mock Supabase admin API, verify returned URL contains token parameter. |
| AC-4.2 | Link authenticates without email/password/OTP | Partial | E2E | Full auth validation requires Supabase. Testable by mocking auth callback route in Playwright. |
| AC-4.3 | Expired magic link redirects to /login with message | Yes | E2E | Playwright test: navigate to expired token URL, assert redirect to /login with error message. |
| AC-4.4 | No-email user gets regular portal link | Yes | Unit | Test `_generate_magic_link()` returns None when email is None, and `deliver_drip()` uses plain portal URL. |
| AC-5.1 | First visit redirects /dashboard to /dashboard/welcome | Yes | E2E | Playwright: mock stats API with `welcome_completed: false`, navigate to /dashboard, assert redirect. |
| AC-5.2 | Welcome page displays score ring, chapters, rules | Yes | E2E | Playwright: verify presence of score ring, 5 chapter nodes, 4 rule cards using data-testid selectors. |
| AC-5.3 | CTA sets welcome_completed=true and redirects | Yes | E2E | Playwright: click CTA, intercept PUT /portal/settings, verify payload, assert redirect to /dashboard. |
| AC-5.4 | Subsequent visits go to /dashboard directly | Yes | E2E | Playwright: mock stats with `welcome_completed: true`, navigate to /dashboard, assert no redirect. |
| AC-5.5 | Skip link sets welcome_completed=true | Yes | E2E | Playwright: click Skip, intercept PUT request, verify flag set. |
| AC-6.1 | Boss warning drip at threshold - 5 | Yes | Unit | Test `evaluate_user()` with score at boss_threshold - 4 (within range) and boss_threshold - 6 (outside). |
| AC-6.2 | Warning message avoids "boss encounter" term | Yes | Unit | Verify template string does not contain "boss encounter" for all 5 darkness levels. |
| AC-6.3 | Boss warning once per chapter | Yes | Unit | Test with drips_delivered containing boss_warning for current chapter -- should not re-trigger. |
| AC-7.1 | Boss debrief after encounter resolves | Yes | Unit | Test `evaluate_user()` with boss_attempts > 0 and game_status changed from boss_fight. |
| AC-7.2 | Message tone varies by outcome | Yes | Unit | Test template selection for passed vs. failed boss outcomes across darkness levels. |
| AC-7.3 | Includes portal link with score and boss count | Yes | Unit | Test URL construction includes dashboard path. |
| AC-8.1 | Drip 7 at 24h +/- 5min after onboarded_at | Yes | Unit | Test `evaluate_user()` at 23h55m (not yet), 24h (eligible), 24h5m (eligible), with time mocking. |
| AC-8.2 | Message introduces chapters/vices without spoilers | Partial | Unit | Template content check -- no specific mechanic values. Subjective "spoiler" judgment not fully automatable. |
| AC-8.3 | Deep link varies by welcome_completed status | Yes | Unit | Test portal path is `/dashboard/welcome` when `welcome_completed=false`, `/dashboard` when `true`. |

**Testability summary:** 25/28 ACs fully testable, 3/28 partially testable (AC-2.3, AC-3.2, AC-8.2 involve subjective voice quality or external auth flows that require mock boundaries).

### Test Scenario Inventory

**E2E Scenarios (Playwright -- portal):**

| Scenario | Priority | User Flow | Status |
|----------|----------|-----------|--------|
| First-visit redirect to /dashboard/welcome | P1 | AC-5.1 | NOT DEFINED in spec |
| Welcome page renders all sections | P1 | AC-5.2 | NOT DEFINED in spec |
| CTA completes welcome and redirects | P1 | AC-5.3 | NOT DEFINED in spec |
| Skip link completes welcome | P2 | AC-5.5 | NOT DEFINED in spec |
| Returning user bypasses welcome | P1 | AC-5.4 | NOT DEFINED in spec |
| Expired magic link shows login page | P2 | AC-4.3 | NOT DEFINED in spec |
| Welcome page accessibility (aria, keyboard) | P2 | Accessibility reqs | NOT DEFINED in spec |
| Welcome page responsive layout (mobile) | P3 | WF-2 | NOT DEFINED in spec |

**Integration Test Points:**

| Component | Integration Point | Mock Required |
|-----------|-------------------|---------------|
| `POST /api/v1/tasks/check-drips` | DripManager + DB session + job execution | Supabase auth admin, Telegram Bot API |
| `HandoffManager._schedule_welcome_messages()` | ScheduledEventRepository | scheduled_events table (mock repo) |
| `DripManager._generate_magic_link()` | Supabase Auth Admin API | `supabase.auth.admin.generate_link()` |
| `DripManager.deliver_drip()` | Telegram Bot API | `bot.send_message()` with inline keyboard |
| `GET /api/v1/portal/stats` (modified) | User repository | Verify `welcome_completed` in response |
| `PUT /api/v1/portal/settings` (modified) | User repository | Verify `welcome_completed` write |

**Unit Test Coverage:**

| Module | Functions | Coverage Target |
|--------|-----------|-----------------|
| `drip_manager.py` | `process_all`, `evaluate_user`, `deliver_drip`, `_generate_magic_link`, `_is_rate_limited`, `_select_template` | >= 90% |
| `drip_templates.py` | Template constants (7 drips x 5 darkness levels = 35 templates) | 100% (existence validation) |
| `handoff.py` (additions) | `_schedule_welcome_messages`, `_get_welcome_template` | >= 85% |
| `welcome-client.tsx` | Step navigation, CTA handler, skip handler, animation triggers | >= 80% |
| `page.tsx` (welcome) | Server-side redirect logic, stats fetch | >= 80% |
| `page.tsx` (dashboard mod) | First-visit detection redirect | >= 85% |

### TDD Readiness Checklist
- [ ] ACs are specific -- YES, 25/28 are fully specific and measurable
- [ ] ACs are measurable -- PARTIAL, 3/28 involve subjective voice quality
- [ ] Test types clear per AC -- NO, spec does not map ACs to test types
- [ ] Red-green-refactor path clear -- NO, no TDD task structure defined

### Coverage Requirements
- [ ] Overall target specified -- NOT SPECIFIED
- [ ] Critical path coverage -- NOT SPECIFIED
- [ ] Branch coverage -- NOT SPECIFIED
- [ ] Exclusions documented -- NOT SPECIFIED

### Recommendations

1. **[CRITICAL] Add a `## Testing Strategy` section to the spec.** This is the most urgent fix. The section should include:
   - **Test types:** pytest (unit + integration), Playwright (E2E), vitest (portal component tests)
   - **Testing pyramid:** ~70% unit (DripManager logic, template selection, rate limiting), ~20% integration (API endpoints, DB interactions, external service mocks), ~10% E2E (Playwright welcome page flow)
   - **Coverage targets:** Overall >= 85%, DripManager >= 90%, welcome page components >= 80%
   - **TDD task mapping:** Each user story should reference the test file(s) to be created before implementation

2. **[CRITICAL] Define the testing pyramid explicitly.** Suggested distribution for this feature:
   - **Unit (~35 tests):** DripManager.evaluate_user (7 triggers x 2 states = 14), rate limiting (4 edge cases), template selection (7 drips x 5 levels spot-check = ~7), welcome message scheduling (4), magic link generation (4 cases), deliver_drip (4 cases)
   - **Integration (~10 tests):** check-drips endpoint (5 tests), welcome_completed in portal stats (2), portal settings write (2), handoff failure isolation (1)
   - **E2E (~8 tests):** Welcome page Playwright scenarios (5), auth flow (2), accessibility (1)
   - **Ratio:** 35/53 = 66% unit, 10/53 = 19% integration, 8/53 = 15% E2E -- acceptable for a feature with significant UI

3. **[HIGH] Define Playwright E2E scenarios for `/dashboard/welcome`.** Add to the spec:
   ```
   E2E-1: First visit redirect (mock stats welcome_completed=false, navigate /dashboard, assert URL is /dashboard/welcome)
   E2E-2: Welcome renders sections (assert score ring, 5 chapter nodes, 4 rule cards visible)
   E2E-3: CTA completion (click "Go to Dashboard", intercept PUT, assert welcome_completed=true, assert redirect)
   E2E-4: Skip link (click Skip, assert PUT called, assert redirect to /dashboard)
   E2E-5: Returning user bypass (mock welcome_completed=true, navigate /dashboard, assert stays on /dashboard)
   ```
   Follow the existing pattern in `portal/e2e/dashboard.spec.ts` using `mockApiRoutes` and `expectCardContent`.

4. **[HIGH] Define unit test requirements for DripManager.** This is the highest-complexity new class. Minimum test cases:
   - `evaluate_user()`: One test per drip trigger (7 triggers), plus negative cases (condition not met), plus already-delivered case
   - `_is_rate_limited()`: Within 2h window, outside window, empty dict, exactly at boundary
   - `_select_template()`: Verify correct template returned for each darkness level
   - `deliver_drip()`: Success path, Telegram send failure, magic link fallback to plain URL

5. **[HIGH] Define integration test requirements for check-drips endpoint.** Minimum:
   - Auth: endpoint rejects requests without TASK_AUTH_SECRET
   - Happy path: returns correct evaluated/delivered/rate_limited counts
   - Error handling: DripManager exception is caught, logged, and returned as error response
   - Idempotency: running twice does not deliver duplicate drips
   - Job execution: start_execution and complete_execution called correctly

6. **[HIGH] Define mock strategy for external services.** Add to spec:
   - **Supabase Auth Admin:** Mock `supabase.auth.admin.generate_link()` returning `MagicMock(properties=MagicMock(action_link="https://test.supabase.co/auth/v1/verify?token=test123"))` for success, raising `Exception` for failure
   - **Telegram Bot API:** Mock `bot.send_message()` with `reply_markup=InlineKeyboardMarkup(...)` -- pattern already established in `tests/onboarding/test_handoff.py`

7. **[HIGH] Set explicit coverage targets.** Add to spec:
   - `nikita/onboarding/drip_manager.py`: >= 90% line coverage
   - `nikita/onboarding/drip_templates.py`: 100% (template existence)
   - `nikita/onboarding/handoff.py` (new code only): >= 85%
   - `portal/src/app/dashboard/welcome/`: >= 80% (vitest component tests)
   - Overall new code: >= 85%

8. **[MEDIUM] Define mock strategy for Supabase and Telegram in tests.** Include patterns from existing codebase:
   - Backend: `unittest.mock.AsyncMock` and `patch` (see `tests/onboarding/test_handoff.py`)
   - Portal E2E: `page.route()` interception (see `portal/e2e/fixtures/api-mocks.ts`)

9. **[MEDIUM] Define test fixtures for drip trigger states.** Create factory functions producing User objects in each of the 7 trigger states. Follow the existing factory pattern in `portal/e2e/fixtures/factories.ts`.

10. **[MEDIUM] Add NFR test specifications.** At minimum:
    - NFR-004 (rate limiting): Unit test `_is_rate_limited()` with timestamps at boundary
    - NFR-005 (failure isolation): Integration test verifying handoff completes when `_schedule_welcome_messages()` raises
    - NFR-001/002 (timing): Unit test verifying `scheduled_at` timestamps are within spec ranges (30-60s, 180-300s)

11. **[MEDIUM] Specify CI/CD integration for new tests.** New backend tests run in `backend-ci.yml`. New Playwright tests for `/dashboard/welcome` run in `portal-ci.yml`. Integration tests requiring Supabase use `pytest.mark.integration` with `skipif(not _SUPABASE_REACHABLE)` guard.

12. **[LOW] Define test file locations.** Suggested structure:
    - `tests/onboarding/test_drip_manager.py` -- DripManager unit tests
    - `tests/onboarding/test_welcome_messages.py` -- Welcome message scheduling tests
    - `tests/api/routes/test_check_drips.py` -- check-drips endpoint integration tests
    - `portal/e2e/welcome.spec.ts` -- Playwright E2E for welcome page
    - `portal/src/app/dashboard/welcome/__tests__/welcome-client.test.tsx` -- vitest component test

13. **[LOW] Add accessibility test cases.** Leverage existing `portal/e2e/accessibility.spec.ts` pattern to verify: `role="img"` on score ring, `aria-current="step"` on chapter stepper, keyboard tab navigation through all interactive elements, `prefers-reduced-motion` disables animations.
