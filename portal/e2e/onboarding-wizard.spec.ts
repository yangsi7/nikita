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

test.describe("Onboarding wizard — US-1 desktop happy path (Spec 214)", () => {
  test("renders all 11 steps in order and commits chosen backstory", async ({ page }) => {
    // ── Request capture for endpoint assertions ──────────────────
    let chosenOptionBody: { chosen_option_id?: string; cache_key?: string } | null = null
    let pipelineReadyCallCount = 0
    const CACHE_KEY = "test-cache-key-abc123"
    const CHOSEN_OPTION_ID = "scenario_techno_warehouse"

    await mockApiRoutes(page)

    // Override: POST /onboarding/preview-backstory returns 3 cards + cache_key
    await page.route("**/api/v1/onboarding/preview-backstory", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          cache_key: CACHE_KEY,
          options: [
            {
              id: CHOSEN_OPTION_ID,
              title: "The warehouse door, 3am.",
              venue: "Zurich techno collective",
              opening_hook: "She saw you from the booth — didn't look away.",
              summary: "You traded numbers in a stairwell lit by a single red bulb.",
              tags: ["techno", "intense"],
            },
            {
              id: "scenario_afterparty_loft",
              title: "The afterparty.",
              venue: "Loft above Limmat",
              opening_hook: "Someone passed you a drink. She noticed.",
              summary: "",
              tags: ["afterparty"],
            },
            {
              id: "scenario_sunrise_river",
              title: "Sunrise by the river.",
              venue: "Limmat embankment",
              opening_hook: "You were walking alone. She wasn't.",
              summary: "",
              tags: ["sunrise"],
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
    const step3 = page.locator('[data-testid="wizard-step-3"]')
    await expect(step3).toBeVisible({ timeout: 10_000 })
    await step3.getByRole("button", { name: /continue/i }).click()

    // ── Step 4: Location ─────────────────────────────────────────
    const step4 = page.locator('[data-testid="wizard-step-4"]')
    await expect(step4).toBeVisible({ timeout: 5_000 })
    await step4.locator('input[name="location_city"]').fill("Zurich")
    await step4.getByRole("button", { name: /accurate/i }).click()

    // ── Step 5: Scene ────────────────────────────────────────────
    const step5 = page.locator('[data-testid="wizard-step-5"]')
    await expect(step5).toBeVisible({ timeout: 5_000 })
    await step5.getByRole("radio", { name: /techno/i }).click()

    // ── Step 6: Darkness ─────────────────────────────────────────
    const step6 = page.locator('[data-testid="wizard-step-6"]')
    await expect(step6).toBeVisible({ timeout: 5_000 })
    // Slider default OK; advance
    await step6.getByRole("button", { name: /confirm/i }).click()

    // ── Step 7: Identity ─────────────────────────────────────────
    const step7 = page.locator('[data-testid="wizard-step-7"]')
    await expect(step7).toBeVisible({ timeout: 5_000 })
    await step7.locator('input[name="name"]').fill("Simon")
    await step7.locator('input[name="age"]').fill("33")
    await step7.locator('input[name="occupation"]').fill("engineer")
    await step7.getByRole("button", { name: /updated/i }).click()

    // ── Step 8: Backstory Reveal ─────────────────────────────────
    const step8 = page.locator('[data-testid="wizard-step-8"]')
    await expect(step8).toBeVisible({ timeout: 10_000 })
    // Select the first backstory card (CHOSEN_OPTION_ID)
    await step8.locator(`[data-testid="backstory-card-${CHOSEN_OPTION_ID}"]`).click()
    await step8.getByRole("button", { name: /how it happened/i }).click()

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
    await step9.getByRole("button", { name: /start in telegram/i }).click()

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

  // US-6 end-to-end continuity: the first bot message must reference the
  // chosen scenario's venue + opening_hook. This exercises the Telegram MCP
  // which is NOT available in CI — run locally via `npx playwright test
  // --grep "@telegram-dogfood"`.
  test.skip("@telegram-dogfood first Telegram bot message references chosen venue + hook (US-6)", async () => {
    // Dogfood hook — orchestrator dispatches Telegram MCP subagent after
    // production deploy to verify SC-3 (backstory continuity). See
    // spec §SC-3 and tasks.md T324.
  })
})
