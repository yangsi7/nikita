import { test, expect } from "@playwright/test"
import { mockApiRoutes } from "./fixtures"

/**
 * Spec 214 — Portal Onboarding Wizard (PR 214-C, T300)
 *
 * Happy-path walkthrough on Chrome desktop viewport covering US-1 (desktop
 * happy path) and US-6 (backstory continuity). The wizard is authored in
 * PR 214-B (`onboarding-wizard.tsx`); these specs assume `data-testid` hooks
 * from the spec §AC-1.5 (`wizard-step-{N}` per step root) and the step-level
 * CTA pattern described in spec §FR-1 step enumeration table.
 *
 * Contract refs:
 *   - PUT /api/v1/onboarding/profile/chosen-option — spec FR-10.1
 *   - GET /api/v1/onboarding/pipeline-ready/{user_id} — spec FR-5
 *   - POST /api/v1/onboarding/preview-backstory — spec FR-8
 *   - POST /api/v1/onboarding/profile — spec FR-9 (pipeline gate entry)
 *
 * Until PR 214-B merges, `OnboardingWizard` is not yet on this branch. These
 * specs FAIL at the RED step intentionally (wizard-step-N selectors do not
 * resolve). They remain valid after PR-B merges — no rewrite required.
 */

// SKIPPED: legacy form wizard specs superseded by PR #363 chat-first wizard.
// Tracked in GH #364 for rewrite against chat UI or deletion with PR 5 cleanup.
test.describe.skip("Onboarding wizard — US-1 desktop happy path (Spec 214)", () => {
  test("renders all 11 steps in order and commits chosen backstory", async ({ page }) => {
    // ── Request capture for endpoint assertions ──────────────────
    let chosenOptionBody: { chosen_option_id?: string; cache_key?: string } | null = null
    let pipelineReadyCallCount = 0
    const CACHE_KEY = "test-cache-key-abc123"
    const CHOSEN_OPTION_ID = "scenario_techno_warehouse"

    await mockApiRoutes(page)

    // Override: POST /onboarding/preview-backstory returns 3 scenarios + cache_key.
    // Schema must match BackstoryPreviewResponse / BackstoryOption (see
    // `portal/src/app/onboarding/types/contracts.ts`) — keys are `scenarios`
    // (NOT `options`), with `context`, `the_moment`, `unresolved_hook`, `tone`.
    await page.route("**/api/v1/onboarding/preview-backstory", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          cache_key: CACHE_KEY,
          scenarios: [
            {
              id: CHOSEN_OPTION_ID,
              venue: "Zurich techno collective",
              context: "The warehouse door, 3am.",
              the_moment: "She saw you from the booth — didn't look away.",
              unresolved_hook: "You traded numbers in a stairwell.",
              tone: "romantic",
            },
            {
              id: "scenario_afterparty_loft",
              venue: "Loft above Limmat",
              context: "The afterparty.",
              the_moment: "Someone passed you a drink. She noticed.",
              unresolved_hook: "You left without saying goodbye.",
              tone: "intellectual",
            },
            {
              id: "scenario_sunrise_river",
              venue: "Limmat embankment",
              context: "Sunrise by the river.",
              the_moment: "You were walking alone. She wasn't.",
              unresolved_hook: "She said your name before you did.",
              tone: "chaotic",
            },
          ],
        }),
      })
    })

    // Override: POST /onboarding/profile returns pipeline metadata
    await page.route("**/api/v1/onboarding/profile", async (route) => {
      if (route.request().method() === "POST") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            user_id: "e2e-player-id",
            status: "ok",
            poll_interval_seconds: 1,
            poll_max_wait_seconds: 10,
          }),
        })
      } else if (route.request().method() === "PATCH") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ status: "ok" }),
        })
      } else {
        await route.fallback()
      }
    })

    // Override: PUT /onboarding/profile/chosen-option captures body
    await page.route("**/api/v1/onboarding/profile/chosen-option", async (route) => {
      const raw = route.request().postData()
      chosenOptionBody = raw ? (JSON.parse(raw) as typeof chosenOptionBody) : null
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          chosen_option: {
            id: CHOSEN_OPTION_ID,
            title: "The warehouse door, 3am.",
            venue: "Zurich techno collective",
            opening_hook: "She saw you from the booth — didn't look away.",
          },
        }),
      })
    })

    // Override: GET /onboarding/pipeline-ready/* polls twice (pending → ready)
    await page.route("**/api/v1/onboarding/pipeline-ready/**", async (route) => {
      pipelineReadyCallCount += 1
      const state = pipelineReadyCallCount >= 2 ? "ready" : "pending"
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          state,
          venue_research_status: state === "ready" ? "ready" : "pending",
          backstory_available: true,
          wizard_step: 10,
          poll_interval_seconds: 1,
          poll_max_wait_seconds: 10,
        }),
      })
    })

    await page.goto("/onboarding", { waitUntil: "domcontentloaded" })

    // ── Step 3: Dossier Header ───────────────────────────────────
    // CTA strings match `portal/src/app/onboarding/steps/copy.ts` (FR-3 canon).
    const step3 = page.locator('[data-testid="wizard-step-3"]')
    await expect(step3).toBeVisible({ timeout: 10_000 })
    await step3.getByRole("button", { name: /open the file/i }).click()

    // ── Step 4: Location ─────────────────────────────────────────
    const step4 = page.locator('[data-testid="wizard-step-4"]')
    await expect(step4).toBeVisible({ timeout: 5_000 })
    await step4.locator('[data-testid="location-city-input"]').fill("Zurich")
    await step4.getByRole("button", { name: /that'?s accurate/i }).click()

    // ── Step 5: Scene ────────────────────────────────────────────
    const step5 = page.locator('[data-testid="wizard-step-5"]')
    await expect(step5).toBeVisible({ timeout: 5_000 })
    await step5.getByRole("radio", { name: /techno/i }).click()
    await step5.getByRole("button", { name: /confirmed/i }).click()

    // ── Step 6: Darkness ─────────────────────────────────────────
    const step6 = page.locator('[data-testid="wizard-step-6"]')
    await expect(step6).toBeVisible({ timeout: 5_000 })
    // Slider default OK; advance
    await step6.getByRole("button", { name: /confirmed/i }).click()

    // ── Step 7: Identity ─────────────────────────────────────────
    // Use label-based locators — inputs are wired via `htmlFor`/`id` pairs,
    // not `name` attributes.
    const step7 = page.locator('[data-testid="wizard-step-7"]')
    await expect(step7).toBeVisible({ timeout: 5_000 })
    await step7.getByLabel(/name \(optional\)/i).fill("Simon")
    await step7.getByLabel(/age \(optional\)/i).fill("33")
    await step7.getByLabel(/what keeps you busy/i).fill("engineer")
    await step7.getByRole("button", { name: /file updated/i }).click()

    // ── Step 8: Backstory Reveal ─────────────────────────────────
    const step8 = page.locator('[data-testid="wizard-step-8"]')
    await expect(step8).toBeVisible({ timeout: 10_000 })
    // Select the first backstory card — testid is index-based, not id-based.
    // The first card (index 0) corresponds to CHOSEN_OPTION_ID per mock order.
    await step8.locator('[data-testid="backstory-card-0"]').click()
    await step8.getByRole("button", { name: /that'?s how it happened/i }).click()

    // AC: PUT /profile/chosen-option was called with chosen_option_id + cache_key
    await expect.poll(() => chosenOptionBody, { timeout: 5_000 }).not.toBeNull()
    expect(chosenOptionBody).toEqual(
      expect.objectContaining({
        chosen_option_id: CHOSEN_OPTION_ID,
        cache_key: CACHE_KEY,
      })
    )

    // ── Step 9: Phone Ask (choose Telegram path to keep test deterministic) ──
    const step9 = page.locator('[data-testid="wizard-step-9"]')
    await expect(step9).toBeVisible({ timeout: 5_000 })
    // Select the Telegram path radio-card (tightened to exact name to avoid
    // matching the "Find her in Telegram." submit CTA below).
    await step9.getByRole("button", { name: "Start in Telegram" }).click()
    // Advance via the text-path CTA ("Find her in Telegram.").
    await step9.getByRole("button", { name: /find her in telegram/i }).click()

    // ── Step 10: Pipeline Ready Gate (polls /pipeline-ready) ─────
    const step10 = page.locator('[data-testid="wizard-step-10"]')
    await expect(step10).toBeVisible({ timeout: 5_000 })
    // Wait for pipeline transition to "ready" (CLEARED stamp renders)
    await expect(step10).toContainText(/cleared/i, { timeout: 15_000 })
    expect(pipelineReadyCallCount).toBeGreaterThanOrEqual(1)

    // ── Step 11: Handoff ─────────────────────────────────────────
    const step11 = page.locator('[data-testid="wizard-step-11"]')
    await expect(step11).toBeVisible({ timeout: 10_000 })
    // AC US-1: handoff CTA reaches Telegram
    await expect(step11).toContainText(/telegram/i)
  })

  // US-6 (SC-3) @telegram-dogfood automation — tracked as GH #302. The test
  // body is intentionally absent here (empty shells are a PR-blocker per
  // `.claude/rules/testing.md`). Orchestrator-driven dogfood continues via
  // Telegram MCP after production deploy until the follow-up lands.

  // Regression guard (2026-04-16 live Gemini-judge walk): a previous
  // className override used `text-primary` on a `bg-primary` Button, making
  // CTA labels invisible (both resolve to the same rose-glow oklch token).
  // Assert the opening-screen primary CTA has visually distinct
  // foreground vs background colors — catches the reintroduction of that bug.
  test("opening-screen primary CTA has contrasting foreground vs background", async ({ page }) => {
    await mockApiRoutes(page)
    await page.goto("/onboarding")

    // Target the primary CTA by its class marker — every wizard Button
    // uses `font-black tracking-[0.2em] uppercase`.
    const cta = page.locator("button.font-black.tracking-\\[0\\.2em\\].uppercase").first()
    await expect(cta).toBeVisible({ timeout: 10_000 })

    const colors = await cta.evaluate((el) => {
      const s = window.getComputedStyle(el)
      return { color: s.color, bg: s.backgroundColor }
    })
    expect(colors.color).not.toBe(colors.bg)
    // CTA label text must not be empty (prevents invisible-text regression)
    const text = (await cta.textContent())?.trim() ?? ""
    expect(text.length).toBeGreaterThan(0)
  })
})
