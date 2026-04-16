import { test, expect } from "@playwright/test"
import { mockApiRoutes } from "./fixtures"

/**
 * Spec 214 — Phone country gate (PR 214-C, T302)
 *
 * US-4: Voice path pre-flight — unsupported country codes MUST be rejected
 * client-side BEFORE POST /onboarding/profile is sent (spec NR-3).
 * US-5: When voice is unavailable, the Telegram fallback UI renders.
 *
 * Step 9 (`wizard-step-9`) offers a binary: voice vs Telegram. Choosing
 * voice expands the phone input; the wizard parses the E.164 number via
 * `libphonenumber-js` and checks membership in
 * `portal/src/app/onboarding/constants/supported-phone-countries.ts`.
 */

test.describe("Onboarding phone-country gate — US-4 + US-5 (Spec 214)", () => {
  test("unsupported country code blocks voice path (US-4)", async ({ page }) => {
    await mockApiRoutes(page)

    let postProfileCalled = false
    await page.route("**/api/v1/onboarding/profile", async (route) => {
      if (route.request().method() === "POST") {
        postProfileCalled = true
      }
      await route.fallback()
    })

    // Jump the wizard to step 9 via persisted localStorage.
    await page.addInitScript(
      ({ key, userId }) => {
        window.localStorage.setItem(
          key,
          JSON.stringify({
            version: 1,
            data: {
              user_id: userId,
              last_step: 9,
              location_city: "Damascus",
              social_scene: "techno",
              drug_tolerance: 3,
              life_stage: "tech",
              interest: null,
              name: "Test",
              age: 25,
              occupation: "engineer",
              phone: null,
              chosen_option_id: "scenario_techno_warehouse",
              cache_key: "test-cache-key",
              saved_at: new Date().toISOString(),
            },
          })
        )
      },
      { key: "nikita_wizard_e2e-player-id", userId: "e2e-player-id" }
    )

    await page.goto("/onboarding?resume=true", { waitUntil: "domcontentloaded" })

    const step9 = page.locator('[data-testid="wizard-step-9"]')
    await expect(step9).toBeVisible({ timeout: 10_000 })

    // Choose the voice path → phone input expands. Use exact name to avoid
    // matching the disabled "Call me." submit button (strict-mode violation).
    await step9.getByRole("button", { name: "Give her your number" }).click()

    const phoneInput = step9.locator('[data-testid="phone-input"]')
    await expect(phoneInput).toBeVisible({ timeout: 5_000 })

    // Syria (+963) — NOT in SUPPORTED_PHONE_COUNTRIES.
    await phoneInput.fill("+963912345678")

    // Attempt to advance (submit) via the voice CTA "Call me.".
    await step9.getByRole("button", { name: "Call me." }).click()

    // AC NR-3: client-side rejection — error message surfaces, profile NOT POSTed.
    await expect(step9).toContainText(/can.?t reach you there|telegram/i, { timeout: 5_000 })
    expect(postProfileCalled).toBe(false)
  })

  test("voice-unavailable (503) falls back to Telegram handoff UI (US-5)", async ({ page }) => {
    await mockApiRoutes(page)

    // Simulate voice agent unavailable — GET /pipeline-ready returns
    // `voice_available: false` so the handoff step renders Telegram fallback.
    await page.route("**/api/v1/onboarding/pipeline-ready/**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          state: "ready",
          venue_research_status: "ready",
          backstory_available: true,
          voice_available: false,
          wizard_step: 10,
          poll_interval_seconds: 1,
          poll_max_wait_seconds: 10,
        }),
      })
    })

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
      } else {
        await route.fallback()
      }
    })

    // Seed wizard at step 10 (pipeline gate) with a valid supported-country
    // phone so the previous step allowed voice.
    await page.addInitScript(
      ({ key, userId }) => {
        window.localStorage.setItem(
          key,
          JSON.stringify({
            version: 1,
            data: {
              user_id: userId,
              last_step: 10,
              location_city: "Zurich",
              social_scene: "techno",
              drug_tolerance: 3,
              life_stage: "tech",
              interest: null,
              name: "Test",
              age: 25,
              occupation: "engineer",
              phone: "+41791234567",
              chosen_option_id: "scenario_techno_warehouse",
              cache_key: "test-cache-key",
              saved_at: new Date().toISOString(),
            },
          })
        )
      },
      { key: "nikita_wizard_e2e-player-id", userId: "e2e-player-id" }
    )

    await page.goto("/onboarding?resume=true", { waitUntil: "domcontentloaded" })

    // Wait for step 11 (handoff) to appear after pipeline-ready resolves.
    const step11 = page.locator('[data-testid="wizard-step-11"]')
    await expect(step11).toBeVisible({ timeout: 15_000 })

    // AC US-5: voice_available=false → Telegram fallback visible.
    await expect(step11).toContainText(/telegram/i, { timeout: 5_000 })
  })
})
