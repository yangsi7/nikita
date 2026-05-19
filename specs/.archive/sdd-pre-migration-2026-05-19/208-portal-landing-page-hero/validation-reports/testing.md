## Testing Validation Report

**Spec:** specs/208-portal-landing-page-hero/spec.md
**Status:** PASS
**Timestamp:** 2026-04-03T00:00:00Z

### Summary
- CRITICAL: 0
- HIGH: 0
- MEDIUM: 3
- LOW: 3

### Findings

| Severity | Category | Issue | Location | Recommendation |
|----------|----------|-------|----------|----------------|
| MEDIUM | TDD Enablement | The framer-motion mock provided in the spec is incomplete — it mocks `motion.div`, `motion.p`, `motion.h1` but does NOT mock `motion.span`, `motion.button`, or `motion.canvas`. Components like `GlowButton` likely use `motion.button`. Tests will crash if unmocked variants are used. | spec.md §framer-motion mock | Extend mock to include all `motion.*` variants used: `motion.button`, `motion.span`, `motion.canvas`, `motion.a`. Use a `Proxy`-based catch-all for safety. |
| MEDIUM | Test Coverage Gap | No unit test specified for `chapter-timeline.tsx` — the acceptance criteria include "Chapter timeline shows 5 dots with labels and thresholds" but no test file is listed for it. `chapter-timeline.test.tsx` is missing from the `__tests__/` file list. | spec.md §Unit Tests | Add `chapter-timeline.test.tsx` to the test file list. Test: renders 5 dots, correct chapter labels (Spark/Intrigue/Investment/Intimacy/Home), correct threshold values (55/60/65/70/75%). |
| MEDIUM | Test Coverage Gap | No unit test for `system-terminal.tsx` — the acceptance criteria include "System terminal lines appear sequentially" and "14 system names visible" but `system-terminal.test.tsx` is missing. Only `system-section.test.tsx` covers "14 system names visible" which may be at the section level. | spec.md §Unit Tests | Add `system-terminal.test.tsx` OR expand `system-section.test.tsx` to verify all 14 system names render (with animation mocked to immediate). |
| LOW | E2E Test Gap | Playwright spec does not include a test for the mobile viewport hero-image hiding (acceptance criteria: "hero image hidden" at < 768px). Only "mobile layout stacks properly" is specified. | spec.md §E2E Tests | Add: `test("mobile — hero image hidden at 375px", async ({ page }) => { await page.setViewportSize({width: 375, height: 812}); ... expect(heroImage).not.toBeVisible() })` |
| LOW | E2E Test Gap | No E2E test for the floating nav appearing on scroll. The spec states it as acceptance criteria but the Playwright test list only has a generic "Scroll → floating nav appears" — no implementation detail. Needs `page.evaluate(() => window.scrollTo(0, window.innerHeight))` then assertion. | spec.md §E2E Tests | Specify the exact scroll mechanism in E2E test: use `page.evaluate` to scroll past hero height, then assert nav becomes visible. |
| LOW | Reduced Motion Test | The unit test for `prefers-reduced-motion` is listed as a key test case but no mock setup is specified. jsdom doesn't support `matchMedia` natively — needs mock in test setup or per-test. | spec.md §Key test cases | Add to spec: `window.matchMedia = vi.fn().mockImplementation(query => ({ matches: query.includes('reduce'), ... }))` in test setup for reduced motion cases. |

### TDD Enablement Checklist
- [x] Test files enumerated before implementation
- [x] Auth-conditional CTA tests specified (unauthenticated/authenticated variants)
- [x] framer-motion mock provided
- [x] Key test cases listed (5 cases)
- [x] Test directory location specified (`__tests__/` co-located)
- [x] Vitest + jsdom environment (already configured in `vitest.config.ts`)
- [x] `@testing-library/react` already installed
- [ ] `chapter-timeline.test.tsx` missing — MEDIUM
- [ ] `system-terminal.test.tsx` missing — MEDIUM
- [ ] framer-motion mock incomplete — MEDIUM
- [ ] `matchMedia` mock for reduced-motion tests — LOW

### Acceptance Criteria Testability Matrix

| Criterion | Unit Test | E2E Test | Testable? |
|-----------|-----------|----------|-----------|
| Unauthenticated → landing page at `/` | hero-section.test | landing.spec #1 | ✓ |
| Authenticated → landing + "Go to Dashboard" | cta-section.test | landing.spec #2 | ✓ |
| FallingPattern renders without errors | hero-section.test (canvas mock) | — | ✓ (with mock) |
| Staggered animation on load | hero-section.test (framer mock) | — | ✓ |
| Floating nav on scroll | landing-nav.test | landing.spec #4 | ✓ (with scroll mock) |
| Telegram mockup animated | pitch-section.test | — | ✓ |
| Terminal lines sequential | system-section.test | — | ✓ (with timer mock) |
| Stats counter animates | system-section.test | — | PARTIAL (mock eliminates animation) |
| Glass cards render | stakes-section.test | — | ✓ |
| Chapter timeline 5 dots | NO TEST SPECIFIED | — | MISSING — MEDIUM |
| CTA links correct per auth | cta/hero tests | landing.spec #2 | ✓ |
| Mobile stacking | — | landing.spec #5 | ✓ |
| Reduced motion disables animations | (per component) | accessibility.spec | PARTIAL — needs matchMedia mock |
| npm run build passes | — | CI | ✓ |
| Playwright E2E pass | — | landing.spec | ✓ |
| Vitest unit tests pass | all test files | — | ✓ |
| Existing routes still work | — | landing.spec #3,6 | ✓ |
| OG metadata correct | — | landing.spec (head check) | ✓ (Playwright can check meta) |

### Recommendations

1. **MEDIUM — Complete framer-motion mock**: Replace the partial mock with a Proxy-based catch-all that covers all `motion.*` variants. Prevents test crashes from using unmocked elements like `motion.button`.

2. **MEDIUM — Add `chapter-timeline.test.tsx`**: At minimum: renders 5 chapter dots, all labels visible (Spark/Intrigue/Investment/Intimacy/Home), threshold values correct.

3. **MEDIUM — Add `system-terminal.test.tsx` or expand system-section test**: Verify all 14 system names appear in DOM when animation is mocked to immediate-complete state.

4. **LOW — `matchMedia` mock**: Add to spec §Testing that `vitest.setup.ts` (or per-test) should mock `window.matchMedia` for reduced-motion tests.

5. **LOW — E2E scroll precision**: Specify `page.evaluate(() => window.scrollTo(0, window.innerHeight + 1))` for floating nav test. Avoids test flake from exact-height edge cases.
